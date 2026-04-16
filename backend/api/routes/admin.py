from __future__ import annotations

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

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/services", response_model=ServicesStatusResponse)
def get_services_status(_auth: AdminAuthDep) -> ServicesStatusResponse:
    return ServicesStatusResponse(services=admin_service.list_services_status())


@router.post("/services/restart", response_model=ServicesRestartResponse)
def post_restart_services(body: ServicesRestartRequest, _auth: AdminAuthDep) -> ServicesRestartResponse:
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
