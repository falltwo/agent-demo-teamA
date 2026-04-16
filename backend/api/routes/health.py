from __future__ import annotations

import os

import httpx
from fastapi import APIRouter

from backend.api.deps import SettingsDep
from backend.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


def _check_ollama() -> bool:
    """探測 Ollama /api/tags，確認服務可達。"""
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    # 移除 /v1 後綴，Ollama 原生 API 在根路徑
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    try:
        r = httpx.get(f"{base}/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


def _check_pinecone() -> bool:
    """嘗試列出 Pinecone indexes，確認 API key 有效且服務可達。"""
    try:
        from pinecone import Pinecone

        api_key = os.getenv("PINECONE_API_KEY", "")
        if not api_key:
            return False
        pc = Pinecone(api_key=api_key)
        pc.list_indexes()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    provider = os.getenv("CHAT_PROVIDER", "").strip().lower()
    deps: dict[str, str] = {}

    # 只在使用 Ollama 時才探測（Gemini/Groq 不在本機）
    if provider in ("ollama", "local", ""):
        deps["ollama"] = "ok" if _check_ollama() else "unreachable"

    if os.getenv("PINECONE_API_KEY", ""):
        deps["pinecone"] = "ok" if _check_pinecone() else "unreachable"

    overall = "ok" if all(v == "ok" for v in deps.values()) else "degraded"
    return HealthResponse(
        status=overall,
        service="agent-demo-api",
        version=settings.api_version,
        deps=deps,
    )
