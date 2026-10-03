"""TMDb token validation, secure storage, and first-run QML flow."""

from stat import S_IMODE

import httpx
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken, TokenStore
from izlek.tmdb.client import TmdbClient, TokenValidationError
from izlek.ui.controllers.token_controller import TokenController


class MemoryKeyring:
    def __init__(self):
        self.value = None

    def get_password(self, service, username):
        return self.value

    def set_password(self, service, username, password):
        self.value = password


class FailingKeyring(MemoryKeyring):
    def get_password(self, service, username):
        raise RuntimeError("unavailable")

    def set_password(self, service, username, password):
        raise RuntimeError("unavailable")


class FailingUpdateKeyring(MemoryKeyring):
    def set_password(self, service, username, password):
        raise RuntimeError("unavailable")


class FakeClient:
    def validate_token(self, token):
        if not token.startswith("valid-for-test"):
            raise TokenValidationError("TMDb tokenı geçersiz veya yetkisiz.")


def test_tmdb_validation_uses_bearer_and_safe_errors():
    seen = []

    def respond(request):
        seen.append(request)
        if request.headers["Authorization"] == "Bearer valid-for-test":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(
            401, json={"status_message": "Secret should not be shown"}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        client = TmdbClient(http_client)
        client.validate_token("valid-for-test")
        try:
            client.validate_token("invalid-for-test")
        except TokenValidationError as error:
            assert "geçersiz" in str(error)
            assert "Secret" not in str(error)
            assert "invalid-for-test" not in str(error)
        else:
            raise AssertionError("Geçersiz token kabul edildi")
    assert seen[0].url == "https://api.themoviedb.org/3/authentication"
    assert seen[0].headers["Authorization"] == "Bearer valid-for-test"


def test_tmdb_rate_limit_retries_once():
    requests = []
    delays = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json={"success": True})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        TmdbClient(http_client, sleeper=delays.append).validate_token("valid-for-test")
    assert len(requests) == 2
    assert delays == [2.0]


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (httpx.ConnectError("offline"), "İnternetinizi kontrol edin"),
        (httpx.ReadTimeout("timed out"), "zaman aşımına uğradı"),
    ],
)
def test_tmdb_network_failures_are_safe(error, message):
    def fail(request):
        raise error

    with httpx.Client(transport=httpx.MockTransport(fail)) as http_client:
        with pytest.raises(TokenValidationError, match=message):
            TmdbClient(http_client).validate_token("test-only")


def test_token_store_prefers_keyring_and_file_fallback(tmp_path):
    path = tmp_path / "config/tmdb-token"
    keyring = MemoryKeyring()
    store = TokenStore(path, keyring)
    assert store.load() is None
    assert store.save("valid-for-test") == "keyring"
    assert store.load() == StoredToken("valid-for-test", "keyring")
    assert not path.exists()

    fallback = TokenStore(path, FailingKeyring())
    assert fallback.save("fallback-for-test") == "file"
    assert S_IMODE(path.stat().st_mode) == 0o600
    assert fallback.load() == StoredToken("fallback-for-test", "file")
    assert store.load() == StoredToken("fallback-for-test", "keyring")
    assert not path.exists()


def test_fallback_migrates_to_available_keyring(tmp_path):
    path = tmp_path / "config/tmdb-token"
    TokenStore(path, FailingKeyring()).save("fallback-for-test")
    keyring = MemoryKeyring()
    assert TokenStore(path, keyring).load() == StoredToken(
        "fallback-for-test", "keyring"
    )
    assert not path.exists()
    assert keyring.value == "fallback-for-test"


def test_new_fallback_overrides_old_keyring_token(tmp_path):
    path = tmp_path / "config/tmdb-token"
    keyring = FailingUpdateKeyring()
    keyring.value = "old-for-test"
    store = TokenStore(path, keyring)
    assert store.save("new-for-test") == "file"
    assert store.load() == StoredToken("new-for-test", "file")


def test_insecure_existing_fallback_is_rejected(tmp_path):
    path = tmp_path / "tmdb-token"
    path.write_text("secret", encoding="utf-8")
    path.chmod(0o644)
    try:
        TokenStore(path, FailingKeyring()).load()
    except PermissionError:
        pass
    else:
        raise AssertionError("Geniş izinli token dosyası kabul edildi")


def test_token_store_without_keyring_uses_restricted_file(
    tmp_path, monkeypatch
):
    import izlek.security.token_store as token_store

    monkeypatch.setattr(token_store, "_system_keyring", lambda: None)
    path = tmp_path / "config/tmdb-token"
    store = TokenStore(path)

    assert store.save("file-only-token") == "file"
    assert store.load() == StoredToken("file-only-token", "file")
    assert S_IMODE(path.parent.stat().st_mode) == 0o700
    assert S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("token", ["", "   ", " token", "token ", "to ken"])
def test_token_store_rejects_empty_or_whitespace_tokens(tmp_path, token):
    store = TokenStore(tmp_path / "tmdb-token", MemoryKeyring())

    with pytest.raises(ValueError, match="token"):
        store.save(token)


def test_controller_rejects_invalid_and_saves_valid_token(tmp_path):
    store = TokenStore(tmp_path / "config/tmdb-token", MemoryKeyring())
    queued = []
    controller = TokenController(store=store, client=FakeClient(), runner=queued.append)
    assert controller.hasToken is False

    controller.saveToken("invalid-for-test")
    assert controller.busy is True
    assert store.load() is None
    queued.pop()()
    assert controller.hasToken is False
    assert controller.feedbackKind == "danger"
    assert store.load() is None

    controller.testToken("valid-for-test")
    queued.pop()()
    assert controller.feedback == "Token geçerli."
    assert store.load() is None

    controller.saveToken("valid-for-test")
    queued.pop()()
    assert controller.hasToken is True
    assert store.load() == StoredToken("valid-for-test", "keyring")
    reopened = TokenController(store=store, client=FakeClient(), runner=queued.append)
    assert reopened.hasToken is True


def test_default_worker_completes_without_blocking_ui(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    store = TokenStore(tmp_path / "config/tmdb-token", MemoryKeyring())
    controller = TokenController(store=store, client=FakeClient())
    controller.saveToken("valid-for-test")
    for _ in range(20):
        if not controller.busy:
            break
        QTest.qWait(20)
    assert controller.busy is False
    assert controller.hasToken is True
    assert store.load().value == "valid-for-test"
    application.processEvents()


def test_fresh_onboarding_and_settings_token_change(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    store = TokenStore(tmp_path / "config/tmdb-token", MemoryKeyring())
    controller = TokenController(
        store=store, client=FakeClient(), runner=lambda work: work()
    )
    warnings = []

    def collect_warning(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous_handler = qInstallMessageHandler(collect_warning)
    try:
        application, engine, window = create_application(token_controller=controller)
        onboarding = window.findChild(QQuickItem, "onboardingPage")
        sidebar = window.findChild(QQuickItem, "sidebar")
        token_field = window.findChild(QQuickItem, "tokenInput")
        assert onboarding.isVisible()
        assert not sidebar.isVisible()
        assert token_field.property("passwordMasked") is True

        controller.saveToken("invalid-for-test")
        application.processEvents()
        assert onboarding.isVisible()
        assert controller.feedbackKind == "danger"
        assert store.load() is None

        controller.saveToken("valid-for-test")
        application.processEvents()
        assert not onboarding.isVisible()
        assert sidebar.isVisible()
        assert controller.feedbackKind == "success"

        settings = window.findChild(QQuickItem, "navSettings")
        center = settings.mapToScene(
            QPointF(settings.width() / 2, settings.height() / 2)
        )
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        application.processEvents()
        assert window.property("currentIndex") == 5
        stack = window.findChild(QQuickItem, "contentStack")
        for _ in range(10):
            if not stack.property("busy"):
                break
            QTest.qWait(100)
        assert not stack.property("busy")
        settings_page = window.findChild(QQuickItem, "settingsPage")
        change_button = settings_page.findChild(QQuickItem, "changeTokenButton")
        center = change_button.mapToScene(
            QPointF(change_button.width() / 2, change_button.height() / 2)
        )
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        application.processEvents()
        replacement = settings_page.findChild(QQuickItem, "tokenInput")
        assert settings_page.property("editingToken") is True
        assert replacement.isVisible()
        replacement.setProperty("text", "valid-for-test-replaced")
        application.processEvents()
        save_button = settings_page.findChild(QQuickItem, "saveTokenButton")
        assert save_button.isEnabled()
        center = save_button.mapToScene(
            QPointF(save_button.width() / 2, save_button.height() / 2)
        )
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        application.processEvents()
        assert store.load().value == "valid-for-test-replaced"
        assert replacement.property("text") == ""
        window.close()
        application.processEvents()
        assert not warnings
    finally:
        qInstallMessageHandler(previous_handler)
