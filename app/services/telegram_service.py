import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import utc_now
from app.database.repositories import (
    claim_next_notification,
    has_deliverable_notifications,
    update_notification_delivery,
)

logger = logging.getLogger(__name__)
SessionFactory = Callable[[], Session]


class Sleeper(Protocol):
    def __call__(self, seconds: float) -> None: ...


class TelegramDeliveryError(Exception):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class NotificationDeliverySummary:
    sent: int = 0
    retrying: int = 0
    failed: int = 0
    errors: int = 0


class TelegramClient:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        timeout: float,
        max_attempts: int,
        retry_delay: float,
        transport: httpx.BaseTransport | None = None,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self._chat_id = chat_id
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        self._sleeper = sleeper
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
        )
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"

    def close(self) -> None:
        self._client.close()

    def send_message(self, message: str) -> None:
        last_error: TelegramDeliveryError | None = None
        for attempt in range(self._max_attempts):
            try:
                response = self._client.post(
                    self._url,
                    json={"chat_id": self._chat_id, "text": message},
                )
                if (
                    response.status_code in (408, 429)
                    or response.status_code >= 500
                ):
                    raise TelegramDeliveryError(
                        f"Telegram retornou HTTP {response.status_code}.",
                        retryable=True,
                    )
                if not response.is_success:
                    raise TelegramDeliveryError(
                        f"Telegram retornou HTTP {response.status_code}.",
                        retryable=False,
                    )
                try:
                    payload = response.json()
                except ValueError as error:
                    raise TelegramDeliveryError(
                        "Telegram retornou uma resposta inválida.",
                        retryable=True,
                    ) from error
                if not isinstance(payload, dict) or payload.get("ok") is not True:
                    raise TelegramDeliveryError(
                        "Telegram rejeitou a mensagem.",
                        retryable=False,
                    )
                return
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = TelegramDeliveryError(
                    f"Falha de comunicação com o Telegram ({type(error).__name__}).",
                    retryable=True,
                )
            except TelegramDeliveryError as error:
                last_error = error

            if not last_error.retryable or attempt + 1 >= self._max_attempts:
                raise last_error
            self._sleeper(self._retry_delay * (2**attempt))

        raise last_error or TelegramDeliveryError(
            "Falha de comunicação com o Telegram.", retryable=True
        )


def deliver_pending_notifications(
    session_factory: SessionFactory,
    *,
    now: datetime | None = None,
    telegram_client: TelegramClient | None = None,
    max_notifications: int = 100,
) -> NotificationDeliverySummary:
    checked_at = now or utc_now()
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("Notification delivery time must include timezone information.")
    checked_at = checked_at.astimezone(timezone.utc)
    summary = NotificationDeliverySummary()

    retry_window = max(
        60.0,
        settings.telegram_request_timeout_seconds
        * settings.telegram_retry_attempts
        + settings.telegram_retry_delay_seconds * settings.telegram_retry_attempts
        + 60.0,
    )
    reclaim_before = checked_at - timedelta(seconds=retry_window)
    try:
        with session_factory() as session:
            has_pending = has_deliverable_notifications(
                session, reclaim_before=reclaim_before
            )
    except SQLAlchemyError:
        logger.exception("Falha de banco ao consultar notificações pendentes.")
        summary.errors += 1
        return summary
    if not has_pending:
        return summary

    if telegram_client is None:
        token = settings.telegram_bot_token.get_secret_value()
        if not token or not settings.telegram_chat_id:
            logger.warning(
                "Telegram não configurado; as notificações permanecem pendentes."
            )
            summary.errors += 1
            return summary
        telegram_client = TelegramClient(
            token=token,
            chat_id=settings.telegram_chat_id,
            timeout=settings.telegram_request_timeout_seconds,
            max_attempts=settings.telegram_retry_attempts,
            retry_delay=settings.telegram_retry_delay_seconds,
        )
        owns_client = True
    else:
        owns_client = False

    attempted_ids: set[int] = set()

    try:
        for _ in range(max_notifications):
            notification = _claim_notification(
                session_factory,
                checked_at,
                reclaim_before,
                attempted_ids,
                summary,
            )
            if notification is None:
                break
            notification_id, event_key, message, attempt_count = notification
            attempted_ids.add(notification_id)
            try:
                telegram_client.send_message(message)
            except TelegramDeliveryError as error:
                status = "pending" if error.retryable else "failed"
                if not _finish_notification(
                    session_factory,
                    notification_id,
                    status=status,
                    now=checked_at,
                    error_message=str(error),
                    summary=summary,
                ):
                    continue
                if error.retryable:
                    summary.retrying += 1
                else:
                    summary.failed += 1
                summary.errors += 1
                logger.warning(
                    "Falha no envio da notificação %s (tentativa acumulada %d): %s",
                    event_key,
                    attempt_count,
                    error,
                )
            except Exception as error:
                safe_error = (
                    "Falha inesperada de envio "
                    f"({type(error).__name__})."
                )
                _finish_notification(
                    session_factory,
                    notification_id,
                    status="pending",
                    now=checked_at,
                    error_message=safe_error,
                    summary=summary,
                )
                summary.retrying += 1
                summary.errors += 1
                logger.error(
                    "Falha inesperada ao enviar notificação %s (%s).",
                    event_key,
                    type(error).__name__,
                )
            else:
                if _finish_notification(
                    session_factory,
                    notification_id,
                    status="sent",
                    now=checked_at,
                    error_message=None,
                    summary=summary,
                ):
                    summary.sent += 1
                    logger.info("Notificação %s enviada ao Telegram.", event_key)
    finally:
        if owns_client:
            telegram_client.close()

    return summary


def _claim_notification(
    session_factory: SessionFactory,
    now: datetime,
    reclaim_before: datetime,
    exclude_ids: set[int],
    summary: NotificationDeliverySummary,
) -> tuple[int, str, str, int] | None:
    try:
        with session_factory() as session:
            with session.begin():
                return claim_next_notification(
                    session,
                    now=now,
                    reclaim_before=reclaim_before,
                    exclude_ids=exclude_ids,
                )
    except SQLAlchemyError:
        logger.exception("Falha de banco ao reservar uma notificação pendente.")
        summary.errors += 1
        return None


def _finish_notification(
    session_factory: SessionFactory,
    notification_id: int,
    *,
    status: str,
    now: datetime,
    error_message: str | None,
    summary: NotificationDeliverySummary,
) -> bool:
    try:
        with session_factory() as session:
            with session.begin():
                return update_notification_delivery(
                    session,
                    notification_id,
                    status=status,
                    now=now,
                    error_message=error_message,
                )
    except SQLAlchemyError:
        logger.exception(
            "Falha de banco ao atualizar notificação %s.", notification_id
        )
        summary.errors += 1
        return False
