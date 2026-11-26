from datetime import datetime, time, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.database.base import Base
from app.database.models import NotificationLog
from app.database.session import create_database_engine, get_db
from app.domain.enums import NotificationType
from app.main import app
from app.services import execution_service

API_KEY = "test-kitchencheck-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'api-test.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "admin_api_key", SecretStr(API_KEY))

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.app.state.test_engine = engine
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
    del test_client.app.state.test_engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_checklist(client: TestClient, *, title: str = "Abertura") -> dict:
    response = client.post(
        "/checklists",
        headers=AUTH_HEADERS,
        json={
            "title": title,
            "description": "Rotina diária",
            "checklist_type": "opening",
            "scheduled_time": "08:00:00",
            "deadline": "08:30:00",
        },
    )
    assert response.status_code == 201
    assert is_utc_timestamp(response.json()["created_at"])
    assert is_utc_timestamp(response.json()["updated_at"])
    return response.json()


def is_utc_timestamp(value: str) -> bool:
    normalized = value.replace("Z", "+00:00")
    timestamp = datetime.fromisoformat(normalized)
    return timestamp.utcoffset() == timezone.utc.utcoffset(timestamp)


def test_resource_routes_require_api_key(client: TestClient, monkeypatch) -> None:
    assert client.get("/checklists").status_code == 401
    assert client.get(
        "/checklists", headers={"X-API-Key": "incorrect-key"}
    ).status_code == 403

    monkeypatch.setattr(settings, "admin_api_key", SecretStr(""))
    response = client.get("/checklists", headers=AUTH_HEADERS)
    assert response.status_code == 503
    assert API_KEY not in response.text


def test_checklist_and_task_crud_and_validation(client: TestClient) -> None:
    checklist = create_checklist(client)
    checklist_id = checklist["id"]

    assert client.get("/checklists", headers=AUTH_HEADERS).json()[0]["id"] == (
        checklist_id
    )
    assert client.get(
        f"/checklists/{checklist_id}", headers=AUTH_HEADERS
    ).status_code == 200
    assert client.get(
        "/checklists/9999", headers=AUTH_HEADERS
    ).status_code == 404

    invalid = client.post(
        "/checklists",
        headers=AUTH_HEADERS,
        json={"title": "Inválido", "checklist_type": "unknown"},
    )
    assert invalid.status_code == 422

    updated = client.put(
        f"/checklists/{checklist_id}",
        headers=AUTH_HEADERS,
        json={
            "title": "Abertura atualizada",
            "description": None,
            "checklist_type": "opening",
            "scheduled_time": "08:15:00",
            "deadline": "08:45:00",
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Abertura atualizada"
    assert updated.json()["scheduled_time"] == time(8, 15).isoformat()
    assert is_utc_timestamp(updated.json()["updated_at"])

    task_response = client.post(
        f"/checklists/{checklist_id}/tasks",
        headers=AUTH_HEADERS,
        json={
            "title": "Verificar forno",
            "description": "Checar temperatura",
            "is_required": True,
            "position": 0,
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    assert client.get(
        f"/checklists/{checklist_id}/tasks", headers=AUTH_HEADERS
    ).json()[0]["id"] == task_id

    task_updated = client.put(
        f"/tasks/{task_id}",
        headers=AUTH_HEADERS,
        json={
            "title": "Verificar forno industrial",
            "description": None,
            "is_required": False,
            "position": 1,
        },
    )
    assert task_updated.status_code == 200
    assert task_updated.json()["is_required"] is False
    assert is_utc_timestamp(task_updated.json()["updated_at"])
    assert client.delete(f"/tasks/{task_id}", headers=AUTH_HEADERS).status_code == 204
    assert client.delete(
        f"/checklists/{checklist_id}", headers=AUTH_HEADERS
    ).status_code == 204


def test_execution_task_completion_and_protected_history(
    client: TestClient,
) -> None:
    checklist = create_checklist(client)
    checklist_id = checklist["id"]
    task_ids = []
    for position in range(2):
        response = client.post(
            f"/checklists/{checklist_id}/tasks",
            headers=AUTH_HEADERS,
            json={
                "title": f"Tarefa {position + 1}",
                "is_required": position == 0,
                "position": position,
            },
        )
        assert response.status_code == 201
        task_ids.append(response.json()["id"])

    started = client.post(
        f"/checklists/{checklist_id}/executions", headers=AUTH_HEADERS
    )
    assert started.status_code == 201
    execution = started.json()
    execution_id = execution["id"]
    assert execution["status"] == "in_progress"
    assert is_utc_timestamp(execution["started_at"])
    assert len(execution["task_executions"]) == 2
    assert execution["completion_percentage"] == 0
    assert execution["is_incomplete"] is True
    assert client.post(
        f"/checklists/{checklist_id}/executions", headers=AUTH_HEADERS
    ).status_code == 409
    assert client.put(
        f"/checklists/{checklist_id}",
        headers=AUTH_HEADERS,
        json={
            "title": checklist["title"],
            "description": checklist["description"],
            "checklist_type": checklist["checklist_type"],
            "scheduled_time": checklist["scheduled_time"],
            "deadline": checklist["deadline"],
            "is_active": False,
        },
    ).status_code == 200
    assert client.delete(
        f"/checklists/{checklist_id}", headers=AUTH_HEADERS
    ).status_code == 409
    assert client.delete(
        f"/tasks/{task_ids[0]}", headers=AUTH_HEADERS
    ).status_code == 409
    task_update = client.put(
        f"/tasks/{task_ids[0]}",
        headers=AUTH_HEADERS,
        json={
            "title": "Tarefa 1",
            "description": None,
            "is_required": False,
            "position": 0,
        },
    )
    assert task_update.status_code == 409

    final_update = client.patch(
        f"/executions/{execution_id}/tasks/{task_ids[0]}",
        headers=AUTH_HEADERS,
    )
    assert final_update.status_code == 200
    assert final_update.json()["status"] == "completed"
    assert is_utc_timestamp(final_update.json()["completed_at"])
    assert is_utc_timestamp(final_update.json()["updated_at"])
    assert final_update.json()["completion_percentage"] == 50
    assert final_update.json()["is_complete"] is True
    assert final_update.json()["is_incomplete"] is False
    optional_task = next(
        item
        for item in final_update.json()["task_executions"]
        if item["task_id"] == task_ids[1]
    )
    assert optional_task["is_completed"] is False
    assert client.get(
        f"/executions/{execution_id}", headers=AUTH_HEADERS
    ).json()["status"] == "completed"
    assert client.get("/executions", headers=AUTH_HEADERS).status_code == 200
    with Session(client.app.state.test_engine) as session:
        notification_types = list(
            session.scalars(
                select(NotificationLog.notification_type).order_by(
                    NotificationLog.id
                )
            )
        )
    assert notification_types == [
        NotificationType.CHECKLIST_STARTED.value,
        NotificationType.CHECKLIST_COMPLETED.value,
    ]
    assert client.patch(
        f"/executions/{execution_id}/tasks/{task_ids[1]}",
        headers=AUTH_HEADERS,
    ).status_code == 409
    assert client.patch(
        f"/executions/{execution_id}/tasks/9999", headers=AUTH_HEADERS
    ).status_code == 404


def test_inactive_or_empty_checklists_cannot_start_execution(
    client: TestClient,
) -> None:
    checklist = create_checklist(client)
    inactive = client.put(
        f"/checklists/{checklist['id']}",
        headers=AUTH_HEADERS,
        json={
            "title": checklist["title"],
            "description": checklist["description"],
            "checklist_type": checklist["checklist_type"],
            "scheduled_time": checklist["scheduled_time"],
            "deadline": checklist["deadline"],
            "is_active": False,
        },
    )
    assert inactive.status_code == 200
    assert client.post(
        f"/checklists/{checklist['id']}/executions", headers=AUTH_HEADERS
    ).status_code == 409
    empty_checklist = create_checklist(client, title="Sem tarefas")
    assert client.post(
        f"/checklists/{empty_checklist['id']}/executions",
        headers=AUTH_HEADERS,
    ).status_code == 409


def test_all_optional_tasks_complete_execution_at_start(client: TestClient) -> None:
    checklist = create_checklist(client)
    task = client.post(
        f"/checklists/{checklist['id']}/tasks",
        headers=AUTH_HEADERS,
        json={"title": "Opcional", "is_required": False, "position": 0},
    )
    assert task.status_code == 201

    execution = client.post(
        f"/checklists/{checklist['id']}/executions", headers=AUTH_HEADERS
    )
    assert execution.status_code == 201
    assert execution.json()["status"] == "completed"
    assert execution.json()["completion_percentage"] == 0
    assert execution.json()["is_complete"] is True
    assert execution.json()["task_executions"][0]["is_completed"] is False


def test_execution_uses_operation_timezone_and_becomes_overdue(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "operation_timezone", "America/Sao_Paulo")
    checklist = create_checklist(client)
    checklist_id = checklist["id"]
    updated = client.put(
        f"/checklists/{checklist_id}",
        headers=AUTH_HEADERS,
        json={
            "title": checklist["title"],
            "description": checklist["description"],
            "checklist_type": checklist["checklist_type"],
            "scheduled_time": "22:00:00",
            "deadline": "00:30:00",
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    task = client.post(
        f"/checklists/{checklist_id}/tasks",
        headers=AUTH_HEADERS,
        json={"title": "Obrigatória", "is_required": True, "position": 0},
    )
    assert task.status_code == 201

    before_deadline = datetime(2026, 1, 1, 2, 29, tzinfo=timezone.utc)
    monkeypatch.setattr(
        execution_service, "utc_now", lambda: before_deadline
    )
    started = client.post(
        f"/checklists/{checklist_id}/executions", headers=AUTH_HEADERS
    )
    assert started.status_code == 201
    execution_id = started.json()["id"]
    assert started.json()["execution_date"] == "2025-12-31"

    after_deadline = datetime(2026, 1, 1, 3, 31, tzinfo=timezone.utc)
    monkeypatch.setattr(execution_service, "utc_now", lambda: after_deadline)
    overdue = client.get(
        f"/executions/{execution_id}", headers=AUTH_HEADERS
    )
    assert overdue.status_code == 200
    assert overdue.json()["status"] == "overdue"
    assert overdue.json()["is_overdue"] is True
    assert overdue.json()["is_incomplete"] is True


def test_timezone_aware_schedule_values_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/checklists",
        headers=AUTH_HEADERS,
        json={
            "title": "Horário com offset",
            "checklist_type": "opening",
            "scheduled_time": "08:00:00-03:00",
        },
    )
    assert response.status_code == 422


def test_invalid_operation_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(operation_timezone="Invalid/Timezone")
