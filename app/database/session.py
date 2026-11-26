from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args = (
        {"check_same_thread": False}
        if url.get_backend_name() == "sqlite"
        else {}
    )

    if (
        url.get_backend_name() == "sqlite"
        and url.database not in (None, "", ":memory:")
    ):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    database_engine = create_engine(url, connect_args=connect_args)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(connection, _connection_record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database_engine


engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
