from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.base import Base
from app.database.session import engine

_UPDATED_AT_BACKFILL_COLUMNS = {
    "checklists": "created_at",
    "tasks": None,
    "checklist_executions": "started_at",
    "task_executions": "completed_at",
}


def initialize_database(database_engine: Engine = engine) -> None:
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=database_engine)
    _migrate_updated_at_columns(database_engine)


def _migrate_updated_at_columns(database_engine: Engine) -> None:
    if database_engine.dialect.name != "sqlite":
        return

    inspector = inspect(database_engine)
    existing_tables = set(inspector.get_table_names())
    for table_name, source_column in _UPDATED_AT_BACKFILL_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if "updated_at" in existing_columns:
            continue

        with database_engine.begin() as connection:
            connection.exec_driver_sql(
                f'ALTER TABLE "{table_name}" ADD COLUMN updated_at DATETIME'
            )
            value_expression = (
                f'COALESCE("{source_column}", CURRENT_TIMESTAMP)'
                if source_column
                else "CURRENT_TIMESTAMP"
            )
            connection.exec_driver_sql(
                f'UPDATE "{table_name}" SET updated_at = {value_expression}'
            )
