from __future__ import annotations

import logging
import threading
import time
from collections import deque

from fastapi import APIRouter, HTTPException

from backend.api.deps import AdminAuthDep
from backend.schemas.admin import (
    DockerContainersResponse,
    OllamaModelsResponse,
    ServicesRestartRequest,
    ServicesRestartResponse,
    ServicesStatusResponse,
)
from backend.services import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# 簡易記憶體 rate limiter：單 process 內限制 restart endpoint。
# 超過閾值時回 429，避免 token 洩漏後被連打觸發 systemd StartLimit 將服務鎖死。
_RESTART_WINDOW_SEC = 60.0
_RESTART_MAX_CALLS = 3
_restart_calls: deque[float] = deque()
_restart_lock = threading.Lock()


def _restart_rate_limit() -> None:
    now = time.monotonic()
    with _restart_lock:
        while _restart_calls and now - _restart_calls[0] > _RESTART_WINDOW_SEC:
            _restart_calls.popleft()
        if len(_restart_calls) >= _RESTART_MAX_CALLS:
            retry_after = int(_RESTART_WINDOW_SEC - (now - _restart_calls[0])) + 1
            logger.warning(
                "admin restart rate-limited: %d calls within %.0fs window",
                len(_restart_calls), _RESTART_WINDOW_SEC,
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many restart requests; retry after {retry_after}s",
                headers={"Retry-After": str(retry_after)},
            )
        _restart_calls.append(now)


@router.get("/services", response_model=ServicesStatusResponse)
def get_services_status(_auth: AdminAuthDep) -> ServicesStatusResponse:
    return ServicesStatusResponse(services=admin_service.list_services_status())


@router.post("/services/restart", response_model=ServicesRestartResponse)
def post_restart_services(body: ServicesRestartRequest, _auth: AdminAuthDep) -> ServicesRestartResponse:
    _restart_rate_limit()
    requested = body.services or list(admin_service.DEFAULT_RESTART_SERVICES)
    requested = [x.strip() for x in requested if x and x.strip()]
    if not requested:
        raise HTTPException(status_code=400, detail="services cannot be empty")

    not_allowed = [x for x in requested if x not in admin_service.RESTARTABLE_SERVICES]
    if not_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"service not allowed: {', '.join(not_allowed)}",
        )

    restarted, failed, statuses = admin_service.restart_services(requested)
    return ServicesRestartResponse(
        requested_services=requested,
        restarted_services=restarted,
        failed_services=failed,
        services=statuses,
    )


@router.get("/ollama/models", response_model=OllamaModelsResponse)
def get_ollama_models(_auth: AdminAuthDep) -> OllamaModelsResponse:
    return admin_service.list_ollama_models()


@router.get("/docker/containers", response_model=DockerContainersResponse)
def get_docker_containers(_auth: AdminAuthDep) -> DockerContainersResponse:
    return admin_service.list_docker_containers()
