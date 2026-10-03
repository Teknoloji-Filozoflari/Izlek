"""Exercise the installed QML shell with a selected Linux Qt platform plugin."""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", choices=("wayland", "xcb", "offscreen"), required=True
    )
    parser.add_argument("--gallery", action="store_true")
    parser.add_argument("--onboarding", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()

    os.environ["QT_QPA_PLATFORM"] = args.platform
    if args.platform == "offscreen":
        os.environ["QT_QUICK_BACKEND"] = "software"

    from PySide6.QtCore import (
        QPoint,
        QPointF,
        Qt,
        QTimer,
        QtMsgType,
        qInstallMessageHandler,
    )
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickItem, QQuickWindow
    from PySide6.QtTest import QTest
    from shiboken6 import getCppPointer, wrapInstance

    from izlek.app import create_application
    from izlek.security.token_store import StoredToken
    from izlek.ui.controllers.token_controller import TokenController

    class SmokeStore:
        def load(self):
            return None if args.onboarding else StoredToken("test-only", "keyring")

    qml_warnings = []
    other_warnings = []

    def collect_warning(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            target = qml_warnings if ".qml:" in message else other_warnings
            target.append(message)
        if kind in (
            QtMsgType.QtWarningMsg,
            QtMsgType.QtCriticalMsg,
            QtMsgType.QtFatalMsg,
        ):
            print(f"Qt: {message}", file=sys.stderr, flush=True)

    previous_handler = qInstallMessageHandler(collect_warning)
    with TemporaryDirectory(prefix="izlek-display-") as config_home:
        os.environ["XDG_CONFIG_HOME"] = config_home
        controller = TokenController(store=SmokeStore())
        application, engine, window = create_application(
            gallery=args.gallery, token_controller=controller
        )
        result = {"ok": False}

        def check_window() -> None:
            try:
                if args.gallery:
                    grid = window.findChild(QQuickItem, "galleryGrid")
                    assert grid is not None and grid.property("count") == 18
                    card = grid.property("currentItem")
                    card.forceActiveFocus()
                    QTest.keyClick(window, Qt.Key.Key_Return)
                elif args.onboarding:
                    onboarding = window.findChild(QQuickItem, "onboardingPage")
                    token_input = window.findChild(QQuickItem, "tokenInput")
                    assert onboarding is not None and onboarding.isVisible()
                    assert token_input is not None
                else:
                    stack = window.findChild(QQuickItem, "contentStack")
                    for index, name in enumerate(
                        (
                            "navHome",
                            "navMovies",
                            "navShows",
                            "navLists",
                            "navDiscover",
                            "navSettings",
                        )
                    ):
                        item = window.findChild(QQuickItem, name)
                        center = item.mapToScene(
                            QPointF(item.width() / 2, item.height() / 2)
                        )
                        QTest.mouseClick(
                            window,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier,
                            QPoint(int(center.x()), int(center.y())),
                        )
                        application.processEvents()
                        assert window.property("currentIndex") == index
                        assert stack.property("currentItem") is not None

                for width, height in ((1366, 768), (1920, 1080)):
                    window.resize(width, height)
                    application.processEvents()
                    print(
                        f"resize request {width}x{height}: "
                        f"actual {window.width()}x{window.height()}"
                    )

                if args.screenshot is not None:
                    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                    quick_window = wrapInstance(getCppPointer(window)[0], QQuickWindow)
                    assert quick_window.grabWindow().save(str(args.screenshot))

                print(f"Qt platform: {QGuiApplication.platformName()}")
                print(f"QML warnings: {len(qml_warnings)}")
                print(f"Other Qt warnings: {len(other_warnings)}")
                result["ok"] = not qml_warnings
            except Exception as error:
                print(f"Smoke test failed: {error}", file=sys.stderr)
            finally:
                application.quit()

        QTimer.singleShot(350, check_window)
        application.exec()
        qInstallMessageHandler(previous_handler)
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
