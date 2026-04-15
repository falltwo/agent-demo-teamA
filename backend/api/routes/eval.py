"""Eval 唯讀 API：線上運行記錄、批次結果列表與詳情。"""
from __future__ import annotations

import eval_log
from fastapi import APIRouter, HTTPException

from backend.schemas.eval import (
    EvalBatchDetailResponse,
    EvalBatchListResponse,
    EvalConfigResponse,
    EvalRunsResponse,
)
from backend.services import eval_service

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])


@router.get("/config", response_model=EvalConfigResponse)
def get_eval_config() -> EvalConfigResponse:
    """是否啟用 EVAL 寫入（與 eval_log.is_enabled() 一致）。"""
    return EvalConfigResponse(eval_log_enabled=eval_log.is_enabled())


@router.get("/runs", response_model=EvalRunsResponse)
def get_eval_runs(limit: int = 500) -> EvalRunsResponse:
    """線上運行記錄（eval_runs.jsonl），新到舊最多 limit 筆。"""
    lim = max(1, min(limit, 500))
    entries, enabled = eval_service.load_online_runs(limit=lim)
    return EvalRunsResponse(entries=entries, eval_log_enabled=enabled, limit=lim)


@router.get("/batch/runs", response_model=EvalBatchListResponse)
def list_eval_batch_runs() -> EvalBatchListResponse:
    """列出 eval/runs 下各批次 run id。"""
    run_ids, runs_dir = eval_service.list_batch_run_ids()
    return EvalBatchListResponse(run_ids=run_ids, runs_dir=str(runs_dir))


@router.get("/batch/{run_id}", response_model=EvalBatchDetailResponse)
def get_eval_batch_detail(run_id: str) -> EvalBatchDetailResponse:
    """單一批次：metrics + 逐題 results。"""
    detail = eval_service.load_batch_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="找不到此批次或 run_id 不合法")
    return detail
