from sqlalchemy.engine import Engine

from app.database.base import Base
from app.database.session import engine


def initialize_database(database_engine: Engine = engine) -> None:
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=database_engine)
