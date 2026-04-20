"""集中化 backend logging 設定。

在 `create_app()` 開頭呼叫 `configure_logging()` 一次，以後各模組只需：

    import logging
    logger = logging.getLogger(__name__)

即可輸出帶模組名稱、時間戳與 traceback 的結構化 log 至 stderr（被 journald 收走）。

環境變數：
- `LOG_LEVEL`   預設 INFO，可設 DEBUG/WARNING/ERROR
- `LOG_FORMAT`  預設「人類可讀」；設 `json` 以後升級結構化 log 時可切換
"""

from __future__ import annotations

import logging
import os
import sys  # noqa: F401

_CONFIGURED = False


def configure_logging() -> None:
    """冪等地設定 root logger。重複呼叫不會增加 handler。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    # 清掉前人（uvicorn / streamlit）已經掛上的 root handler，避免重複輸出
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)

    # 調低第三方吵雜 logger（可視情況放行）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _CONFIGURED = True


def configure_threadpool() -> None:
    """拉高 FastAPI sync-def 共用的 anyio threadpool 上限。

    Chat 端點是同步 def，呼叫 30-120s 的 LLM；預設 40 thread 的 pool 在高並發會飢餓。
    透過環境變數 `API_THREADPOOL_LIMIT` 調整（預設 100）。
    """
    try:
        limit = int(os.getenv("API_THREADPOOL_LIMIT", "100"))
    except (TypeError, ValueError):
        limit = 100
    if limit <= 0:
        return
    try:
        # anyio.to_thread.current_default_thread_limiter 只能在 event loop 內呼叫。
        # 這裡改透過環境變數 + anyio 的 capacity 屬性於 startup event 設。
        import anyio
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = limit
        logging.getLogger(__name__).info("anyio threadpool limit set to %d", limit)
    except Exception as e:
        logging.getLogger(__name__).warning(
            "Failed to raise anyio threadpool limit: %s", e, exc_info=True
        )
