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
            self._feedback_kind = "danger"
            self.changed.emit()
            return
        self._submit("import", self._import_path)

    def _work(self, generation: int, action: str, path: Path) -> None:
        try:
            if action == "export":
                result = self._service.export_file(path)
            elif action == "preview":
                result = self._service.preview_file(path)
            else:
                result = self._service.import_file(path)
        except TransferError as exc:
            self._finished.emit(generation, action, {}, str(exc))
        except (OSError, SQLAlchemyError, ValueError, KeyError, OverflowError):
            self._finished.emit(generation, action, {}, file_operation_failed())
        else:
            self._finished.emit(generation, action, result, "")

    @Slot(int, str, object, str)
    def _apply_finished(
        self, generation: int, action: str, result: dict, error: str
    ) -> None:
        if generation != self._generation:
            return
        self._busy = False
        if error:
            self._feedback = error
            self._feedback_kind = "danger"
            if action == "preview":
                self._preview = {}
                self._import_path = None
            self.changed.emit()
            return
        if action == "preview":
            self._preview = result
            self._feedback = t("transfer.validated")
        elif action == "export":
            self._feedback = t("transfer.exported")
        else:
            self._feedback = t("transfer.imported")
            self._preview = {}
            self._import_path = None
            self.dataImported.emit()
        self._feedback_kind = "success"
        self.changed.emit()

    def close(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._service.close()
