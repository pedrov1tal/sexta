from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.automation.engine import run_automation_check
from app.config import settings
from app.database.base import Base
from app.database.init import initialize_database
from app.database.models import Checklist, ChecklistExecution, NotificationLog
from app.database.repositories import create_checklist, create_task
from app.database.session import create_database_engine
from app.domain.enums import ChecklistType, ExecutionStatus


@pytest.fixture
def session_factory(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'automation-test.db'}")
    initialize_database(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_scheduled_checklist(
    session_factory, *, required_tasks: int = 1, optional_tasks: int = 0
) -> int:
    with session_factory() as session:
        with session.begin():
            checklist = create_checklist(
                session,
                title="Abertura",
                checklist_type=ChecklistType.OPENING,
                scheduled_time=time(8, 0),
                deadline=time(9, 0),
            )
            for position in range(required_tasks + optional_tasks):
                create_task(
                    session,
                    checklist_id=checklist.id,
                    title=f"Tarefa {position + 1}",
                    position=position,
                    is_required=position < required_tasks,
                )
            checklist_id = checklist.id
    return checklist_id


def test_monitoring_starts_due_execution_once_and_counts_pending_tasks(
    session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "operation_timezone", "UTC")
    checklist_id = create_scheduled_checklist(
        session_factory, required_tasks=1, optional_tasks=1
    )

    before_schedule = run_automation_check(
        session_factory, datetime(2026, 11, 25, 7, 59, tzinfo=timezone.utc)
    )
    assert before_schedule.started_executions == 0

    at_schedule = run_automation_check(
        session_factory, datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
    )
    assert at_schedule.started_executions == 1
    assert at_schedule.pending_executions == 1
    assert at_schedule.pending_tasks == 2
    assert at_schedule.notification_events == 0

    following_check = run_automation_check(
        session_factory, datetime(2026, 11, 25, 8, 1, tzinfo=timezone.utc)
    )
    assert following_check.started_executions == 0
    assert following_check.inspected_executions == 1

    with session_factory() as session:
        executions = list(session.scalars(select(ChecklistExecution)))
        assert len(executions) == 1
        assert executions[0].checklist_id == checklist_id
        assert executions[0].execution_date == date(2026, 11, 25)
        assert executions[0].status is ExecutionStatus.IN_PROGRESS


def test_overdue_execution_emits_one_notification_and_survives_deactivation(
    session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "operation_timezone", "UTC")
    checklist_id = create_scheduled_checklist(session_factory)

    started = run_automation_check(
        session_factory, datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
    )
    assert started.started_executions == 1

    with session_factory() as session:
        with session.begin():
            checklist = session.get(Checklist, checklist_id)
            assert checklist is not None
            checklist.is_active = False

    after_deadline = datetime(2026, 11, 25, 9, 1, tzinfo=timezone.utc)
    overdue = run_automation_check(session_factory, after_deadline)
    assert overdue.active_checklists == 0
    assert overdue.overdue_executions == 1
    assert overdue.notification_events == 1
    assert overdue.pending_tasks == 1

    repeated = run_automation_check(
        session_factory, datetime(2026, 11, 25, 9, 2, tzinfo=timezone.utc)
    )
    assert repeated.notification_events == 0
    assert repeated.overdue_executions == 1

    with session_factory() as session:
        executions = list(session.scalars(select(ChecklistExecution)))
        events = list(session.scalars(select(NotificationLog)))
        assert len(executions) == 1
        assert executions[0].status is ExecutionStatus.OVERDUE
        assert len(events) == 1
        assert events[0].status == "pending"
        assert "tarefa(s) obrigatória(s) pendente(s)" in events[0].message


def test_scheduled_job_catches_failures_and_remains_callable(
    monkeypatch, caplog
) -> None:
    from app.automation import __main__ as automation_main

    def fail_check(_session_factory) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        automation_main, "run_automation_check", fail_check
    )

    automation_main._run_scheduled_check()
    automation_main._run_scheduled_check()

    assert caplog.text.count("agendador continuará ativo") == 2
