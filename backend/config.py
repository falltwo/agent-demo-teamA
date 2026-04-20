from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 專案根目錄（backend/ 的上一層），供載入根目錄 .env
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """API 設定；機密與 LLM／Pinecone 等沿用專案根目錄 .env（GOOGLE_API_KEY、PINECONE_* 等）。"""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_title: str = Field(default="agent-demo API", validation_alias="API_TITLE")
    api_version: str = Field(default="1.0.0", validation_alias="API_VERSION")
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")

    # 逗號分隔，例如：http://localhost:5173,http://127.0.0.1:5173
    api_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="API_CORS_ORIGINS",
    )
    api_cors_origin_regex: str | None = Field(default=None, validation_alias="API_CORS_ORIGIN_REGEX")

    def cors_origin_list(self) -> list[str]:
        raw = (self.api_cors_origins or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    # 上傳灌入（與 Streamlit 同步處理；超大檔可另做背景 job）
    ingest_max_file_mb: float = Field(default=32.0, validation_alias="INGEST_MAX_FILE_MB")
    ingest_max_total_mb: float = Field(default=128.0, validation_alias="INGEST_MAX_TOTAL_MB")
    ingest_max_files: int = Field(default=20, ge=1, validation_alias="INGEST_MAX_FILES")
    # 預設僅記憶體處理；若設為路徑，未來可將超大檔 spill 至此並於完成後刪除。
    # 目前 `ingest_service` 尚未讀取此欄位（保留給背景 job 規格，參見 backend/README.md）。
    ingest_temp_dir: str | None = Field(
        default=None,
        validation_alias="INGEST_TEMP_DIR",
        description="保留欄位，目前未使用；規劃作為未來背景 ingest job 的 spill-to-disk 路徑。",
    )

    # Admin API 保護用 Bearer token；若未設定則不驗證（向後相容）
    admin_api_token: str | None = Field(
        default=None,
        validation_alias="ADMIN_API_TOKEN",
        description="若設定，/api/v1/admin/* 端點須以 Bearer token 認證",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
