"""Qt Quick application entry point."""

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine

from izlek import __version__
from izlek.core.paths import app_paths
from izlek.db.engine import initialize_database
from izlek.ui.controllers.cache_controller import CacheController
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.custom_lists_controller import CustomListsController
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.favorites_controller import FavoritesController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.quick_library_controller import QuickLibraryController
from izlek.ui.controllers.search_controller import SearchController
from izlek.ui.controllers.statistics_controller import StatisticsController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.transfer_controller import TransferController
from izlek.ui.controllers.tv_detail_controller import TvDetailController
from izlek.ui.controllers.tv_library_controller import TvLibraryController

_PACKAGE_DIR = Path(__file__).resolve().parent
_MAIN_QML = _PACKAGE_DIR / "ui/qml/Main.qml"
_GALLERY_QML = _PACKAGE_DIR / "ui/qml/ComponentsGallery.qml"
_APP_ICON = _PACKAGE_DIR / "resources/icons/izlek.svg"


def create_application(
    gallery: bool = False,
    token_controller: TokenController | None = None,
    search_controller: SearchController | None = None,
    movie_controller: MovieDetailController | None = None,
    tv_controller: TvDetailController | None = None,
    continue_controller: ContinueWatchingController | None = None,
    movie_library_controller: MovieLibraryController | None = None,
    tv_library_controller: TvLibraryController | None = None,
    favorites_controller: FavoritesController | None = None,
    custom_lists_controller: CustomListsController | None = None,
    discover_controller: DiscoverController | None = None,
    statistics_controller: StatisticsController | None = None,
    transfer_controller: TransferController | None = None,
    cache_controller: CacheController | None = None,
    quick_library_controller: QuickLibraryController | None = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, QWindow]:
    """Load the QML shell and restore its saved size and maximized state."""
    application = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    application.setApplicationName("İzlek")
    application.setDesktopFileName("izlek")
    application.setWindowIcon(QIcon(str(_APP_ICON)))

    settings_path = app_paths().config / "window.ini"
    if gallery:
        settings = None
    else:
        try:
            settings_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            settings = None
        else:
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)

    def read_setting(key: str, default: int | bool, value_type: type) -> int | bool:
        if settings is None:
            return default
        return settings.value(key, default, type=value_type)

    engine = QQmlApplicationEngine()
    if not gallery:
        controller = token_controller or TokenController(parent=engine)
        if controller.parent() is None:
            controller.setParent(engine)
        engine.rootContext().setContextProperty("tokenController", controller)
        application.aboutToQuit.connect(controller.close)
        search = search_controller or SearchController(parent=engine)
        if search.parent() is None:
            search.setParent(engine)
        engine.rootContext().setContextProperty("searchController", search)
        controller.tokenSaved.connect(search.refresh_token)
        application.aboutToQuit.connect(search.close)
        movie = movie_controller or MovieDetailController(parent=engine)
        if movie.parent() is None:
            movie.setParent(engine)
        engine.rootContext().setContextProperty("movieController", movie)
        controller.tokenSaved.connect(movie.refresh_token)
        application.aboutToQuit.connect(movie.close)
        tv = tv_controller or TvDetailController(parent=engine)
        if tv.parent() is None:
            tv.setParent(engine)
        engine.rootContext().setContextProperty("tvController", tv)
        controller.tokenSaved.connect(tv.refresh_token)
        application.aboutToQuit.connect(tv.close)
        continuing = continue_controller or ContinueWatchingController(parent=engine)
        if continuing.parent() is None:
            continuing.setParent(engine)
        engine.rootContext().setContextProperty("continueController", continuing)
        controller.tokenSaved.connect(continuing.refresh_token)
        application.aboutToQuit.connect(continuing.close)
        favorites = favorites_controller or FavoritesController(parent=engine)
        if favorites.parent() is None:
            favorites.setParent(engine)
        engine.rootContext().setContextProperty("favoritesController", favorites)
        application.aboutToQuit.connect(favorites.close)
        custom_lists = custom_lists_controller or CustomListsController(parent=engine)
        if custom_lists.parent() is None:
            custom_lists.setParent(engine)
        engine.rootContext().setContextProperty("customListsController", custom_lists)
        application.aboutToQuit.connect(custom_lists.close)
        controller.tokenSaved.connect(custom_lists.refresh_token)
        discover = discover_controller or DiscoverController(parent=engine)
        if discover.parent() is None:
            discover.setParent(engine)
        engine.rootContext().setContextProperty("discoverController", discover)
        controller.tokenSaved.connect(discover.refresh_token)
        application.aboutToQuit.connect(discover.close)
        statistics = statistics_controller or StatisticsController(parent=engine)
        if statistics.parent() is None:
            statistics.setParent(engine)
        engine.rootContext().setContextProperty("statisticsController", statistics)
        controller.tokenSaved.connect(statistics.refresh_token)
        application.aboutToQuit.connect(statistics.close)
        library = movie_library_controller or MovieLibraryController(parent=engine)
        if library.parent() is None:
            library.setParent(engine)
        engine.rootContext().setContextProperty("movieLibraryController", library)
        controller.tokenSaved.connect(library.refresh_token)
        application.aboutToQuit.connect(library.close)
        shows = tv_library_controller or TvLibraryController(parent=engine)
        if shows.parent() is None:
            shows.setParent(engine)
        engine.rootContext().setContextProperty("tvLibraryController", shows)
        controller.tokenSaved.connect(shows.refresh_token)
        application.aboutToQuit.connect(shows.close)
        transfer = transfer_controller or TransferController(parent=engine)
        if transfer.parent() is None:
            transfer.setParent(engine)
        engine.rootContext().setContextProperty("transferController", transfer)
        transfer.dataImported.connect(continuing.refresh)
        transfer.dataImported.connect(favorites.refresh)
        transfer.dataImported.connect(custom_lists.refresh)
        transfer.dataImported.connect(statistics.refresh)
        transfer.dataImported.connect(library.refresh)
        transfer.dataImported.connect(shows.refresh)
        application.aboutToQuit.connect(transfer.close)
        cache = cache_controller or CacheController(parent=engine)
        if cache.parent() is None:
            cache.setParent(engine)
        engine.rootContext().setContextProperty("cacheController", cache)
        for local_controller in (
            continuing,
            favorites,
            custom_lists,
            statistics,
            library,
            shows,
        ):
            cache.metadataExpired.connect(local_controller.refresh)
        transfer.dataImported.connect(cache.refresh)
        controller.tokenSaved.connect(cache.refresh)
        movie.libraryChanged.connect(cache.refresh)
        tv.libraryChanged.connect(cache.refresh)
        application.aboutToQuit.connect(cache.close)
        quick_library = quick_library_controller or QuickLibraryController(
            parent=engine
        )
        if quick_library.parent() is None:
            quick_library.setParent(engine)
        engine.rootContext().setContextProperty("quickLibraryController", quick_library)
        application.aboutToQuit.connect(quick_library.close)
        transfer.dataImported.connect(quick_library.refresh)
        continuing.progressSaved.connect(statistics.refresh)
        continuing.progressSaved.connect(favorites.refresh)
        continuing.progressSaved.connect(quick_library.refresh)
        for detail_controller in (movie, tv):
            detail_controller.libraryChanged.connect(quick_library.refresh)
            for local_controller in (
                library, shows, statistics, custom_lists, favorites, continuing,
            ):
                detail_controller.libraryChanged.connect(local_controller.refresh)
        quick_library.libraryAdded.connect(cache.refresh)
        for local_controller in (library, shows, statistics, custom_lists, favorites):
            quick_library.libraryAdded.connect(local_controller.refresh)
        engine.rootContext().setContextProperty("appVersion", __version__)
    qml_file = _GALLERY_QML if gallery else _MAIN_QML
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    roots = engine.rootObjects()
    if not roots or not isinstance(roots[0], QWindow):
        raise RuntimeError(f"QML ana penceresi yüklenemedi: {qml_file}")

    window = roots[0]
    window.setIcon(application.windowIcon())
    window.resize(
        max(window.minimumWidth(), read_setting("window/width", 1280, int)),
        max(window.minimumHeight(), read_setting("window/height", 800, int)),
    )
    if read_setting("window/maximized", False, bool):
        window.showMaximized()
    else:
        window.show()

    def save_window_state() -> None:
        if settings is None:
            return
        maximized = bool(window.windowStates() & Qt.WindowState.WindowMaximized)
        settings.setValue("window/maximized", maximized)
        if not maximized:
            settings.setValue("window/width", window.width())
            settings.setValue("window/height", window.height())
        settings.sync()

    application.aboutToQuit.connect(save_window_state)
    return application, engine, window


def main() -> int:
    """Start the desktop application."""
    package_smoke = "--package-smoke-test" in sys.argv[1:]
    if package_smoke:
        executable_dir = Path(sys.executable).resolve().parent
        for user_path in vars(app_paths()).values():
            resolved = user_path.resolve()
            if resolved == executable_dir or executable_dir in resolved.parents:
                raise RuntimeError(
                    f"Paket kullanıcı verisini uygulama yanına yazamaz: {resolved}"
                )
    database = initialize_database()
    try:
        application, engine, window = create_application(
            gallery="--gallery" in sys.argv[1:]
        )
        if package_smoke:
            QTimer.singleShot(250, application.quit)
        return application.exec()
    finally:
        database.dispose()
