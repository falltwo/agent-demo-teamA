from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.api.deps import SettingsDep
from backend.schemas.ingest import IngestUploadResponse, SourcesListResponse
from backend.services.ingest_adapter import run_ingest_upload
from sources_registry import list_sources

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest/upload", response_model=IngestUploadResponse)
async def post_ingest_upload(
    settings: SettingsDep,
    files: Annotated[list[UploadFile], File(..., description="一或多個 .txt / .md / .pdf / .docx")],
    chat_id: Annotated[str | None, Form(description="對話 id；與 Streamlit `active_conv_id` 一致，寫入 metadata")] = None,
) -> IngestUploadResponse:
    """
    多部分表單：`files` 為檔案欄位（可重複），`chat_id` 為一般表單欄位。
    行為對齊 Streamlit「灌入到向量庫」：同步完成後回傳 chunk 數與本次更新的來源列。
    """
    if not files:
        raise HTTPException(status_code=400, detail="至少需要一個檔案")
    cid = (chat_id or "").strip() or None
    return await run_ingest_upload(files, cid, settings)


@router.get("/sources", response_model=SourcesListResponse)
def get_sources(
    chat_id: str | None = None,
) -> SourcesListResponse:
    """對齊 `sources_registry.list_sources`（側欄「是否有上傳」與來源列表）。"""
    cid = (chat_id or "").strip() or None
    return SourcesListResponse(entries=list_sources(chat_id=cid))
