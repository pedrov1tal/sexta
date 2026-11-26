from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.domain.enums import ChecklistType, ExecutionStatus
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
