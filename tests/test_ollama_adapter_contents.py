"""Unit tests for llm_client._normalize_contents (B4-15).

重點：先前版本在遇到 list-of-dict（Gemini/OpenAI 風格訊息結構）時會直接 json.dumps
把 JSON 字面量當成 prompt 餵給 Ollama；修正後應正確抽出 text parts。
"""
from __future__ import annotations

from llm_client import _normalize_contents


def test_plain_string() -> None:
    assert _normalize_contents("hello world") == "hello world"


def test_string_is_stripped() -> None:
    assert _normalize_contents("  spaced  ") == "spaced"


def test_none_returns_empty() -> None:
    assert _normalize_contents(None) == ""


def test_list_of_strings() -> None:
    out = _normalize_contents(["part a", "part b"])
    assert "part a" in out
    assert "part b" in out


def test_gemini_style_parts() -> None:
    """Gemini contents: [{"role": "...", "parts": [{"text": "..."}, ...]}]"""
    contents = [
        {"role": "user", "parts": [{"text": "What is 1+1?"}, {"text": "Think step by step."}]}
    ]
    out = _normalize_contents(contents)
    assert "What is 1+1?" in out
    assert "Think step by step." in out
    # 不應把 JSON 字面量丟進來
    assert "parts" not in out
    assert "{" not in out


def test_openai_style_messages() -> None:
    """OpenAI 風格：[{"role": "user", "content": "..."}]"""
    contents = [
        {"role": "system", "content": "you are helpful"},
        {"role": "user", "content": "hi"},
    ]
    out = _normalize_contents(contents)
    assert "you are helpful" in out
    assert "hi" in out
    assert '"role"' not in out


def test_object_with_text_attribute() -> None:
    class _Part:
        def __init__(self, t: str) -> None:
            self.text = t

    out = _normalize_contents([_Part("attr-text-1"), _Part("attr-text-2")])
    assert "attr-text-1" in out
    assert "attr-text-2" in out


def test_mixed_list() -> None:
    contents = [
        "loose string",
        {"role": "user", "parts": [{"text": "structured"}]},
        {"role": "assistant", "content": "openai-style"},
    ]
    out = _normalize_contents(contents)
    assert "loose string" in out
    assert "structured" in out
    assert "openai-style" in out


def test_unrecognised_falls_back_to_json() -> None:
    """完全無法解析的輸入才退回 json.dumps。"""
    out = _normalize_contents({"weird": {"nested": 1}})
    # dict（非 list）直接走 fallback
    assert "weird" in out
