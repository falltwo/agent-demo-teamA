"""Unit tests for admin endpoint authentication."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.schemas.admin import OllamaModelsResponse, ServicesStatusResponse


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
    # 不帶 token → 應回 401（認證在進入 service 前就擋掉，不需 mock）
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
    # mock ollama service call，避免 CI 環境沒有 ollama 指令
    with patch(
        "backend.services.admin_service.list_ollama_models",
        return_value=OllamaModelsResponse(models=[]),
    ):
        r = client.get(
            "/api/v1/admin/ollama/models",
            headers={"Authorization": "Bearer secret-token"},
        )
    # 認證通過（不應是 401）
    assert r.status_code != 401


def test_admin_no_token_configured_allows_open_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """未設定 ADMIN_API_TOKEN 時，維持向後相容，不強制認證。"""
    client = _make_client(monkeypatch, None)
    # mock service call，避免 CI 執行 systemctl
    with patch(
        "backend.services.admin_service.list_services_status",
        return_value=[],
    ):
        r = client.get("/api/v1/admin/services")
    assert r.status_code != 401


def test_admin_restart_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, "secret-token")
    # 不帶 token → 應回 401（認證在 service 執行前攔截）
    r = client.post("/api/v1/admin/services/restart", json={"services": []})
    assert r.status_code == 401
