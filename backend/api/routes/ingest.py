from pathlib import Path, PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from backend.api.deps import SettingsDep
from backend.schemas.ingest import (
    IngestUploadResponse,
    SourcePreviewResponse,
    SourcesListResponse,
)
from backend.services.ingest_adapter import run_ingest_upload
from rag_common import load_bm25_corpus
from sources_registry import list_sources

router = APIRouter(prefix="/api/v1", tags=["ingest"])


def _source_variants(value: str) -> set[str]:
    normalized = value.strip().replace("\\", "/")
    variants = {normalized}
    try:
        repaired = normalized.encode("latin-1").decode("utf-8")
    except UnicodeError:
        repaired = None
    if repaired:
        variants.add(repaired)
    expanded: set[str] = set()
    for item in variants:
        expanded.add(item)
        expanded.add(PurePosixPath(item).name)
    return {item for item in expanded if item}


@router.post("/ingest/upload", response_model=IngestUploadResponse)
async def post_ingest_upload(
    settings: SettingsDep,
    files: Annotated[list[UploadFile], File(..., description="One or more .txt / .md / .pdf / .docx files")],
    chat_id: Annotated[str | None, Form(description="Conversation id for metadata scoping")] = None,
) -> IngestUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    cid = (chat_id or "").strip() or None
    return await run_ingest_upload(files, cid, settings)


@router.get("/sources", response_model=SourcesListResponse)
def get_sources(
    chat_id: str | None = None,
) -> SourcesListResponse:
    cid = (chat_id or "").strip() or None
    return SourcesListResponse(entries=list_sources(chat_id=cid))


@router.get("/sources/preview", response_model=SourcePreviewResponse)
def get_source_preview(
    source: Annotated[str, Query(description="Exact source id, such as uploaded/<chat_id>/<filename>")],
    chat_id: Annotated[str | None, Query(description="Optional conversation scope")] = None,
) -> SourcePreviewResponse:
    normalized_source = source.strip()
    if not normalized_source:
        raise HTTPException(status_code=400, detail="source is required")

    normalized_chat_id = (chat_id or "").strip() or None
    source_keys = _source_variants(normalized_source)
    corpus = load_bm25_corpus()
    matched = [
        row for row in corpus
        if _source_variants(str(row.get("source", ""))).intersection(source_keys)
        and (normalized_chat_id is None or row.get("chat_id") == normalized_chat_id)
    ]
    if not matched:
        raise HTTPException(status_code=404, detail="Preview source not found")

    matched.sort(key=lambda row: int(row.get("chunk_index", 0)))
    canonical_source = str(matched[0].get("source", normalized_source)).strip().replace("\\", "/")
    title = Path(canonical_source).name.replace("\\", "/")
    if "#chunk" in title:
        title = title.split("#chunk", 1)[0]
    content = "\n\n".join(str(row.get("text", "")).strip() for row in matched if str(row.get("text", "")).strip())
    if not content:
        raise HTTPException(status_code=404, detail="Preview content is empty")

    return SourcePreviewResponse(
        source=canonical_source,
        chat_id=normalized_chat_id,
        title=title,
        content=content,
        chunk_count=len(matched),
    )
