"""Unit tests for admin restart rate-limit (B4-10)."""
from __future__ import annotations

from collections import deque
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.schemas.admin import ServiceStatus


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # 確保未啟用 admin token（用開放模式測 rate limit 本身）
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    from backend.config import get_settings
    get_settings.cache_clear()
    from backend.main import create_app
    return TestClient(create_app())


def _reset_rate_limit_state() -> None:
    """清空 module-level rate-limit deque，避免測試間互相污染。"""
    from backend.api.routes import admin as admin_mod
    admin_mod._restart_calls = deque()


def test_restart_allows_under_limit(client: TestClient) -> None:
    _reset_rate_limit_state()
    with patch(
        "backend.services.admin_service.restart_services",
        return_value=([], [], []),
    ):
        for _ in range(3):  # _RESTART_MAX_CALLS == 3
            r = client.post(
                "/api/v1/admin/services/restart",
                json={"services": ["contract-agent-api.service"]},
            )
            assert r.status_code == 200


def test_restart_rate_limits_after_threshold(client: TestClient) -> None:
    _reset_rate_limit_state()
    with patch(
        "backend.services.admin_service.restart_services",
        return_value=(
            ["contract-agent-api.service"],
            [],
            [
                ServiceStatus(
                    name="contract-agent-api.service",
                    active_state="active",
                    sub_state="running",
                )
            ],
        ),
    ):
        # 前 3 次成功
        for _ in range(3):
            r = client.post(
                "/api/v1/admin/services/restart",
                json={"services": ["contract-agent-api.service"]},
            )
            assert r.status_code == 200
        # 第 4 次超限 → 429
        r = client.post(
            "/api/v1/admin/services/restart",
            json={"services": ["contract-agent-api.service"]},
        )
        assert r.status_code == 429
        # 必帶 Retry-After header
        assert "retry-after" in {k.lower() for k in r.headers.keys()}


def test_restart_rate_limit_window_resets(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """模擬時間超過 window 後，舊請求被 popleft，計數歸零。"""
    _reset_rate_limit_state()
    from backend.api.routes import admin as admin_mod

    times: list[float] = [0.0]

    def fake_monotonic() -> float:
        return times[0]

    monkeypatch.setattr(admin_mod.time, "monotonic", fake_monotonic)

    with patch(
        "backend.services.admin_service.restart_services",
        return_value=([], [], []),
    ):
        # 在 t=0 送 3 次滿額
        for _ in range(3):
            r = client.post(
                "/api/v1/admin/services/restart",
                json={"services": ["contract-agent-api.service"]},
            )
            assert r.status_code == 200

        # 下一次在 window 內 → 429
        times[0] = 10.0
        r = client.post(
            "/api/v1/admin/services/restart",
            json={"services": ["contract-agent-api.service"]},
        )
        assert r.status_code == 429

        # 跳到 window 外 → 應放行
        times[0] = 10.0 + admin_mod._RESTART_WINDOW_SEC + 1
        r = client.post(
            "/api/v1/admin/services/restart",
            json={"services": ["contract-agent-api.service"]},
        )
        assert r.status_code == 200
