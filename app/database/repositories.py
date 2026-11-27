from datetime import date, datetime, time

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import ChecklistType, ExecutionStatus
from app.domain.enums import NotificationType
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
    statement = (
        select(ChecklistExecution)
        .options(
            selectinload(ChecklistExecution.checklist),
            selectinload(ChecklistExecution.task_executions).selectinload(
                TaskExecution.task
            ),
        )
        .where(ChecklistExecution.id == execution_id)
    )
    return session.scalar(statement)


def get_checklist_execution_for_date(
    session: Session, checklist_id: int, execution_date: date
) -> ChecklistExecution | None:
    statement = select(ChecklistExecution).where(
        ChecklistExecution.checklist_id == checklist_id,
        ChecklistExecution.execution_date == execution_date,
    )
    return session.scalar(statement)


def get_task_execution(
    session: Session, execution_id: int, task_id: int
) -> TaskExecution | None:
    statement = select(TaskExecution).where(
        TaskExecution.execution_id == execution_id,
        TaskExecution.task_id == task_id,
    )
    return session.scalar(statement)


def list_active_checklist_ids(session: Session) -> list[int]:
    statement = (
        select(Checklist.id)
        .where(Checklist.is_active.is_(True))
        .order_by(Checklist.id)
    )
    return list(session.scalars(statement).all())


def list_open_execution_ids(session: Session) -> list[int]:
    statement = (
        select(ChecklistExecution.id)
        .where(
            ChecklistExecution.status.in_(
                (
                    ExecutionStatus.PENDING,
                    ExecutionStatus.IN_PROGRESS,
                    ExecutionStatus.OVERDUE,
                )
            )
        )
        .order_by(ChecklistExecution.id)
    )
    return list(session.scalars(statement).all())


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
        .options(
            selectinload(ChecklistExecution.checklist),
            selectinload(ChecklistExecution.task_executions).selectinload(
                TaskExecution.task
            ),
        )
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
    updated_at: datetime | None = None,
) -> ChecklistExecution:
    execution = ChecklistExecution(
        checklist_id=checklist_id,
        execution_date=execution_date,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        updated_at=updated_at,
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
    execution_id: int | None,
    message: str,
    status: str,
    notification_type: NotificationType,
    event_key: str,
    sent_at: datetime | None = None,
    error_message: str | None = None,
) -> NotificationLog:
    notification = NotificationLog(
        execution_id=execution_id,
        message=message,
        status=status,
        notification_type=notification_type.value,
        event_key=event_key,
        sent_at=sent_at,
        error_message=error_message,
    )
    session.add(notification)
    session.flush()
    return notification


def get_notification_by_event_key(
    session: Session, event_key: str
) -> NotificationLog | None:
    statement = select(NotificationLog).where(
        NotificationLog.event_key == event_key
    )
    return session.scalar(statement)


def has_deliverable_notifications(
    session: Session, *, reclaim_before: datetime
) -> bool:
    statement = (
        select(NotificationLog.id)
        .where(
            or_(
                NotificationLog.status == "pending",
                and_(
                    NotificationLog.status == "sending",
                    NotificationLog.updated_at < reclaim_before,
                ),
            )
        )
        .limit(1)
    )
    return session.scalar(statement) is not None


def claim_next_notification(
    session: Session,
    *,
    now: datetime,
    reclaim_before: datetime,
    exclude_ids: set[int] | None = None,
) -> tuple[int, str, str, int] | None:
    statement = (
        select(NotificationLog.id)
        .where(
            or_(
                NotificationLog.status == "pending",
                and_(
                    NotificationLog.status == "sending",
                    NotificationLog.updated_at < reclaim_before,
                ),
            )
        )
        .order_by(NotificationLog.id)
        .limit(1)
    )
    if exclude_ids:
        statement = statement.where(NotificationLog.id.not_in(exclude_ids))
    notification_id = session.scalar(statement)
    if notification_id is None:
        return None

    claim = (
        update(NotificationLog)
        .where(
            NotificationLog.id == notification_id,
            or_(
                NotificationLog.status == "pending",
                and_(
                    NotificationLog.status == "sending",
                    NotificationLog.updated_at < reclaim_before,
                ),
            ),
        )
        .values(
            status="sending",
            attempt_count=NotificationLog.attempt_count + 1,
            updated_at=now,
        )
    )
    if session.execute(claim).rowcount != 1:
        return None

    notification = session.get(NotificationLog, notification_id)
    if notification is None:
        return None
    return (
        notification.id,
        notification.event_key,
        notification.message,
        notification.attempt_count,
    )


def get_notification(session: Session, notification_id: int) -> NotificationLog | None:
    return session.get(NotificationLog, notification_id)


def update_notification_delivery(
    session: Session,
    notification_id: int,
    *,
    status: str,
    now: datetime,
    error_message: str | None = None,
    telegram_message_id: int | None = None,
) -> bool:
    notification = get_notification(session, notification_id)
    if notification is None:
        return False
    notification.status = status
    notification.sent_at = now if status == "sent" else None
    notification.error_message = error_message
    notification.telegram_message_id = telegram_message_id
    notification.updated_at = now
    session.flush()
    return True
