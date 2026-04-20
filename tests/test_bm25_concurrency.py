"""Unit tests for BM25 corpus file lock + atomic write (B4-06) in rag_common.

以多 process（不只多 thread）驗證 append_bm25_corpus 在並發呼叫下不會有資料丟失：
- 總筆數 == 期望（每 worker append N 筆）
- JSON 檔永遠是合法 JSON（no half-written truncation）
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path

import pytest


def _worker(corpus_path: str, worker_id: int, n: int) -> None:
    # subprocess 專屬 process；需自行設定 env 再 import rag_common
    os.environ["BM25_CORPUS_PATH"] = corpus_path
    from rag_common import append_bm25_corpus  # local import so env var 已生效

    chunks = [
        {
            "id": f"w{worker_id}-c{i}",
            "text": f"worker {worker_id} chunk {i}",
            "source": f"src-w{worker_id}",
            "chunk_index": i,
        }
        for i in range(n)
    ]
    append_bm25_corpus(chunks)


def test_concurrent_append_preserves_all_rows(tmp_path: Path) -> None:
    corpus_path = tmp_path / "bm25_corpus.json"
    workers = 4
    per_worker = 10

    # 使用 spawn 避免 fork 繼承 FD 導致 flock 語意異常（Linux fork 會複製 FD，但不共享 lock owner）
    ctx = mp.get_context("spawn")
    procs = [
        ctx.Process(target=_worker, args=(str(corpus_path), wid, per_worker))
        for wid in range(workers)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
    for p in procs:
        assert p.exitcode == 0, f"worker crashed: exit={p.exitcode}"

    assert corpus_path.exists(), "BM25 corpus file should be created"
    # 檔案必須是合法 JSON
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == workers * per_worker, (
        f"rows lost: expected {workers * per_worker}, got {len(data)}"
    )
    # 所有 worker 的資料都該保留
    ids = {row["id"] for row in data if isinstance(row, dict)}
    for wid in range(workers):
        for i in range(per_worker):
            assert f"w{wid}-c{i}" in ids, f"missing id w{wid}-c{i}"


def test_atomic_write_never_leaves_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """成功寫入後不應留下 .tmp 暫存檔。"""
    monkeypatch.setenv("BM25_CORPUS_PATH", str(tmp_path / "bm25_corpus.json"))
    from rag_common import append_bm25_corpus, get_bm25_corpus_path

    append_bm25_corpus(
        [{"id": "a1", "text": "hello", "source": "s", "chunk_index": 0}]
    )
    p = get_bm25_corpus_path()
    assert p.exists()
    tmp = p.with_suffix(p.suffix + ".tmp")
    assert not tmp.exists(), "tmp file should be replaced atomically"
