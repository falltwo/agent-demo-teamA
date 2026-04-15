"""將 HTTP 契約對應到 `chat_service.answer_with_rag_and_log`，不複製 Agent 邏輯。"""
from __future__ import annotations

import time
from typing import Any

from chat_service import answer_with_rag_and_log

from backend.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChunkItem


def _history_to_payload(history: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in history]


def _chunks_to_models(chunks: list[dict[str, Any]]) -> list[ChunkItem]:
    out: list[ChunkItem] = []
    for c in chunks:
        if not isinstance(c, dict):
            continue
        out.append(ChunkItem.model_validate(c))
    return out


def _client_hints(message: str, tool_name: str, extra: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """對齊 Streamlit `pending_web_vs_rag_question` / `pending_chart_question` 的下一輪參數。"""
    next_orig: str | None = None
    next_chart_q: str | None = None
    if tool_name == "ask_web_vs_rag":
        next_orig = message
    if tool_name == "analyze_and_chart" and extra and extra.get("asked_chart_confirmation"):
        next_chart_q = (extra.get("chart_query") or message) or None
    return next_orig, next_chart_q


def run_chat_turn(body: ChatRequest) -> ChatResponse:
    history_payload = _history_to_payload(body.history)
    t0 = time.perf_counter()
    answer, sources, chunks_raw, tool_name, extra = answer_with_rag_and_log(
        question=body.message.strip(),
        top_k=body.top_k,
        history=history_payload,
        strict=body.strict,
        chat_id=body.chat_id,
        rag_scope_chat_id=body.rag_scope_chat_id,
        original_question=body.original_question,
        clarification_reply=body.clarification_reply,
        chart_confirmation_question=body.chart_confirmation_question,
        chart_confirmation_reply=body.chart_confirmation_reply,
    )
    latency_sec = time.perf_counter() - t0
    next_orig, next_chart = _client_hints(body.message.strip(), tool_name, extra)
    return ChatResponse(
        answer=answer or "",
        sources=list(sources or []),
        chunks=_chunks_to_models(list(chunks_raw or [])),
        tool_name=tool_name,
        extra=extra,
        latency_sec=round(latency_sec, 4),
        next_original_question_for_clarification=next_orig,
        next_chart_confirmation_question=next_chart,
    )
