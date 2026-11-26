from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.security import require_admin_api_key
from app.database.models import Checklist
from app.database.session import get_db
from app.schemas.checklist import ChecklistCreate, ChecklistRead, ChecklistUpdate
from app.services.checklist_service import (
    create_checklist_record,
    delete_checklist_record,
    get_checklist_record,
    list_checklist_records,
    update_checklist_record,
)

router = APIRouter(
    prefix="/checklists",
    tags=["checklists"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.post(
    "", response_model=ChecklistRead, status_code=status.HTTP_201_CREATED
)
def create_checklist(
    data: ChecklistCreate, session: Annotated[Session, Depends(get_db)]
) -> Checklist:
    return create_checklist_record(session, data)


@router.get("", response_model=list[ChecklistRead])
def list_checklists(
    session: Annotated[Session, Depends(get_db)]
) -> list[Checklist]:
    return list_checklist_records(session)


@router.get("/{checklist_id}", response_model=ChecklistRead)
def get_checklist(
    checklist_id: int, session: Annotated[Session, Depends(get_db)]
) -> Checklist:
    return get_checklist_record(session, checklist_id)


@router.put("/{checklist_id}", response_model=ChecklistRead)
def update_checklist(
    checklist_id: int,
    data: ChecklistUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> Checklist:
    return update_checklist_record(session, checklist_id, data)


@router.delete(
    "/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_checklist(
    checklist_id: int, session: Annotated[Session, Depends(get_db)]
) -> Response:
    delete_checklist_record(session, checklist_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
