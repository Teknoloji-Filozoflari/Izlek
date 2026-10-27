"""Asynchronous import/export workflow for the Settings page."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.i18n import t
from izlek.services.transfer import TransferError, TransferService
from izlek.ui.controllers.messages import file_operation_failed


def _local_path(value: str) -> Path:
    url = QUrl(value)
    path = url.toLocalFile() if url.isLocalFile() else value
    if not path.strip():
        raise TransferError("Dosya konumu seçilmedi")
    return Path(path)


class TransferController(QObject):
    """Validate, preview and transfer local data outside the UI thread."""

    changed = Signal()
    dataImported = Signal()
    _finished = Signal(int, str, object, str)

    def __init__(
        self,
        service: TransferService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or TransferService()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._busy = False
        self._feedback = ""
        self._feedback_kind = "neutral"
        self._preview: dict = {}
        self._import_path: Path | None = None
        self._finished.connect(self._apply_finished)

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Property(str, notify=changed)
    def feedbackKind(self) -> str:
        return self._feedback_kind

    @Property("QVariantMap", notify=changed)
    def preview(self) -> dict:
        return self._preview

    def _submit(self, action: str, path: Path) -> None:
        if self._busy:
            return
        self._generation += 1
        generation = self._generation
        self._busy = True
        self._feedback = ""
        self._feedback_kind = "neutral"
        self.changed.emit()
        self._executor.submit(self._work, generation, action, path)

    @Slot(str)
    def exportTo(self, location: str) -> None:
        try:
            path = _local_path(location)
        except TransferError as exc:
            self._feedback = str(exc)
            self._feedback_kind = "danger"
            self.changed.emit()
            return
        self._submit("export", path)

    @Slot(str)
    def previewImport(self, location: str) -> None:
        if self._busy:
            return
        try:
            path = _local_path(location)
        except TransferError as exc:
            self._feedback = str(exc)
            self._feedback_kind = "danger"
            self.changed.emit()
            return
        self._preview = {}
        self._import_path = path
        self._submit("preview", path)

    @Slot()
    def importSelected(self) -> None:
        if self._import_path is None or not self._preview:
            self._feedback = t("transfer.need_file")
