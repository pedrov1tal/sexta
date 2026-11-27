from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.init import initialize_database
from app.database.models import NotificationLog
from app.database.repositories import (
    create_checklist,
    create_checklist_execution,
    create_task,
    create_task_execution,
)
from app.database.session import create_database_engine
from app.domain.enums import ChecklistType, ExecutionStatus, NotificationType
from app.services.notification_service import (
    queue_daily_summary,
    queue_execution_completed,
    queue_execution_started,
)
from app.services.telegram_service import (
    TelegramClient,
    deliver_pending_notifications,
)


@pytest.fixture
def session_factory(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'telegram-test.db'}")
    initialize_database(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def enqueue_daily_summary(session_factory) -> None:
    with session_factory() as session:
        with session.begin():
            assert queue_daily_summary(session, date(2026, 11, 25))


def make_client(handler, *, attempts=2, captured_sleeps=None):
    return TelegramClient(
        token="test-token-never-log",
        chat_id="12345",
        timeout=1,
        max_attempts=attempts,
        retry_delay=0,
        transport=httpx.MockTransport(handler),
        sleeper=(captured_sleeps.append if captured_sleeps is not None else lambda _: None),
    )


def test_telegram_client_uses_https_and_retries_temporary_http_errors(
    caplog,
) -> None:
    responses = iter(
        [
            httpx.Response(503, json={"ok": False}),
            httpx.Response(
                200, json={"ok": True, "result": {"message_id": 101}}
            ),
        ]
    )
    requests = []
    client = make_client(
        lambda request: requests.append(request) or next(responses)
    )
    try:
        assert client.send_message("Mensagem de teste") == 101
    finally:
        client.close()

    assert len(requests) == 2
    assert requests[0].url.scheme == "https"
    assert requests[0].read() == (
        b'{"chat_id":"12345","text":"Mensagem de teste"}'
    )
    assert "test-token-never-log" not in caplog.text


def test_outbox_sends_once_and_persists_delivery(session_factory) -> None:
    enqueue_daily_summary(session_factory)
    request_count = 0

    def handler(_request):
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200, json={"ok": True, "result": {"message_id": 101}}
        )

    client = make_client(handler)
    now = datetime(2026, 11, 25, 23, 0, tzinfo=timezone.utc)
    try:
        first_delivery = deliver_pending_notifications(
            session_factory, now=now, telegram_client=client
        )
        repeated_delivery = deliver_pending_notifications(
            session_factory, now=now, telegram_client=client
        )
    finally:
        client.close()

    with session_factory() as session:
        notification = session.scalar(select(NotificationLog))

    assert first_delivery.sent == 1
    assert repeated_delivery.sent == 0
    assert request_count == 1
    assert notification is not None
    assert notification.execution_id is None
    assert notification.status == "sent"
    assert notification.sent_at == now
    assert notification.attempt_count == 1
    assert notification.telegram_message_id == 101


def test_temporary_failure_is_retried_on_next_automation_cycle(
    session_factory, caplog
) -> None:
    enqueue_daily_summary(session_factory)
    failing_client = make_client(
        lambda _request: httpx.Response(503, json={"ok": False})
    )
    now = datetime(2026, 11, 25, 23, 0, tzinfo=timezone.utc)
    try:
        failed_delivery = deliver_pending_notifications(
            session_factory, now=now, telegram_client=failing_client
        )
    finally:
        failing_client.close()

    successful_client = make_client(
        lambda _request: httpx.Response(
            200, json={"ok": True, "result": {"message_id": 102}}
        ),
        attempts=1,
    )
    try:
        retried_delivery = deliver_pending_notifications(
            session_factory,
            now=now.replace(minute=1),
            telegram_client=successful_client,
        )
    finally:
        successful_client.close()

    with session_factory() as session:
        notification = session.scalar(select(NotificationLog))

    assert failed_delivery.retrying == 1
    assert retried_delivery.sent == 1
    assert notification is not None
    assert notification.status == "sent"
    assert notification.attempt_count == 2
    assert notification.error_message is None
    assert notification.telegram_message_id == 102
    assert "test-token-never-log" not in caplog.text


def test_permanent_http_error_is_recorded_without_retrying(session_factory) -> None:
    enqueue_daily_summary(session_factory)
    request_count = 0

    def handler(_request):
        nonlocal request_count
        request_count += 1
        return httpx.Response(401, json={"ok": False})

    client = make_client(handler, attempts=3)
    try:
        result = deliver_pending_notifications(
            session_factory,
            now=datetime(2026, 11, 25, 23, 0, tzinfo=timezone.utc),
            telegram_client=client,
        )
    finally:
        client.close()

    with session_factory() as session:
        notification = session.scalar(select(NotificationLog))

    assert result.failed == 1
    assert request_count == 1
    assert notification is not None
    assert notification.status == "failed"
    assert notification.attempt_count == 1
    assert notification.error_message == "Telegram retornou HTTP 401."


def test_execution_notifications_are_formatted_and_deduplicated(
    session_factory,
) -> None:
    started_at = datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
    with session_factory() as session:
        with session.begin():
            checklist = create_checklist(
                session,
                title="Abertura da cozinha",
                checklist_type=ChecklistType.OPENING,
            )
            task = create_task(
                session,
                checklist_id=checklist.id,
                title="Conferir equipamentos",
                position=0,
            )
            execution = create_checklist_execution(
                session,
                checklist_id=checklist.id,
                execution_date=date(2026, 11, 25),
                status=ExecutionStatus.IN_PROGRESS,
                started_at=started_at,
            )
            task_execution = create_task_execution(
                session,
                execution_id=execution.id,
                task_id=task.id,
            )
            assert queue_execution_started(session, execution, "UTC")
            assert not queue_execution_started(session, execution, "UTC")

            task_execution.is_completed = True
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = started_at.replace(hour=8, minute=15)
            assert queue_execution_completed(session, execution, "UTC")

    with session_factory() as session:
        notifications = list(
            session.scalars(
                select(NotificationLog).order_by(NotificationLog.id)
            )
        )

    assert len(notifications) == 2
    assert notifications[0].notification_type == NotificationType.CHECKLIST_STARTED.value
    assert "Checklist: Abertura da cozinha" in notifications[0].message
    assert notifications[1].notification_type == NotificationType.CHECKLIST_COMPLETED.value
    assert "Conclusão: 100%" in notifications[1].message
