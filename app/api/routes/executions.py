from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.security import require_admin_api_key
from app.database.models import ChecklistExecution
from app.database.session import get_db
from app.schemas.execution import ChecklistExecutionRead
from app.services.execution_service import (
    complete_execution_task,
    get_execution_record,
    list_execution_records,
    start_checklist_execution,
)

router = APIRouter(
    tags=["executions"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.post(
    "/checklists/{checklist_id}/executions",
    response_model=ChecklistExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def start_execution(
    checklist_id: int, session: Annotated[Session, Depends(get_db)]
) -> ChecklistExecution:
    return start_checklist_execution(session, checklist_id)


@router.get("/executions", response_model=list[ChecklistExecutionRead])
def list_executions(
    session: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ChecklistExecution]:
    return list_execution_records(session, skip=skip, limit=limit)


@router.get("/executions/{execution_id}", response_model=ChecklistExecutionRead)
def get_execution(
    execution_id: int, session: Annotated[Session, Depends(get_db)]
) -> ChecklistExecution:
    return get_execution_record(session, execution_id)


@router.patch(
    "/executions/{execution_id}/tasks/{task_id}",
    response_model=ChecklistExecutionRead,
)
def complete_task(
    execution_id: int,
    task_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> ChecklistExecution:
    return complete_execution_task(session, execution_id, task_id)
