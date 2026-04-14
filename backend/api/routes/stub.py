from fastapi import APIRouter

from backend.api.deps import SettingsDep
from backend.schemas.stub import StubInfoResponse

router = APIRouter(prefix="/api/v1", tags=["stub"])


@router.get("/info", response_model=StubInfoResponse)
def stub_info(settings: SettingsDep) -> StubInfoResponse:
    """最小可運行範例：後續可改為真實 chat／ingest 端點。"""
    return StubInfoResponse(message="stub", api_version=settings.api_version)
