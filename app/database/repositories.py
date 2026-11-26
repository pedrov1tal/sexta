from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Checklist,
    ChecklistExecution,
    ChecklistType,
    ExecutionStatus,
    NotificationLog,
    Task,
    TaskExecution,
)


def create_checklist(
    session: Session,
    *,
    title: str,
    checklist_type: ChecklistType,
    description: str | None = None,
    scheduled_time: time | None = None,
    deadline: time | None = None,
    is_active: bool = True,
) -> Checklist:
    checklist = Checklist(
        title=title,
        checklist_type=checklist_type,
        description=description,
        scheduled_time=scheduled_time,
        deadline=deadline,
        is_active=is_active,
    )
    session.add(checklist)
    session.flush()
    return checklist


def get_checklist(session: Session, checklist_id: int) -> Checklist | None:
    return session.get(Checklist, checklist_id)


def list_checklists(
    session: Session, *, active_only: bool = False
) -> list[Checklist]:
    statement = select(Checklist).order_by(Checklist.id)
    if active_only:
        statement = statement.where(Checklist.is_active.is_(True))
    return list(session.scalars(statement).all())


def create_task(
    session: Session,
    *,
    checklist_id: int,
    title: str,
    position: int,
    description: str | None = None,
    is_required: bool = True,
) -> Task:
    task = Task(
        checklist_id=checklist_id,
        title=title,
        position=position,
        description=description,
        is_required=is_required,
    )
    session.add(task)
    session.flush()
    return task


def create_checklist_execution(
    session: Session,
    *,
    checklist_id: int,
    execution_date: date,
    status: ExecutionStatus = ExecutionStatus.PENDING,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> ChecklistExecution:
    execution = ChecklistExecution(
        checklist_id=checklist_id,
        execution_date=execution_date,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
    )
    session.add(execution)
    session.flush()
    return execution


def create_task_execution(
    session: Session,
    *,
    execution_id: int,
    task_id: int,
    is_completed: bool = False,
    completed_at: datetime | None = None,
) -> TaskExecution:
    task_execution = TaskExecution(
        execution_id=execution_id,
        task_id=task_id,
        is_completed=is_completed,
        completed_at=completed_at,
    )
    session.add(task_execution)
    session.flush()
    return task_execution


def create_notification_log(
    session: Session,
    *,
    execution_id: int,
    message: str,
    status: str,
    sent_at: datetime | None = None,
    error_message: str | None = None,
) -> NotificationLog:
    notification = NotificationLog(
        execution_id=execution_id,
        message=message,
        status=status,
        sent_at=sent_at,
        error_message=error_message,
    )
    session.add(notification)
    session.flush()
    return notification
