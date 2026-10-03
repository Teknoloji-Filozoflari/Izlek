"""SQLite engine and automatic Alembic migration setup."""

from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from izlek.core.paths import app_paths

DB_FILENAME = "izlek.sqlite3"
_MIGRATION_LOCK = Lock()


def database_path() -> Path:
    """Return the database file under the current XDG data directory."""
    return app_paths().data / DB_FILENAME


def create_database_engine(path: Path | None = None) -> Engine:
    """Create a SQLite engine with foreign keys enforced on every connection."""
    target = database_path() if path is None else path
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        target.touch(mode=0o600, exist_ok=False)
    except FileExistsError:
        pass
    engine = create_engine(URL.create("sqlite", database=str(target)))

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def upgrade_database(engine: Engine) -> None:
    """Apply all packaged Alembic revisions to an existing or new database."""
    migrations = Path(__file__).parent / "migrations"
    config = Config()
    config.set_main_option("script_location", str(migrations))
    # Alembic's EnvironmentContext uses process-global module proxies.
    with _MIGRATION_LOCK, engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def initialize_database(path: Path | None = None) -> Engine:
    """Open the local database and bring its schema to the current revision."""
    engine = create_database_engine(path)
    try:
        upgrade_database(engine)
    except Exception:
        engine.dispose()
        raise
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a factory whose sessions callers commit or roll back explicitly."""
    return sessionmaker(bind=engine, expire_on_commit=False)
