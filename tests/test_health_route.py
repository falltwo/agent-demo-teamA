"""Unit tests for /health endpoint with dependency probing."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHAT_PROVIDER", "ollama")
    monkeypatch.setenv("PINECONE_API_KEY", "fake-key-for-test")
    # 清除 lru_cache，讓 Settings 重新載入 monkeypatch 後的環境變數
    from backend.config import get_settings
    get_settings.cache_clear()
    from backend.main import create_app
    return TestClient(create_app())


def test_health_ok_when_all_deps_up(client: TestClient) -> None:
    with patch("backend.api.routes.health._check_ollama", return_value=True), \
         patch("backend.api.routes.health._check_pinecone", return_value=True):
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["deps"]["ollama"] == "ok"
    assert body["deps"]["pinecone"] == "ok"


def test_health_degraded_when_ollama_down(client: TestClient) -> None:
    with patch("backend.api.routes.health._check_ollama", return_value=False), \
         patch("backend.api.routes.health._check_pinecone", return_value=True):
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["deps"]["ollama"] == "unreachable"
    assert body["deps"]["pinecone"] == "ok"


def test_health_degraded_when_pinecone_down(client: TestClient) -> None:
    with patch("backend.api.routes.health._check_ollama", return_value=True), \
         patch("backend.api.routes.health._check_pinecone", return_value=False):
        r = client.get("/health")
    body = r.json()
    assert body["status"] == "degraded"
    assert body["deps"]["pinecone"] == "unreachable"


def test_health_has_version_field(client: TestClient) -> None:
    with patch("backend.api.routes.health._check_ollama", return_value=True), \
         patch("backend.api.routes.health._check_pinecone", return_value=True):
        r = client.get("/health")
    assert "version" in r.json()
    assert "service" in r.json()
