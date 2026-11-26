from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ExecutionStatus
from app.schemas.checklist import TaskRead


class TaskExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    is_completed: bool
    completed_at: datetime | None
    task: TaskRead


class ChecklistExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checklist_id: int
    execution_date: date
    status: ExecutionStatus
    started_at: datetime | None
    completed_at: datetime | None
    task_executions: list[TaskExecutionRead]
