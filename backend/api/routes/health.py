from fastapi import APIRouter

from backend.api.deps import SettingsDep
from backend.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", service="agent-demo-api", version=settings.api_version)
