from enum import Enum


class ChecklistType(str, Enum):
    OPENING = "opening"
    OPERATION = "operation"
    CLOSING = "closing"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class NotificationType(str, Enum):
    CHECKLIST_STARTED = "checklist_started"
    OVERDUE = "overdue"
    CHECKLIST_COMPLETED = "checklist_completed"
    DAILY_SUMMARY = "daily_summary"
