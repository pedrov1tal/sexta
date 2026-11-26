import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import utc_now
from app.database.repositories import (
    create_checklist_execution,
    create_task_executions,
    get_checklist,
    get_checklist_execution,
    get_checklist_execution_for_date,
    list_active_checklist_ids,
    list_open_execution_ids,
)
from app.domain.enums import ExecutionStatus
from app.services.execution_service import refresh_execution_status

logger = logging.getLogger(__name__)
SessionFactory = Callable[[], Session]


@dataclass
class AutomationCheckSummary:
    active_checklists: int = 0
    inspected_executions: int = 0
    started_executions: int = 0
    pending_executions: int = 0
    pending_tasks: int = 0
    overdue_executions: int = 0
    notification_events: int = 0
    skipped_without_tasks: int = 0
    errors: int = 0


def run_automation_check(
    session_factory: SessionFactory, now: datetime | None = None
) -> AutomationCheckSummary:
    checked_at = now or utc_now()
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("Automation check time must include timezone information.")
    checked_at = checked_at.astimezone(timezone.utc)
    operation_timezone = ZoneInfo(settings.operation_timezone)
    local_now = checked_at.astimezone(operation_timezone)
    summary = AutomationCheckSummary()

    logger.info(
        "Verificação automática iniciada em %s (fuso %s).",
        checked_at.isoformat(),
        settings.operation_timezone,
    )
    try:
        with session_factory() as session:
            checklist_ids = list_active_checklist_ids(session)
            summary.active_checklists = len(checklist_ids)
            execution_ids = list_open_execution_ids(session)
    except SQLAlchemyError:
        logger.exception("Falha ao consultar o banco durante a verificação.")
        summary.errors += 1
        return summary

    for execution_id in execution_ids:
        _inspect_execution(
            session_factory, execution_id, checked_at, summary
        )

    for checklist_id in checklist_ids:
        execution_id = _start_due_execution(
            session_factory,
            checklist_id,
            local_now,
            checked_at,
            summary,
        )
        if execution_id is not None:
            _inspect_execution(
                session_factory, execution_id, checked_at, summary
            )

    logger.info(
        "Verificação concluída: checklists ativos=%d, execuções iniciadas=%d, "
        "execuções com pendências=%d, tarefas pendentes=%d, atrasadas=%d, "
        "eventos=%d, ignoradas sem tarefas=%d, falhas=%d.",
        summary.active_checklists,
        summary.started_executions,
        summary.pending_executions,
        summary.pending_tasks,
        summary.overdue_executions,
        summary.notification_events,
        summary.skipped_without_tasks,
        summary.errors,
    )
    return summary


def _start_due_execution(
    session_factory: SessionFactory,
    checklist_id: int,
    local_now: datetime,
    checked_at: datetime,
    summary: AutomationCheckSummary,
) -> int | None:
    try:
        with session_factory() as session:
            with session.begin():
                checklist = get_checklist(session, checklist_id)
                if checklist is None or not checklist.is_active:
                    return None
                if checklist.scheduled_time is None:
                    return None
                if local_now.timetz().replace(tzinfo=None) < checklist.scheduled_time:
                    return None

                execution_date = local_now.date()
                if get_checklist_execution_for_date(
                    session, checklist.id, execution_date
                ):
                    return None

                tasks = list(checklist.tasks)
                if not tasks:
                    logger.warning(
                        "Checklist %s (%s) está ativo, mas não possui tarefas; "
                        "execução não iniciada.",
                        checklist.id,
                        checklist.title,
                    )
                    summary.skipped_without_tasks += 1
                    return None

                required_tasks = [task for task in tasks if task.is_required]
                execution = create_checklist_execution(
                    session,
                    checklist_id=checklist.id,
                    execution_date=execution_date,
                    status=(
                        ExecutionStatus.IN_PROGRESS
                        if required_tasks
                        else ExecutionStatus.COMPLETED
                    ),
                    started_at=checked_at,
                    completed_at=None if required_tasks else checked_at,
                    updated_at=checked_at,
                )
                create_task_executions(
                    session,
                    execution_id=execution.id,
                    task_ids=[task.id for task in tasks],
                )
                execution_id = execution.id
        summary.started_executions += 1
        logger.info(
            "Execução %s iniciada para checklist %s na data operacional %s.",
            execution_id,
            checklist_id,
            local_now.date(),
        )
        return execution_id
    except SQLAlchemyError:
        logger.exception(
            "Falha de banco ao iniciar checklist %s; será reavaliado na próxima "
            "verificação.",
            checklist_id,
        )
        summary.errors += 1
        return None
    except Exception:
        logger.exception(
            "Falha inesperada ao iniciar checklist %s.", checklist_id
        )
        summary.errors += 1
        return None


def _inspect_execution(
    session_factory: SessionFactory,
    execution_id: int,
    checked_at: datetime,
    summary: AutomationCheckSummary,
) -> None:
    notification_created = False
    has_execution = False
    pending_count = 0
    is_overdue = False
    try:
        with session_factory() as session:
            with session.begin():
                execution = get_checklist_execution(session, execution_id)
                if execution is None:
                    return

                has_execution = True
                notification_created = refresh_execution_status(
                    session, execution, checked_at
                )
                task_executions = list(execution.task_executions)
                pending_tasks = [
                    task_execution
                    for task_execution in task_executions
                    if not task_execution.is_completed
                ]
                pending_count = len(pending_tasks)
                is_overdue = execution.status is ExecutionStatus.OVERDUE
                logger.info(
                    "Execução %s verificada: status=%s, tarefas pendentes=%d.",
                    execution.id,
                    execution.status.value,
                    pending_count,
                )
    except SQLAlchemyError:
        logger.exception(
            "Falha de banco ao verificar execução %s.", execution_id
        )
        summary.errors += 1
        return
    except Exception:
        logger.exception(
            "Falha inesperada ao verificar execução %s.", execution_id
        )
        summary.errors += 1
        return

    if not has_execution:
        return
    summary.inspected_executions += 1
    if pending_count:
        summary.pending_executions += 1
        summary.pending_tasks += pending_count
    if is_overdue:
        summary.overdue_executions += 1
    if notification_created:
        summary.notification_events += 1
