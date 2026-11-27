from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.domain.enums import ExecutionStatus
from app.schemas.checklist import TaskRead


class TaskExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    is_completed: bool
    completed_at: datetime | None
    updated_at: datetime
    task: TaskRead


class ChecklistExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checklist_id: int
    execution_date: date
    status: ExecutionStatus
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
    task_executions: list[TaskExecutionRead]

    @computed_field
    @property
    def completion_percentage(self) -> float:
        if not self.task_executions:
            return 0.0
        completed_count = sum(
            task_execution.is_completed
            for task_execution in self.task_executions
        )
        return round(completed_count * 100 / len(self.task_executions), 2)

    @computed_field
    @property
    def is_complete(self) -> bool:
        required_tasks = (
            task_execution
            for task_execution in self.task_executions
            if task_execution.task.is_required
        )
        return all(task_execution.is_completed for task_execution in required_tasks)

    @computed_field
    @property
    def is_incomplete(self) -> bool:
        return not self.is_complete

    @computed_field
    @property
    def is_overdue(self) -> bool:
        return self.status is ExecutionStatus.OVERDUE
