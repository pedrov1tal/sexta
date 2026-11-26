from datetime import time

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import Base
from app.database.session import create_database_engine, get_db
from app.main import app

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
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
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
    return response.json()


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
    assert len(execution["task_executions"]) == 2
    assert client.delete(
        f"/checklists/{checklist_id}", headers=AUTH_HEADERS
    ).status_code == 409
    assert client.delete(
        f"/tasks/{task_ids[0]}", headers=AUTH_HEADERS
    ).status_code == 409

    first_update = client.patch(
        f"/executions/{execution_id}/tasks/{task_ids[0]}",
        headers=AUTH_HEADERS,
    )
    assert first_update.status_code == 200
    assert first_update.json()["status"] == "in_progress"
    second_update = client.patch(
        f"/executions/{execution_id}/tasks/{task_ids[1]}",
        headers=AUTH_HEADERS,
    )
    assert second_update.status_code == 200
    assert second_update.json()["status"] == "completed"
    assert second_update.json()["completed_at"] is not None
    assert client.get(
        f"/executions/{execution_id}", headers=AUTH_HEADERS
    ).json()["status"] == "completed"
    assert client.get("/executions", headers=AUTH_HEADERS).status_code == 200
    assert client.patch(
        f"/executions/{execution_id}/tasks/{task_ids[0]}",
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
