"""Movie library controller with shared film and TV presentation behavior."""

from PySide6.QtCore import QObject

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.services.movie_library import MovieLibraryService
from izlek.ui.controllers.library_controller import LibraryController


class MovieLibraryController(LibraryController):
    """Expose locally tracked movies to the Filmler page."""

    def __init__(
        self,
        service: MovieLibraryService | None = None,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(service or MovieLibraryService(), images, store, parent)
