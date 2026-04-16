from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceEntry(BaseModel):
    source: str
    chunk_count: int
    chat_id: str | None = None


class IngestUploadResponse(BaseModel):
    mode: Literal["sync"] = "sync"
    chunks_ingested: int = Field(..., description="Number of chunks ingested into Pinecone")
    sources_updated: list[SourceEntry] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)


class SourcesListResponse(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


class SourcePreviewResponse(BaseModel):
    source: str
    chat_id: str | None = None
    title: str
    content: str
    chunk_count: int = 0
