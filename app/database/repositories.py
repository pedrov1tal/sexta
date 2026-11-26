from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ChecklistType, ExecutionStatus
from app.database.models import (
    Checklist,
    ChecklistExecution,
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


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def get_checklist_execution(
    session: Session, execution_id: int
) -> ChecklistExecution | None:
    return session.get(ChecklistExecution, execution_id)


def get_task_execution(
    session: Session, execution_id: int, task_id: int
) -> TaskExecution | None:
    statement = select(TaskExecution).where(
        TaskExecution.execution_id == execution_id,
        TaskExecution.task_id == task_id,
    )
    return session.scalar(statement)


def list_checklists(
    session: Session, *, active_only: bool = False
) -> list[Checklist]:
    statement = select(Checklist).order_by(Checklist.id)
    if active_only:
        statement = statement.where(Checklist.is_active.is_(True))
    return list(session.scalars(statement).all())


def list_tasks(session: Session, checklist_id: int) -> list[Task]:
    statement = (
        select(Task)
        .where(Task.checklist_id == checklist_id)
        .order_by(Task.position, Task.id)
    )
    return list(session.scalars(statement).all())


def list_checklist_executions(
    session: Session, *, skip: int = 0, limit: int = 100
) -> list[ChecklistExecution]:
    statement = (
        select(ChecklistExecution)
        .order_by(ChecklistExecution.execution_date.desc(), ChecklistExecution.id.desc())
        .offset(skip)
        .limit(limit)
    )
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


def create_task_executions(
    session: Session, *, execution_id: int, task_ids: list[int]
) -> list[TaskExecution]:
    task_executions = [
        TaskExecution(execution_id=execution_id, task_id=task_id)
        for task_id in task_ids
    ]
    session.add_all(task_executions)
    session.flush()
    return task_executions


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
