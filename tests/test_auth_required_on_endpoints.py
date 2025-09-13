import pytest
from fastapi.testclient import TestClient

from mcg_agent.app import app
from mcg_agent.security.jwt_auth import create_access_token


def test_query_requires_auth():
    client = TestClient(app)
    r = client.post("/query", json={"prompt": "hello"})
    assert r.status_code == 401


def test_pipeline_summary_requires_auth():
    client = TestClient(app)
    r = client.get("/pipeline/summary")
    assert r.status_code == 401


def test_query_with_valid_token(monkeypatch):
    # Ensure GEN_PROVIDER doesn't require network
    monkeypatch.setenv("GEN_PROVIDER", "punctuation_only")
    client = TestClient(app)
    token = create_access_token("test-user")
    r = client.post("/query", headers={"Authorization": f"Bearer {token}"}, json={"prompt": "Hello world!"})
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    assert data["metadata"].get("user_id") == "test-user"

