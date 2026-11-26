from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import ChecklistExecution, utc_now
from app.domain.enums import ExecutionStatus
from app.database.repositories import (
    create_checklist_execution,
    create_task_executions,
    get_checklist,
    get_checklist_execution,
    get_task_execution,
    list_checklist_executions,
)
from app.services.exceptions import ResourceConflictError, ResourceNotFoundError


def start_checklist_execution(
    session: Session, checklist_id: int
) -> ChecklistExecution:
    with session.begin():
        checklist = get_checklist(session, checklist_id)
        if checklist is None:
            raise ResourceNotFoundError("Checklist não encontrado.")
        if not checklist.is_active:
            raise ResourceConflictError(
                "Não é possível iniciar um checklist inativo."
            )
        tasks = list(checklist.tasks)
        if not tasks:
            raise ResourceConflictError(
                "Adicione ao menos uma tarefa antes de iniciar a execução."
            )

        started_at = utc_now()
        operation_timezone = ZoneInfo(settings.operation_timezone)
        required_tasks = [task for task in tasks if task.is_required]
        execution = create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=started_at.astimezone(operation_timezone).date(),
            status=(
                ExecutionStatus.IN_PROGRESS
                if required_tasks
                else ExecutionStatus.COMPLETED
            ),
            started_at=started_at,
            completed_at=None if required_tasks else started_at,
            updated_at=started_at,
        )
        create_task_executions(
            session,
            execution_id=execution.id,
            task_ids=[task.id for task in tasks],
        )
        refresh_execution_status(execution, started_at)
    return execution


def list_execution_records(
    session: Session, *, skip: int = 0, limit: int = 100
) -> list[ChecklistExecution]:
    now = utc_now()
    with session.begin():
        executions = list_checklist_executions(session, skip=skip, limit=limit)
        for execution in executions:
            refresh_execution_status(execution, now)
    return executions


def get_execution_record(
    session: Session, execution_id: int
) -> ChecklistExecution:
    with session.begin():
        execution = get_checklist_execution(session, execution_id)
        if execution is None:
            raise ResourceNotFoundError("Execução não encontrada.")
        refresh_execution_status(execution, utc_now())
    return execution


def refresh_execution_status(
    execution: ChecklistExecution, now: datetime
) -> None:
    if execution.status is ExecutionStatus.COMPLETED:
        return

    task_executions = list(execution.task_executions)
    required_executions = [
        task_execution
        for task_execution in task_executions
        if task_execution.task.is_required
    ]
    if (
        execution.status is not ExecutionStatus.PENDING
        and all(item.is_completed for item in required_executions)
    ):
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = now
        execution.updated_at = now
        return

    deadline = _execution_deadline(execution)
    if (
        execution.status in (ExecutionStatus.PENDING, ExecutionStatus.IN_PROGRESS)
        and deadline is not None
        and now > deadline
    ):
        execution.status = ExecutionStatus.OVERDUE
        execution.updated_at = now


def _execution_deadline(execution: ChecklistExecution) -> datetime | None:
    checklist = execution.checklist
    if checklist.deadline is None:
        return None

    deadline_date = execution.execution_date
    if (
        checklist.scheduled_time is not None
        and checklist.deadline < checklist.scheduled_time
    ):
        deadline_date += timedelta(days=1)

    operation_timezone = ZoneInfo(settings.operation_timezone)
    local_deadline = datetime.combine(
        deadline_date, checklist.deadline
    ).replace(tzinfo=operation_timezone)
    return local_deadline.astimezone(timezone.utc)


def complete_execution_task(
    session: Session, execution_id: int, task_id: int
) -> ChecklistExecution:
    with session.begin():
        execution = get_checklist_execution(session, execution_id)
        if execution is None:
            raise ResourceNotFoundError("Execução não encontrada.")
        task_execution = get_task_execution(session, execution_id, task_id)
        if task_execution is None:
            raise ResourceNotFoundError(
                "A tarefa não pertence a esta execução."
            )
        if execution.status is ExecutionStatus.COMPLETED:
            raise ResourceConflictError("A execução já foi concluída.")
        now = utc_now()
        refresh_execution_status(execution, now)
        if not task_execution.is_completed:
            task_execution.is_completed = True
            task_execution.completed_at = now
            task_execution.updated_at = now

        required_task_executions = [
            item
            for item in execution.task_executions
            if item.task.is_required
        ]
        if all(item.is_completed for item in required_task_executions):
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = now
            execution.updated_at = now
    return execution
