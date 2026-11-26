from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Checklist, Task
from app.database.repositories import (
    create_checklist,
    create_task,
    get_checklist,
    get_task,
    list_checklists,
    list_tasks,
)
from app.schemas.checklist import ChecklistCreate, ChecklistUpdate, TaskCreate, TaskUpdate
from app.services.exceptions import ResourceConflictError, ResourceNotFoundError


def create_checklist_record(
    session: Session, data: ChecklistCreate
) -> Checklist:
    with session.begin():
        return create_checklist(session, **data.model_dump())


def list_checklist_records(session: Session) -> list[Checklist]:
    return list_checklists(session)


def get_checklist_record(session: Session, checklist_id: int) -> Checklist:
    checklist = get_checklist(session, checklist_id)
    if checklist is None:
        raise ResourceNotFoundError("Checklist não encontrado.")
    return checklist


def update_checklist_record(
    session: Session, checklist_id: int, data: ChecklistUpdate
) -> Checklist:
    with session.begin():
        checklist = get_checklist(session, checklist_id)
        if checklist is None:
            raise ResourceNotFoundError("Checklist não encontrado.")
        for field, value in data.model_dump().items():
            setattr(checklist, field, value)
    return checklist


def delete_checklist_record(session: Session, checklist_id: int) -> None:
    with session.begin():
        checklist = get_checklist(session, checklist_id)
        if checklist is None:
            raise ResourceNotFoundError("Checklist não encontrado.")
        if checklist.executions:
            raise ResourceConflictError(
                "Não é possível excluir um checklist com execuções registradas."
            )
        session.delete(checklist)


def create_task_record(
    session: Session, checklist_id: int, data: TaskCreate
) -> Task:
    try:
        with session.begin():
            if get_checklist(session, checklist_id) is None:
                raise ResourceNotFoundError("Checklist não encontrado.")
            return create_task(
                session,
                checklist_id=checklist_id,
                **data.model_dump(),
            )
    except IntegrityError as error:
        raise ResourceConflictError(
            "Já existe uma tarefa nessa posição do checklist."
        ) from error


def list_task_records(session: Session, checklist_id: int) -> list[Task]:
    if get_checklist(session, checklist_id) is None:
        raise ResourceNotFoundError("Checklist não encontrado.")
    return list_tasks(session, checklist_id)


def update_task_record(
    session: Session, task_id: int, data: TaskUpdate
) -> Task:
    try:
        with session.begin():
            task = get_task(session, task_id)
            if task is None:
                raise ResourceNotFoundError("Tarefa não encontrada.")
            if task.task_executions and task.is_required != data.is_required:
                raise ResourceConflictError(
                    "Não é possível alterar a obrigatoriedade de uma tarefa "
                    "que já possui histórico de execução."
                )
            for field, value in data.model_dump().items():
                setattr(task, field, value)
    except IntegrityError as error:
        raise ResourceConflictError(
            "Já existe uma tarefa nessa posição do checklist."
        ) from error
    return task


def delete_task_record(session: Session, task_id: int) -> None:
    with session.begin():
        task = get_task(session, task_id)
        if task is None:
            raise ResourceNotFoundError("Tarefa não encontrada.")
        if task.task_executions:
            raise ResourceConflictError(
                "Não é possível excluir uma tarefa que já foi executada."
            )
        session.delete(task)
