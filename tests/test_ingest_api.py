"""Ingest API：mock `ingest_file_items` 與向量庫 client，驗證 multipart 契約。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@patch("backend.services.ingest_adapter.ingest_file_items")
@patch("backend.services.ingest_adapter.get_cached_rag_stack")
def test_ingest_upload_returns_sync_shape(
    mock_stack: MagicMock,
    mock_ingest: MagicMock,
    client: TestClient,
) -> None:
    mock_stack.return_value = (
        MagicMock(),
        MagicMock(),
        MagicMock(),
        768,
        "m",
        "gemini-embedding-001",
        "idx",
    )
    mock_ingest.return_value = (
        3,
        [{"source": "uploaded/chat-1/a.pdf", "chunk_count": 3, "chat_id": "chat-1"}],
    )
    files = [("files", ("note.txt", b"hello world", "text/plain"))]
    data = {"chat_id": "chat-1"}
    res = client.post("/api/v1/ingest/upload", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "sync"
    assert body["chunks_ingested"] == 3
    assert body["sources_updated"][0]["source"] == "uploaded/chat-1/a.pdf"
    assert body["sources_updated"][0]["chunk_count"] == 3
    mock_ingest.assert_called_once()


def test_sources_list_returns_entries(client: TestClient) -> None:
    with patch("backend.api.routes.ingest.list_sources", return_value=[{"source": "x", "chunk_count": 1, "chat_id": None}]):
        r = client.get("/api/v1/sources")
    assert r.status_code == 200
    assert r.json()["entries"][0]["source"] == "x"
