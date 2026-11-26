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
