"""Unit tests for admin endpoint authentication."""

import pytest
from fastapi.testclient import TestClient


def _make_client(monkeypatch: pytest.MonkeyPatch, token: str | None) -> TestClient:
    if token is not None:
        monkeypatch.setenv("ADMIN_API_TOKEN", token)
    else:
        monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    from backend.config import get_settings
    get_settings.cache_clear()
    from backend.main import create_app
    return TestClient(create_app())


def test_admin_returns_401_without_token_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, "secret-token")
    r = client.get("/api/v1/admin/services")
    assert r.status_code == 401


def test_admin_returns_401_with_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, "secret-token")
    r = client.get(
        "/api/v1/admin/services",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_admin_allows_valid_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, "secret-token")
    r = client.get(
        "/api/v1/admin/ollama/models",
        headers={"Authorization": "Bearer secret-token"},
    )
    # 認證通過（即使 ollama 未啟動，回傳碼也不應是 401）
    assert r.status_code != 401


def test_admin_no_token_configured_allows_open_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """未設定 ADMIN_API_TOKEN 時，維持向後相容，不強制認證。"""
    client = _make_client(monkeypatch, None)
    r = client.get("/api/v1/admin/services")
    assert r.status_code != 401


def test_admin_restart_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, "secret-token")
    r = client.post("/api/v1/admin/services/restart", json={"services": []})
    assert r.status_code == 401
