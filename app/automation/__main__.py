import argparse
import logging
from threading import Event
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database.session import SessionLocal
from app.automation.engine import run_automation_check

logger = logging.getLogger(__name__)


def _run_scheduled_check() -> None:
    try:
        summary = run_automation_check(SessionLocal)
        if summary.errors:
            logger.error(
                "Verificação automática terminou com %d falha(s).",
                summary.errors,
            )
    except Exception:
        logger.exception(
            "Falha inesperada na verificação; o agendador continuará ativo."
        )


def main() -> int:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Motor de automação KitchenCheck.")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Executa uma verificação e encerra, para testes e demonstrações.",
    )
    arguments = parser.parse_args()

    if arguments.run_once:
        summary = run_automation_check(SessionLocal)
        return 1 if summary.errors else 0

    interval = settings.automation_interval_minutes
    scheduler = BackgroundScheduler(
        timezone=ZoneInfo(settings.operation_timezone),
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": max(60, interval * 60),
        },
    )
    scheduler.add_job(
        _run_scheduled_check,
        trigger="interval",
        minutes=interval,
        id="kitchencheck-monitor",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Motor de automação iniciado: intervalo=%d minuto(s), fuso=%s.",
        interval,
        settings.operation_timezone,
    )

    try:
        Event().wait()
    except KeyboardInterrupt:
        logger.info("Encerrando o motor de automação.")
    finally:
        scheduler.shutdown(wait=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
