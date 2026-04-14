"""驗證上傳大小／數量後呼叫 `ingest_service.ingest_file_items`。"""
from __future__ import annotations

from fastapi import HTTPException, UploadFile

from backend.config import Settings
from backend.schemas.ingest import IngestUploadResponse, SourceEntry
from backend.rag_clients import get_cached_rag_stack
from ingest_service import ALLOWED_SUFFIXES, ingest_file_items, sanitize_upload_filename


async def _read_file_limited(upload: UploadFile, max_bytes: int) -> tuple[str, bytes]:
    """讀取 UploadFile 並強制單檔上限。"""
    name = upload.filename or "uploaded"
    out = bytearray()
    chunk_size = 1024 * 1024
    while True:
        block = await upload.read(chunk_size)
        if not block:
            break
        out.extend(block)
        if len(out) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"檔案超過單檔上限（{max_bytes // (1024 * 1024)} MB）",
            )
    return name, bytes(out)


def _suffix_ok(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(s) for s in ALLOWED_SUFFIXES)


async def run_ingest_upload(
    files: list[UploadFile],
    chat_id: str | None,
    settings: Settings,
) -> IngestUploadResponse:
    if len(files) > settings.ingest_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"檔案數量超過上限（最多 {settings.ingest_max_files} 個）",
        )

    max_file = int(settings.ingest_max_file_mb * 1024 * 1024)
    max_total = int(settings.ingest_max_total_mb * 1024 * 1024)

    items: list[tuple[str, bytes]] = []
    skipped: list[str] = []
    total = 0

    for upload in files:
        raw_name, raw = await _read_file_limited(upload, max_file)
        total += len(raw)
        if total > max_total:
            raise HTTPException(
                status_code=400,
                detail=f"合計大小超過上限（{settings.ingest_max_total_mb} MB）",
            )
        if not _suffix_ok(raw_name):
            skipped.append(raw_name)
            continue
        try:
            sanitize_upload_filename(raw_name)
        except ValueError:
            skipped.append(raw_name)
            continue
        items.append((raw_name, raw))

    if not items:
        return IngestUploadResponse(chunks_ingested=0, sources_updated=[], skipped_files=skipped)

    _chat, embed_client, index, index_dim, _llm, embed_model, _index_name = get_cached_rag_stack()

    n, new_entries = ingest_file_items(
        items,
        embed_client=embed_client,
        index=index,
        index_dim=index_dim,
        embed_model=embed_model,
        chat_id=chat_id,
    )

    return IngestUploadResponse(
        chunks_ingested=n,
        sources_updated=[SourceEntry.model_validate(e) for e in new_entries],
        skipped_files=skipped,
    )
