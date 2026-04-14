"""Chat API 契約測試：mock `route_and_answer`，不呼叫真實 LLM／向量庫。"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@patch("chat_service.eval_log_enabled", return_value=False)
@patch("chat_service.route_and_answer")
def test_post_chat_returns_contract_fields(
    mock_route: object,
    _eval_off: object,
    client: TestClient,
) -> None:
    mock_route.return_value = (
        "主文\n\n**參考連結：**\n- http://example.com",
        ["src/a.pdf"],
        [{"tag": "[x#chunk0]", "text": "snippet"}],
        "rag_search",
        {"chart_option": {"series": []}, "asked_chart_confirmation": False},
    )
    res = client.post(
        "/api/v1/chat",
        json={
            "message": "你好",
            "top_k": 5,
            "history": [],
            "strict": False,
            "chat_id": "chat-1",
            "rag_scope_chat_id": None,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["answer"].startswith("主文")
    assert data["sources"] == ["src/a.pdf"]
    assert data["chunks"][0]["tag"] == "[x#chunk0]"
    assert data["chunks"][0]["text"] == "snippet"
    assert data["tool_name"] == "rag_search"
    assert data["extra"]["chart_option"] == {"series": []}
    assert "latency_sec" in data
    assert data["next_original_question_for_clarification"] is None
    assert data["next_chart_confirmation_question"] is None

    mock_route.assert_called_once()
    call_kw = mock_route.call_args.kwargs
    assert call_kw["question"] == "你好"
    assert call_kw["strict"] is False
    assert call_kw["chat_id"] == "chat-1"
    assert call_kw["rag_scope_chat_id"] is None


@patch("chat_service.eval_log_enabled", return_value=False)
@patch("chat_service.route_and_answer")
def test_strict_true_passed_to_router(mock_route: object, _eval_off: object, client: TestClient) -> None:
    mock_route.return_value = ("ok", [], [], "rag_search", None)
    client.post(
        "/api/v1/chat",
        json={"message": "q", "top_k": 3, "strict": True},
    )
    assert mock_route.call_args.kwargs["strict"] is True


@patch("chat_service.eval_log_enabled", return_value=False)
@patch("chat_service.route_and_answer")
def test_clarification_round_trip(mock_route: object, _eval_off: object, client: TestClient) -> None:
    mock_route.return_value = ("要知識庫還是網路？", [], [], "ask_web_vs_rag", None)
    r = client.post(
        "/api/v1/chat",
        json={"message": "有沒有 AI 新聞", "top_k": 5, "strict": False},
    )
    assert r.json()["next_original_question_for_clarification"] == "有沒有 AI 新聞"

    mock_route.return_value = ("整合答案", ["u"], [], "rag_search", None)
    r2 = client.post(
        "/api/v1/chat",
        json={
            "message": "知識庫",
            "top_k": 5,
            "strict": False,
            "original_question": "有沒有 AI 新聞",
            "clarification_reply": "知識庫",
        },
    )
    assert r2.status_code == 200
    kw = mock_route.call_args.kwargs
    assert kw["original_question"] == "有沒有 AI 新聞"
    assert kw["clarification_reply"] == "知識庫"


@patch("chat_service.eval_log_enabled", return_value=False)
@patch("chat_service.route_and_answer")
def test_chart_confirmation_hint(mock_route: object, _eval_off: object, client: TestClient) -> None:
    mock_route.return_value = (
        "分析…\n\n需要幫我生成圖表嗎？",
        [],
        [],
        "analyze_and_chart",
        {"asked_chart_confirmation": True, "chart_query": "各公司營收"},
    )
    r = client.post("/api/v1/chat", json={"message": "分析財報", "top_k": 8, "strict": False})
    assert r.json()["next_chart_confirmation_question"] == "各公司營收"
