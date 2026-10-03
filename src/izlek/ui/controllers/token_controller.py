"""Nonblocking onboarding and token replacement for QML."""

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QThreadPool, Signal, Slot

from izlek.security.token_store import TokenStore
from izlek.tmdb.client import TmdbClient, TokenValidationError


class TokenController(QObject):
    """Validate in a worker, then expose only safe UI state to QML."""

    hasTokenChanged = Signal()
    busyChanged = Signal()
    feedbackChanged = Signal()
    storageChanged = Signal()
    tokenSaved = Signal()
    _finished = Signal(int, bool, str, str)

    def __init__(
        self,
        store: TokenStore | None = None,
        client: TmdbClient | None = None,
        runner: Callable[[Callable[[], None]], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._client = client or TmdbClient()
        self._runner = runner or QThreadPool.globalInstance().start
        self._has_token = False
        self._busy = False
        self._feedback = ""
        self._feedback_kind = "neutral"
        self._storage = ""
        self._request_id = 0
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            self._set_feedback("TMDb tokenı güvenli biçimde okunamadı.", "danger")
        else:
            if stored is not None:
                self._has_token = True
                self._storage = stored.location
        self._finished.connect(self._on_finished)

    @Property(bool, notify=hasTokenChanged)
    def hasToken(self) -> bool:
        return self._has_token

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=feedbackChanged)
    def feedback(self) -> str:
        return self._feedback

    @Property(str, notify=feedbackChanged)
    def feedbackKind(self) -> str:
        return self._feedback_kind

    @Property(str, notify=storageChanged)
    def storageKind(self) -> str:
        return self._storage

    def _set_feedback(self, message: str, kind: str) -> None:
        self._feedback = message
        self._feedback_kind = kind
        self.feedbackChanged.emit()

    @Slot(str)
    def testToken(self, token: str) -> None:
        self._start(token, save=False)

    @Slot(str)
    def saveToken(self, token: str) -> None:
        self._start(token, save=True)

    def _start(self, token: str, *, save: bool) -> None:
        if self._busy:
            return
        candidate = token.strip()
        if not candidate:
            self._set_feedback("TMDb Read Access Token girin.", "danger")
            return
        self._request_id += 1
        request_id = self._request_id
        self._busy = True
        self.busyChanged.emit()
        self._set_feedback("Token doğrulanıyor…", "neutral")

        def work() -> None:
            try:
                self._client.validate_token(candidate)
                location = self._store.save(candidate) if save else ""
            except TokenValidationError as exc:
                self._finished.emit(request_id, False, "", str(exc))
            except OSError:
                self._finished.emit(
                    request_id, False, "", "Token güvenli biçimde kaydedilemedi."
                )
            except Exception:
                self._finished.emit(request_id, False, "", "İşlem tamamlanamadı.")
            else:
                self._finished.emit(request_id, True, location, "")

        self._runner(work)

    @Slot(int, bool, str, str)
    def _on_finished(
        self, request_id: int, success: bool, location: str, error: str
    ) -> None:
        if request_id != self._request_id:
            return
        self._busy = False
        self.busyChanged.emit()
        if not success:
            self._set_feedback(error, "danger")
            return
        if location:
            self._storage = location
            self.storageChanged.emit()
            if location == "file":
                self._set_feedback(
                    "Token kaydedildi. Sistem anahtarlığı kullanılamadı; token "
                    "yalnızca hesabınızın okuyabildiği yerel dosyada düz metin "
                    "olarak saklanıyor.",
                    "warning",
                )
            else:
                self._set_feedback("Token kaydedildi.", "success")
            if not self._has_token:
                self._has_token = True
                self.hasTokenChanged.emit()
            self.tokenSaved.emit()
        else:
            self._set_feedback("Token geçerli.", "success")
