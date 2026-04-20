"""Unit tests for LLM call budget (B4-05) in rag_graph.

驗證：
- 未呼叫 _reset_llm_budget 時（非 run_rag 直接入口），_bump_llm_call 不會拋錯。
- 呼叫 _reset_llm_budget(n) 後，前 n 次不拋，第 n+1 次拋 LLMBudgetExceeded。
- 計數器透過 ContextVar 隔離，重置後從零開始。
"""
from __future__ import annotations

import pytest

from rag_graph import (
    LLMBudgetExceeded,
    _bump_llm_call,
    _get_llm_calls,
    _reset_llm_budget,
)


def test_bump_without_reset_is_noop() -> None:
    """未初始化計數器（非 run_rag 入口）不應拋錯，回傳 0。"""
    # 新的 ContextVar default=None，直接 bump 應安全
    n = _bump_llm_call("test_stage_no_reset")
    assert n == 0


def test_reset_starts_from_zero() -> None:
    _reset_llm_budget(5)
    assert _get_llm_calls() == 0


def test_bump_within_budget_ok() -> None:
    _reset_llm_budget(3)
    assert _bump_llm_call("s1") == 1
    assert _bump_llm_call("s2") == 2
    assert _bump_llm_call("s3") == 3
    assert _get_llm_calls() == 3


def test_bump_over_budget_raises() -> None:
    _reset_llm_budget(2)
    _bump_llm_call("s1")
    _bump_llm_call("s2")
    with pytest.raises(LLMBudgetExceeded) as exc:
        _bump_llm_call("s3_over")
    assert "s3_over" in str(exc.value)


def test_reset_is_isolated_per_invocation() -> None:
    _reset_llm_budget(1)
    _bump_llm_call("once")
    # 重置後重新從零計數
    _reset_llm_budget(2)
    assert _get_llm_calls() == 0
    _bump_llm_call("after_reset")
    assert _get_llm_calls() == 1


def test_budget_minimum_is_one() -> None:
    """_reset_llm_budget 會 max(1, n)，避免傳入 0/負數時永遠拋錯。"""
    _reset_llm_budget(0)
    # 至少允許一次呼叫
    _bump_llm_call("first")
    with pytest.raises(LLMBudgetExceeded):
        _bump_llm_call("second")
