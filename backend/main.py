"""
FastAPI 應用程式入口。

啟動（專案根目錄）：
  uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

與 Streamlit 雙軌並存時，另開終端機：
  uv run streamlit run streamlit_app.py
"""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# 集中化 .env 載入：backend 進程內任何模組可直接 os.getenv 取值，不必各自 load_dotenv。
# load_dotenv 預設 override=False，不覆蓋既有環境（容器/systemd 注入的 env 仍優先）。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from backend.api.routes.chat import router as chat_router
from backend.api.routes.chat_stream import router as chat_stream_router
from backend.api.routes.admin import router as admin_router
from backend.api.routes.eval import router as eval_router
from backend.api.routes.health import router as health_router
from backend.api.routes.ingest import router as ingest_router
from backend.api.routes.stub import router as stub_router
from backend.config import get_settings
from backend.logging_config import configure_logging, configure_threadpool
from backend.exception_handlers import (
    http_exception_handler,
    pydantic_validation_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.api_title, version=settings.api_version)

    # CORS：目前以 Bearer token 認證，不依賴瀏覽器 cookie，關閉 allow_credentials 以便
    # 保留 allow_methods=[*] 與 allow_headers=[*] 的便利（CORS spec 禁止 credentials + *）。
    # 若日後改用 cookie/session，需同時把 origins/methods/headers 列白名單並打開 credentials。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_origin_regex=settings.api_cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(chat_stream_router)
    app.include_router(admin_router)
    app.include_router(ingest_router)
    app.include_router(eval_router)
    app.include_router(stub_router)

    @app.on_event("startup")
    async def _raise_threadpool_limit() -> None:
        # Chat 端點為同步 def；長時間 LLM 呼叫會佔滿 anyio 預設 40-thread pool。
        configure_threadpool()

    return app


app = create_app()
