"""讀取 eval 日誌與批次結果檔（唯讀）；路徑與 streamlit_app／eval_log 一致。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import eval_log
from backend.schemas.eval import EvalBatchDetailResponse, EvalRunEntry

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _eval_runs_dir() -> Path:
    # .env 已由 backend.main.create_app 或上游模組 load 過；此處不再每次 reload。
    raw = os.getenv("EVAL_RUNS_DIR", "eval/runs")
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (_PROJECT_ROOT / p).resolve()


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def load_online_runs(limit: int = 500) -> tuple[list[EvalRunEntry], bool, int]:
    """等同 eval_log.load_runs(limit)，並回傳 (entries, eval_enabled, dropped_rows)。

    dropped_rows 統計：JSONL 解析失敗 + 非 dict + Pydantic 驗證失敗 的總和。
    """
    raw, parse_dropped = eval_log.load_runs_with_stats(limit=limit)
    enabled = eval_log.is_enabled()
    entries: list[EvalRunEntry] = []
    dropped = int(parse_dropped)
    for row in raw:
        if not isinstance(row, dict):
            dropped += 1
            continue
        try:
            entries.append(
                EvalRunEntry(
                    timestamp=row.get("timestamp") if isinstance(row.get("timestamp"), str) else None,
                    question=str(row.get("question") or ""),
                    answer=str(row.get("answer") or ""),
                    tool_name=str(row.get("tool_name") or ""),
                    latency_sec=float(row.get("latency_sec") or 0.0),
                    top_k=int(row.get("top_k") or 0),
                    source_count=int(row.get("source_count") or 0),
                    chat_id=row.get("chat_id") if isinstance(row.get("chat_id"), str) else None,
                )
            )
        except Exception:
            dropped += 1
            continue
    return entries, enabled, dropped


def list_batch_run_ids() -> tuple[list[str], Path]:
    """列出 eval/runs 下 run_*_results.jsonl 之 run id（與 Streamlit stem 規則一致）。"""
    runs_dir = _eval_runs_dir()
    if not runs_dir.is_dir():
        return [], runs_dir

    files = sorted(
        runs_dir.glob("run_*_results.jsonl"),
        key=lambda p: p.name,
        reverse=True,
    )
    run_ids: list[str] = []
    for f in files:
        stem = f.stem.replace("_results", "")
        if stem:
            run_ids.append(stem)
    return run_ids, runs_dir


def _safe_results_path(runs_dir: Path, run_id: str) -> Path | None:
    if not run_id or not _RUN_ID_RE.match(run_id):
        return None
    candidate = (runs_dir / f"{run_id}_results.jsonl").resolve()
    base = runs_dir.resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def load_batch_detail(run_id: str) -> EvalBatchDetailResponse | None:
    """讀取單一批次 run；run_id 非法或檔案不存在回傳 None。"""
    runs_dir = _eval_runs_dir()
    results_path = _safe_results_path(runs_dir, run_id)
    if results_path is None or not results_path.is_file():
        return None

    results: list[dict[str, Any]] = []
    dropped = 0
    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                dropped += 1
                continue
            if isinstance(obj, dict):
                results.append(obj)
            else:
                dropped += 1

    metrics: dict[str, Any] | None = None
    metrics_path = runs_dir / f"{run_id}_metrics.json"
    if metrics_path.is_file():
        try:
            raw = json.loads(metrics_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                metrics = raw
        except Exception:
            metrics = None

    return EvalBatchDetailResponse(
        run_id=run_id,
        metrics=metrics,
        results=results,
        dropped_rows=dropped,
    )
