from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import ChecklistExecution
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

        started_at = datetime.now(timezone.utc)
        execution = create_checklist_execution(
            session,
            checklist_id=checklist.id,
            execution_date=started_at.date(),
            status=ExecutionStatus.IN_PROGRESS,
            started_at=started_at,
        )
        create_task_executions(
            session,
            execution_id=execution.id,
            task_ids=[task.id for task in tasks],
        )
    return execution


def list_execution_records(
    session: Session, *, skip: int = 0, limit: int = 100
) -> list[ChecklistExecution]:
    return list_checklist_executions(session, skip=skip, limit=limit)


def get_execution_record(
    session: Session, execution_id: int
) -> ChecklistExecution:
    execution = get_checklist_execution(session, execution_id)
    if execution is None:
        raise ResourceNotFoundError("Execução não encontrada.")
    return execution


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
        if not task_execution.is_completed:
            task_execution.is_completed = True
            task_execution.completed_at = datetime.now(timezone.utc)

        task_executions = list(execution.task_executions)
        if task_executions and all(item.is_completed for item in task_executions):
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
    return execution
