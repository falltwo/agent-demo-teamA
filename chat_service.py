"""與 Streamlit／FastAPI 共用的 Agent 問答入口：薄封裝 `agent_router.route_and_answer`，並可選寫入 Eval 日誌。"""
from __future__ import annotations

import time
from typing import Any

from agent_router import route_and_answer
from eval_log import is_enabled as eval_log_enabled
from eval_log import log_run as eval_log_run


def answer_with_rag(
    *,
    question: str,
    top_k: int,
    history: list[dict[str, Any]] | None = None,
    strict: bool = True,
    chat_id: str | None = None,
    rag_scope_chat_id: str | None = None,
    original_question: str | None = None,
    clarification_reply: str | None = None,
    chart_confirmation_question: str | None = None,
    chart_confirmation_reply: str | None = None,
) -> tuple[str, list[str], list[dict[str, Any]], str, dict[str, Any] | None]:
    """走總管 Agent，回傳 (answer, sources, chunks, tool_name, extra)。"""
    answer, sources, chunks, tool_name, extra = route_and_answer(
        question=question,
        top_k=top_k,
        history=history or [],
        strict=strict,
        chat_id=chat_id,
        rag_scope_chat_id=rag_scope_chat_id,
        original_question=original_question,
        clarification_reply=clarification_reply,
        chart_confirmation_question=chart_confirmation_question,
        chart_confirmation_reply=chart_confirmation_reply,
    )
    return answer, sources, chunks, tool_name, extra


def answer_with_rag_and_log(
    *,
    question: str,
    top_k: int,
    history: list[dict[str, Any]] | None = None,
    strict: bool = True,
    chat_id: str | None = None,
    rag_scope_chat_id: str | None = None,
    original_question: str | None = None,
    clarification_reply: str | None = None,
    chart_confirmation_question: str | None = None,
    chart_confirmation_reply: str | None = None,
) -> tuple[str, list[str], list[dict[str, Any]], str, dict[str, Any] | None]:
    """呼叫 answer_with_rag 並計時；若啟用 Eval 記錄則寫入一筆 log（與原 streamlit_app 行為一致）。"""
    t0 = time.perf_counter()
    answer, sources, chunks, tool_name, extra = answer_with_rag(
        question=question,
        top_k=top_k,
        history=history or [],
        strict=strict,
        chat_id=chat_id,
        rag_scope_chat_id=rag_scope_chat_id,
        original_question=original_question,
        clarification_reply=clarification_reply,
        chart_confirmation_question=chart_confirmation_question,
        chart_confirmation_reply=chart_confirmation_reply,
    )
    latency = time.perf_counter() - t0
    if eval_log_enabled():
        eval_log_run(
            question=question,
            answer=answer or "",
            tool_name=tool_name,
            latency_sec=latency,
            top_k=top_k,
            source_count=len(sources),
            chat_id=chat_id,
        )
    return answer, sources, chunks, tool_name, extra
