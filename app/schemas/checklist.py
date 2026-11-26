from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import ChecklistType


class ChecklistFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    checklist_type: ChecklistType
    scheduled_time: time | None = None
    deadline: time | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("O título não pode ficar vazio.")
        return title


class ChecklistCreate(ChecklistFields):
    is_active: bool = True


class ChecklistUpdate(ChecklistFields):
    is_active: bool


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_required: bool = True
    position: int = Field(ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("O título não pode ficar vazio.")
        return title


class TaskUpdate(TaskCreate):
    pass


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checklist_id: int
    title: str
    description: str | None
    is_required: bool
    position: int


class ChecklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    checklist_type: ChecklistType
    scheduled_time: time | None
    deadline: time | None
    is_active: bool
    created_at: datetime
    tasks: list[TaskRead]
