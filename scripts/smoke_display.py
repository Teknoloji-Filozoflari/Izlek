"""Exercise the installed QML shell with a selected Linux Qt platform plugin."""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", choices=("wayland", "xcb", "offscreen"), required=True
    )
    parser.add_argument("--gallery", action="store_true")
    parser.add_argument("--onboarding", action="store_true")
    parser.add_argument("--hover-filters", action="store_true")
    parser.add_argument("--hover-list-picker", action="store_true")
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
    from PySide6.QtQml import QQmlExpression
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
    with (
        TemporaryDirectory(prefix="izlek-display-") as user_root,
        patch("izlek.security.token_store._system_keyring", return_value=None),
    ):
        for name, directory in (
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_STATE_HOME", "state"),
        ):
            os.environ[name] = str(Path(user_root) / directory)
        controller = TokenController(store=SmokeStore())
        lists_controller = None
        if args.hover_list_picker:
            from datetime import UTC, datetime

            from izlek.db.engine import create_session_factory, initialize_database
            from izlek.db.models import MediaType
            from izlek.repositories.local import MediaRepository
            from izlek.services.custom_lists import CustomListsService
            from izlek.ui.controllers.custom_lists_controller import (
                CustomListsController,
            )

            database = initialize_database()
            factory = create_session_factory(database)
            with factory.begin() as session:
                repo = MediaRepository(session)
                for kind, title in ((MediaType.MOVIE, "Deneme Film"),
                                    (MediaType.TV, "Deneme Dizi")):
                    repo.upsert(42, kind, title, last_synced_at=datetime.now(UTC))
            service = CustomListsService(factory)
            service.create("Deneme Listesi")
            lists_controller = CustomListsController(service)
        application, engine, window = create_application(
            gallery=args.gallery, token_controller=controller,
            custom_lists_controller=lists_controller,
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
                elif args.hover_filters or args.hover_list_picker:
                    window.resize(1366, 768)
                    if args.hover_list_picker:
                        window.navigate(3)
                        for _ in range(100):
                            application.processEvents()
                            if (not lists_controller.busy
                                    and lists_controller.candidates):
                                break
                            QTest.qWait(20)
                    QTest.qWait(200)

                    def option_labels(item):
                        found = (
                            [item] if item.objectName() == "filterOptionLabel" else []
                        )
                        for child in item.childItems():
                            found.extend(option_labels(child))
                        return found

                    names = (("listMediaPicker",) if args.hover_list_picker else
                             ("discoverMedia", "discoverGenre", "discoverCountry"))
                    for name in names:
                        combo = window.findChild(QQuickItem, name)
                        combo.forceActiveFocus()
                        QTest.keyClick(window, Qt.Key.Key_Space)
                        QTest.qWait(200)
                        view = QQmlExpression(
                            engine.rootContext(), combo, "popup.contentItem"
                        ).evaluate()[0]
                        labels = option_labels(view)
                        assert labels, (
                            name, "No popup labels", combo.property("count")
                        )
                        assert labels[0].property("text") == combo.textAt(0), (
                            name, labels[0].property("text"), combo.textAt(0)
                        )
                        for label in labels:
                            if (
                                label.parentItem().y() + label.parentItem().height()
                                > view.height()
                            ):
                                continue
                            point = label.mapToScene(
                                QPointF(label.width() / 2, label.height() / 2)
                            )
                            QTest.mouseMove(window, point.toPoint())
                            QTest.qWait(75)
                            assert all(option.isVisible() for option in labels), (
                                name, [(option.property("text"), option.isVisible(),
                                        option.parentItem().isVisible())
                                       for option in labels], point,
                                combo.property("enabled"),
                            )
                            assert all(
                                option.parentItem().isVisible() for option in labels
                            ), name
                        print(
                            f"Hover verified: {name}, {len(labels)} visible delegates"
                        )
                        if name == "discoverMedia":
                            label = labels[-1]
                            point = label.mapToScene(
                                QPointF(label.width() / 2, label.height() / 2)
                            )
                            QTest.mouseClick(
                                window,
                                Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier,
                                point.toPoint(),
                            )
                            QTest.qWait(100)
                            assert combo.property("currentIndex") == 1
                            search = engine.rootContext().contextProperty(
                                "searchController"
                            )
                            assert search.mediaType == "tv"
                        else:
                            QTest.keyClick(window, Qt.Key.Key_Escape)
                        QTest.qWait(100)
                else:
                    stack = window.findChild(QQuickItem, "contentStack")
                    for index, name in enumerate(
                        (
                            "navHome",
                            "navMovies",
                            "navShows",
                            "navLists",
                            "navStatistics",
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
                        QTest.qWait(300)
                        assert window.property("currentIndex") == index
                        assert stack.property("currentItem") is not None

                for width, height in ((1366, 768), (1920, 1080)):
                    window.resize(width, height)
                    application.processEvents()
                    QTest.qWait(100)
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
