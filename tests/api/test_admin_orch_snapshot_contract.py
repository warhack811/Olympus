from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_routes
from app.auth.dependencies import get_current_admin_user
from app.core.telemetry import counter_store


class DummyAdmin:
    def __init__(self) -> None:
        self.username = "admin"
        self.role = "admin"
        self.is_banned = False


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(admin_routes.router, prefix="/api/v1/admin")
    return app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = create_app()

    async def override_admin():
        return DummyAdmin()

    async def fake_read_counters():
        return {
            "requests.try": 3,
            "requests.returned": 2,
            "requests.rollout_in": 1,
            "rag.used": 1,
        }

    async def fake_read_fallback_reasons():
        return {"timeout": 2}

    app.dependency_overrides[get_current_admin_user] = override_admin
    monkeypatch.setattr(counter_store, "read_counters", fake_read_counters)
    monkeypatch.setattr(counter_store, "read_fallback_reasons", fake_read_fallback_reasons)

    with TestClient(app) as test_client:
        yield test_client


def test_snapshot_contract_shape(client: TestClient):
    response = client.get("/api/v1/admin/orch/snapshot")
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    assert isinstance(data["debug_mode"], bool)
    assert data["verbose_requested"] is False
    assert isinstance(data["telemetry"], dict)

    snapshot = data["snapshot"]
    flags = snapshot["flags"]
    rollout = snapshot["rollout"]
    telemetry_summary = snapshot["telemetry_summary"]
    requests = telemetry_summary["requests"]
    rag = telemetry_summary["rag"]
    fallback_reasons = telemetry_summary["fallback_reasons"]
    last_trace_summary = snapshot["last_trace_summary"]
    auto_circuit = snapshot["auto_circuit"]

    assert flags["production_enabled"] in (True, False)
    assert flags["streaming_enabled"] in (True, False)
    assert isinstance(flags["rollout_percent"], int)
    assert isinstance(flags["allowlist_count"], int)

    assert isinstance(rollout["rollout_percent"], int)
    assert isinstance(rollout["allowlist_count"], int)

    assert requests["try"] == 3
    assert requests["returned"] == 2
    assert requests["rollout_in"] == 1
    assert rag["used"] == 1
    assert fallback_reasons == {"timeout": 2}

    assert "trace_id" in last_trace_summary
    assert isinstance(last_trace_summary["event_count"], int)
    assert "timestamp" in last_trace_summary

    assert isinstance(auto_circuit["status"], str)


def test_snapshot_fail_open_returns_defaults(monkeypatch: pytest.MonkeyPatch):
    app = create_app()

    async def override_admin():
        return DummyAdmin()

    async def failing_get_redis():
        raise RuntimeError("redis down")

    app.dependency_overrides[get_current_admin_user] = override_admin
    monkeypatch.setattr(counter_store, "get_redis", failing_get_redis)

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/admin/orch/snapshot")

    assert response.status_code == 200
    snapshot = response.json()["snapshot"]
    telemetry_summary = snapshot["telemetry_summary"]

    assert telemetry_summary["requests"]["try"] == 0
    assert telemetry_summary["requests"]["returned"] == 0
    assert telemetry_summary["requests"]["rollout_in"] == 0
    assert telemetry_summary["rag"]["used"] == 0
    assert telemetry_summary["fallback_reasons"] == {}
