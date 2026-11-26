from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from app.database.models import (
    ChecklistExecution,
    NotificationLog,
    TaskExecution,
    utc_now,
)
from app.database.repositories import (
    get_notification_by_event_key,
)
from app.domain.enums import ExecutionStatus, NotificationType


def queue_execution_started(
    session: Session, execution: ChecklistExecution, timezone_name: str
) -> bool:
    local_started = execution.started_at
    if local_started is not None:
        local_started = local_started.astimezone(ZoneInfo(timezone_name))
    started_time = local_started.strftime("%H:%M") if local_started else "—"
    message = (
        "KITCHENCHECK — CHECKLIST INICIADO\n\n"
        f"Checklist: {execution.checklist.title}\n"
        f"Data: {execution.execution_date:%d/%m/%Y}\n"
        f"Horário: {started_time}"
    )
    return _queue(
        session,
        execution_id=execution.id,
        notification_type=NotificationType.CHECKLIST_STARTED,
        event_key=f"checklist-started:{execution.id}",
        message=message,
    )


def queue_execution_completed(
    session: Session, execution: ChecklistExecution, timezone_name: str
) -> bool:
    local_completed = execution.completed_at
    if local_completed is not None:
        local_completed = local_completed.astimezone(ZoneInfo(timezone_name))
    completed_time = local_completed.strftime("%H:%M") if local_completed else "—"
    completion = _completion_percentage(execution)
    message = (
        "KITCHENCHECK — CHECKLIST FINALIZADO\n\n"
        f"Checklist: {execution.checklist.title}\n"
        f"Conclusão: {completion}%\n"
        f"Horário: {completed_time}"
    )
    return _queue(
        session,
        execution_id=execution.id,
        notification_type=NotificationType.CHECKLIST_COMPLETED,
        event_key=f"checklist-completed:{execution.id}",
        message=message,
    )


def queue_execution_overdue(
    session: Session, execution: ChecklistExecution
) -> bool:
    pending = [
        item.task.title
        for item in execution.task_executions
        if item.task.is_required and not item.is_completed
    ]
    task_list = "\n".join(f"- {title}" for title in pending) or "- Nenhuma"
    message = (
        "KITCHENCHECK — ALERTA DE ATRASO\n\n"
        f"Checklist: {execution.checklist.title}\n\n"
        "Tarefas obrigatórias pendentes:\n"
        f"{task_list}\n"
        f"Conclusão: {_completion_percentage(execution)}%"
    )
    return _queue(
        session,
        execution_id=execution.id,
        notification_type=NotificationType.OVERDUE,
        event_key=f"checklist-overdue:{execution.id}",
        message=message,
    )


def queue_daily_summary(session: Session, operation_date: date) -> bool:
    event_key = f"daily-summary:{operation_date.isoformat()}"
    if get_notification_by_event_key(session, event_key) is not None:
        return False

    statement = (
        select(ChecklistExecution)
        .options(
            selectinload(ChecklistExecution.checklist),
            selectinload(ChecklistExecution.task_executions).selectinload(
                TaskExecution.task
            ),
        )
        .where(ChecklistExecution.execution_date == operation_date)
        .order_by(ChecklistExecution.id)
    )
    executions = list(session.scalars(statement).all())
    completed = sum(
        execution.status is ExecutionStatus.COMPLETED
        for execution in executions
    )
    overdue = sum(
        execution.status is ExecutionStatus.OVERDUE for execution in executions
    )
    pending_tasks = sum(
        not task_execution.is_completed
        for execution in executions
        for task_execution in execution.task_executions
    )
    total_tasks = sum(
        len(execution.task_executions) for execution in executions
    )
    completed_tasks = total_tasks - pending_tasks
    percent = round(completed_tasks / total_tasks * 100) if total_tasks else 0
    message = (
        "KITCHENCHECK — RESUMO DO DIA\n\n"
        f"Data operacional: {operation_date:%d/%m/%Y}\n"
        f"Checklists iniciados: {len(executions)}\n"
        f"Finalizados: {completed}\n"
        f"Atrasados: {overdue}\n"
        f"Tarefas pendentes: {pending_tasks}\n"
        f"Conclusão geral: {percent}%"
    )
    return _queue(
        session,
        execution_id=None,
        notification_type=NotificationType.DAILY_SUMMARY,
        event_key=event_key,
        message=message,
    )


def _queue(
    session: Session,
    *,
    execution_id: int | None,
    notification_type: NotificationType,
    event_key: str,
    message: str,
) -> bool:
    if get_notification_by_event_key(session, event_key) is not None:
        return False
    statement = sqlite_insert(NotificationLog).values(
        execution_id=execution_id,
        message=message,
        status="pending",
        notification_type=notification_type.value,
        event_key=event_key,
        attempt_count=0,
        updated_at=utc_now(),
    )
    result = session.execute(
        statement.on_conflict_do_nothing(index_elements=["event_key"])
    )
    return result.rowcount == 1


def _completion_percentage(execution: ChecklistExecution) -> int:
    total = len(execution.task_executions)
    if not total:
        return 0
    completed = sum(
        task_execution.is_completed
        for task_execution in execution.task_executions
    )
    return round(completed / total * 100)
