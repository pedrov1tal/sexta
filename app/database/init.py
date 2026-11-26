import logging

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database.base import Base
from app.database.session import engine

_UPDATED_AT_BACKFILL_COLUMNS = {
    "checklists": "created_at",
    "tasks": None,
    "checklist_executions": "started_at",
    "task_executions": "completed_at",
}
logger = logging.getLogger(__name__)


def initialize_database(database_engine: Engine = engine) -> None:
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=database_engine)
    _migrate_updated_at_columns(database_engine)
    _migrate_unique_execution_date(database_engine)
    _migrate_notification_log(database_engine)


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


def _migrate_unique_execution_date(database_engine: Engine) -> None:
    if database_engine.dialect.name != "sqlite":
        return

    try:
        with database_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_checklist_execution_date "
                "ON checklist_executions (checklist_id, execution_date)"
            )
            connection.exec_driver_sql(
                "DROP INDEX IF EXISTS ix_executions_checklist_date"
            )
    except IntegrityError as error:
        logger.exception(
            "Não foi possível aplicar a unicidade de execução diária; "
            "verifique se há execuções duplicadas por checklist e data."
        )
        raise RuntimeError(
            "O banco contém execuções duplicadas por checklist e data."
        ) from error


def _migrate_notification_log(database_engine: Engine) -> None:
    if database_engine.dialect.name != "sqlite":
        return

    from app.database.models import NotificationLog

    inspector = inspect(database_engine)
    if "notification_logs" not in inspector.get_table_names():
        return
    columns = {
        column["name"]: column for column in inspector.get_columns("notification_logs")
    }
    required_columns = {
        "notification_type",
        "event_key",
        "attempt_count",
        "updated_at",
    }
    if (
        required_columns.issubset(columns)
        and columns["execution_id"]["nullable"]
    ):
        return

    raw_connection = database_engine.raw_connection()
    cursor = raw_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "ALTER TABLE notification_logs RENAME TO notification_logs_legacy"
        )
        cursor.execute(
            str(CreateTable(NotificationLog.__table__).compile(
                dialect=database_engine.dialect
            ))
        )
        cursor.execute(
            """
            INSERT INTO notification_logs (
                id,
                execution_id,
                message,
                status,
                notification_type,
                event_key,
                sent_at,
                error_message,
                attempt_count,
                updated_at
            )
            SELECT
                id,
                execution_id,
                message,
                status,
                'legacy',
                'legacy:' || id,
                sent_at,
                error_message,
                0,
                COALESCE(sent_at, CURRENT_TIMESTAMP)
            FROM notification_logs_legacy
            """
        )
        cursor.execute("DROP TABLE notification_logs_legacy")
        for index in NotificationLog.__table__.indexes:
            cursor.execute(
                str(CreateIndex(index).compile(dialect=database_engine.dialect))
            )
        violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                "A migração do histórico de notificações encontrou "
                "referências inválidas."
            )
        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        logger.exception("Falha ao migrar a tabela de notificações.")
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys=ON")
        raw_connection.close()
