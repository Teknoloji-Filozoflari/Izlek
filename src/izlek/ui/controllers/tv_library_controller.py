"""TV library controller with shared film and TV presentation behavior."""

from PySide6.QtCore import QObject

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.library_controller import LibraryController


class TvLibraryController(LibraryController):
    """Expose locally tracked shows and episode progress to Diziler."""

    def __init__(
        self,
        service: TvLibraryService | None = None,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(service or TvLibraryService(), images, store, parent)
