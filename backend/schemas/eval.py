"""Eval API 契約（對齊 streamlit_app Eval 兩頁與 eval_log／eval/runs 檔案結構）。"""

from typing import Any

from pydantic import BaseModel, Field


class EvalRunEntry(BaseModel):
    """單筆線上運行記錄（eval_runs.jsonl 一行）。"""

    timestamp: str | None = None
    question: str = ""
    answer: str = ""
    tool_name: str = ""
    latency_sec: float = 0.0
    top_k: int = 0
    source_count: int = 0
    chat_id: str | None = None


class EvalRunsResponse(BaseModel):
    """GET /api/v1/eval/runs — 與 eval_log.load_runs(limit) 一致（新到舊）。"""

    entries: list[EvalRunEntry] = Field(default_factory=list)
    eval_log_enabled: bool = Field(
        ...,
        description="是否啟用寫入 EVAL_LOG（與 eval_log.is_enabled() 一致）；不影響讀取既有檔案。",
    )
    limit: int = Field(default=500, description="本次載入筆數上限")
    dropped_rows: int = Field(
        default=0,
        description="讀取時因 JSON 解析失敗或結構不合法而被丟棄的列數（僅供前端/運維觀察）。",
    )


class EvalConfigResponse(BaseModel):
    """GET /api/v1/eval/config"""

    eval_log_enabled: bool


class EvalBatchListResponse(BaseModel):
    """GET /api/v1/eval/batch/runs"""

    run_ids: list[str] = Field(default_factory=list)
    runs_dir: str = Field(..., description="解析後之批次結果目錄（供除錯／說明）")


class EvalBatchDetailResponse(BaseModel):
    """GET /api/v1/eval/batch/{run_id}"""

    run_id: str
    metrics: dict[str, Any] | None = None
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="run_*_results.jsonl 每行一筆原始 JSON",
    )
    dropped_rows: int = Field(
        default=0,
        description="讀取時因 JSON 解析失敗或非 dict 被丟棄的列數（僅供觀察）。",
    )
