from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.security import require_admin_api_key
from app.database.models import Task
from app.database.session import get_db
from app.schemas.checklist import TaskCreate, TaskRead, TaskUpdate
from app.services.checklist_service import (
    create_task_record,
    delete_task_record,
    list_task_records,
    update_task_record,
)

router = APIRouter(
    tags=["tasks"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.post(
    "/checklists/{checklist_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    checklist_id: int,
    data: TaskCreate,
    session: Annotated[Session, Depends(get_db)],
) -> Task:
    return create_task_record(session, checklist_id, data)


@router.get("/checklists/{checklist_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    checklist_id: int, session: Annotated[Session, Depends(get_db)]
) -> list[Task]:
    return list_task_records(session, checklist_id)


@router.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    data: TaskUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> Task:
    return update_task_record(session, task_id, data)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int, session: Annotated[Session, Depends(get_db)]
) -> Response:
    delete_task_record(session, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
