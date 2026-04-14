from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceEntry(BaseModel):
    """與 `sources_registry.update_registry_on_ingest` 寫入之一筆一致。"""

    source: str
    chunk_count: int
    chat_id: str | None = None


class IngestUploadResponse(BaseModel):
    """同步灌入完成回應（與 Streamlit 按鈕後等待結果一致）。"""

    mode: Literal["sync"] = "sync"
    chunks_ingested: int = Field(..., description="寫入 Pinecone 的 chunk 數")
    sources_updated: list[SourceEntry] = Field(default_factory=list)
    skipped_files: list[str] = Field(
        default_factory=list,
        description="因副檔名／檔名不合法而略過的原始檔名（若有）",
    )


class SourcesListResponse(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
