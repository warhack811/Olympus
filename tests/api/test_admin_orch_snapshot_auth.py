from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
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


def test_snapshot_requires_admin(monkeypatch: pytest.MonkeyPatch):
    app = create_app()

    async def deny_admin():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_current_admin_user] = deny_admin

    with TestClient(app) as client:
        resp = client.get("/api/v1/admin/orch/snapshot")

    assert resp.status_code in (401, 403)


def test_snapshot_allows_admin(monkeypatch: pytest.MonkeyPatch):
    app = create_app()

    async def allow_admin():
        return DummyAdmin()

    async def fake_read_counters():
        return {
            "requests.try": 0,
            "requests.returned": 0,
            "requests.rollout_in": 0,
            "rag.used": 0,
        }

    async def fake_read_fallback_reasons():
        return {}

    app.dependency_overrides[get_current_admin_user] = allow_admin
    monkeypatch.setattr(counter_store, "read_counters", fake_read_counters)
    monkeypatch.setattr(counter_store, "read_fallback_reasons", fake_read_fallback_reasons)

    with TestClient(app) as client:
        resp = client.get("/api/v1/admin/orch/snapshot")

    assert resp.status_code == 200
    assert resp.json().get("ok") is True
