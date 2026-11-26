from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import UTCDateTime
from app.domain.enums import ChecklistType, ExecutionStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Checklist(Base):
    __tablename__ = "checklists"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
        Index("ix_checklists_type_active", "checklist_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_type: Mapped[ChecklistType] = mapped_column(
        SqlEnum(
            ChecklistType,
            name="checklist_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            validate_strings=True,
        ),
        nullable=False,
    )
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    deadline: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Task.position",
    )
    executions: Mapped[list["ChecklistExecution"]] = relationship(
        back_populates="checklist",
        passive_deletes="all",
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("checklist_id", "position", name="uq_tasks_checklist_position"),
        Index("ix_tasks_checklist_id", "checklist_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    checklist: Mapped["Checklist"] = relationship(back_populates="tasks")
    task_executions: Mapped[list["TaskExecution"]] = relationship(
        back_populates="task",
        passive_deletes="all",
    )


class ChecklistExecution(Base):
    __tablename__ = "checklist_executions"
    __table_args__ = (
        Index(
            "uq_checklist_execution_date",
            "checklist_id",
            "execution_date",
            unique=True,
        ),
        Index("ix_executions_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id", ondelete="RESTRICT"), nullable=False
    )
    execution_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        SqlEnum(
            ExecutionStatus,
            name="execution_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            validate_strings=True,
        ),
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default=ExecutionStatus.PENDING.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    checklist: Mapped["Checklist"] = relationship(back_populates="executions")
    task_executions: Mapped[list["TaskExecution"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TaskExecution(Base):
    __tablename__ = "task_executions"
    __table_args__ = (
        UniqueConstraint(
            "execution_id", "task_id", name="uq_task_executions_execution_task"
        ),
        Index("ix_task_executions_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_executions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    execution: Mapped["ChecklistExecution"] = relationship(
        back_populates="task_executions"
    )
    task: Mapped["Task"] = relationship(back_populates="task_executions")


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        CheckConstraint("length(trim(message)) > 0", name="message_not_empty"),
        CheckConstraint("length(trim(status)) > 0", name="status_not_empty"),
        Index("ix_notification_logs_execution_status", "execution_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_executions.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    execution: Mapped["ChecklistExecution"] = relationship(
        back_populates="notification_logs"
    )
