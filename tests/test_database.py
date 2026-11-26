from datetime import date, time

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.init import initialize_database
from app.database.models import ChecklistExecution, NotificationLog
from app.domain.enums import ChecklistType, ExecutionStatus, NotificationType
from app.database.repositories import (
    create_checklist,
    create_checklist_execution,
    create_notification_log,
    create_task,
    create_task_execution,
    get_checklist,
    list_checklists,
)
from app.database.session import create_database_engine


@pytest.fixture
def database_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_repository_operations_relationships_and_persistence(database_engine) -> None:
    with Session(database_engine) as session:
        checklist = create_checklist(
            session,
            title="Abertura",
            checklist_type=ChecklistType.OPENING,
            scheduled_time=time(8, 0),
            deadline=time(8, 30),
        )
        task = create_task(
            session,
            checklist_id=checklist.id,
            title="Verificar equipamentos",
            position=0,
        )
        execution = create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=date(2026, 11, 25),
        )
        create_task_execution(
            session,
            execution_id=execution.id,
            task_id=task.id,
        )
        create_notification_log(
            session,
            execution_id=execution.id,
            message="Checklist pendente",
            status="sent",
            notification_type=NotificationType.OVERDUE,
            event_key=f"checklist-overdue:{execution.id}",
        )
        session.commit()
        checklist_id = checklist.id

    with Session(database_engine) as session:
        saved_checklist = get_checklist(session, checklist_id)

        assert saved_checklist is not None
        assert saved_checklist.tasks[0].title == "Verificar equipamentos"
        assert saved_checklist.executions[0].status is ExecutionStatus.PENDING
        saved_task_execution = saved_checklist.executions[0].task_executions[0]
        assert saved_task_execution.task.title == (
            "Verificar equipamentos"
        )
        saved_notification = saved_checklist.executions[0].notification_logs[0]
        assert saved_notification.status == "sent"
        assert saved_notification.notification_type == NotificationType.OVERDUE.value
        assert saved_notification.event_key == "checklist-overdue:1"
        assert saved_notification.error_message is None
        assert [item.id for item in list_checklists(session, active_only=True)] == [
            checklist_id
        ]
        assert saved_task_execution.is_completed is False


def test_task_position_must_be_unique_within_checklist(database_engine) -> None:
    with Session(database_engine) as session:
        checklist = create_checklist(
            session, title="Operação", checklist_type=ChecklistType.OPERATION
        )
        create_task(
            session,
            checklist_id=checklist.id,
            title="Primeira tarefa",
            position=0,
        )
        session.commit()

        with pytest.raises(IntegrityError):
            create_task(
                session,
                checklist_id=checklist.id,
                title="Posição duplicada",
                position=0,
            )
        session.rollback()


def test_checklist_cannot_be_deleted_while_execution_exists(database_engine) -> None:
    with Session(database_engine) as session:
        checklist = create_checklist(
            session, title="Fechamento", checklist_type=ChecklistType.CLOSING
        )
        create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=date(2026, 11, 25),
        )
        session.commit()

        session.delete(checklist)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_only_one_execution_per_checklist_and_date(database_engine) -> None:
    with Session(database_engine) as session:
        checklist = create_checklist(
            session, title="Abertura", checklist_type=ChecklistType.OPENING
        )
        create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=date(2026, 11, 25),
        )
        session.commit()

        with pytest.raises(IntegrityError):
            create_checklist_execution(
                session,
                checklist_id=checklist.id,
                execution_date=date(2026, 11, 25),
            )
        session.rollback()


def test_notification_log_migration_preserves_existing_history(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    tables_without_notification_log = [
        table
        for table in Base.metadata.sorted_tables
        if table.name != "notification_logs"
    ]
    Base.metadata.create_all(engine, tables=tables_without_notification_log)

    with Session(engine) as session:
        checklist = create_checklist(
            session, title="Fechamento", checklist_type=ChecklistType.CLOSING
        )
        execution = create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=date(2026, 11, 25),
        )
        session.commit()
        execution_id = execution.id

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE notification_logs (
                id INTEGER PRIMARY KEY,
                execution_id INTEGER NOT NULL
                    REFERENCES checklist_executions(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                status VARCHAR(50) NOT NULL,
                sent_at DATETIME,
                error_message TEXT
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO notification_logs
                (id, execution_id, message, status, error_message)
            VALUES (17, ?, 'Registro legado', 'pending', 'erro anterior')
            """,
            (execution_id,),
        )

    initialize_database(engine)

    columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("notification_logs")
    }
    with Session(engine) as session:
        notification = session.get(NotificationLog, 17)

    assert columns["execution_id"]["nullable"] is True
    assert notification is not None
    assert notification.message == "Registro legado"
    assert notification.notification_type == "legacy"
    assert notification.event_key == "legacy:17"
    assert notification.error_message == "erro anterior"
    assert notification.attempt_count == 0
    engine.dispose()
