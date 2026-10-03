"""Alembic environment for the installed application and CLI."""

from alembic import context

from izlek.db.engine import create_database_engine
from izlek.db.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations_online()
