"""Eval 唯讀 API 測試。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services import eval_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_get_eval_config(client: TestClient) -> None:
    r = client.get("/api/v1/eval/config")
    assert r.status_code == 200
    assert "eval_log_enabled" in r.json()
    assert isinstance(r.json()["eval_log_enabled"], bool)


@patch("backend.services.eval_service.load_online_runs")
def test_get_eval_runs(mock_load: object, client: TestClient) -> None:
    from backend.schemas.eval import EvalRunEntry

    mock_load.return_value = (
        [
            EvalRunEntry(
                timestamp="2026-01-01T00:00:00+00:00",
                question="q1",
                answer="a1",
                tool_name="rag_search",
                latency_sec=1.2,
                top_k=5,
                source_count=2,
                chat_id=None,
            )
        ],
        True,
    )
    r = client.get("/api/v1/eval/runs")
    assert r.status_code == 200
    data = r.json()
    assert data["eval_log_enabled"] is True
    assert len(data["entries"]) == 1
    assert data["entries"][0]["tool_name"] == "rag_search"
    assert data["limit"] == 500


def test_eval_batch_list_and_detail(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eval_service, "_eval_runs_dir", lambda: tmp_path)

    (tmp_path / "run_demo_results.jsonl").write_text(
        json.dumps(
            {
                "id": "1",
                "question": "hello",
                "predicted_tool": "rag_search",
                "expected_tool": "rag_search",
                "success": True,
                "latency_sec": 0.5,
                "answer": "ok",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "run_demo_metrics.json").write_text(
        json.dumps({"total": 1, "routing_accuracy": 100, "routing_accuracy_n": 1}),
        encoding="utf-8",
    )

    lr = client.get("/api/v1/eval/batch/runs")
    assert lr.status_code == 200
    assert "run_demo" in lr.json()["run_ids"]

    d = client.get("/api/v1/eval/batch/run_demo")
    assert d.status_code == 200
    body = d.json()
    assert body["run_id"] == "run_demo"
    assert body["metrics"]["total"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["question"] == "hello"


def test_eval_batch_detail_404(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(eval_service, "_eval_runs_dir", lambda: tmp_path)
    r = client.get("/api/v1/eval/batch/does_not_exist")
    assert r.status_code == 404
