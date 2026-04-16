"""Unit tests for llm_client utility functions."""

from llm_client import _normalize_ollama_base_url


def test_normalize_no_v1() -> None:
    assert _normalize_ollama_base_url("http://host:11434") == "http://host:11434/v1"


def test_normalize_with_v1_no_repeat() -> None:
    """已含 /v1 時不應產生 /v1/v1。"""
    assert _normalize_ollama_base_url("http://host:11434/v1") == "http://host:11434/v1"


def test_normalize_trailing_slash() -> None:
    """尾部斜線應被清除。"""
    assert _normalize_ollama_base_url("http://host:11434/v1/") == "http://host:11434/v1"


def test_normalize_empty_uses_default() -> None:
    assert _normalize_ollama_base_url("") == "http://127.0.0.1:11434/v1"


def test_normalize_none_uses_default() -> None:
    # type: ignore[arg-type]
    assert _normalize_ollama_base_url(None) == "http://127.0.0.1:11434/v1"  # type: ignore[arg-type]


def test_normalize_custom_path_without_v1() -> None:
    assert _normalize_ollama_base_url("http://192.168.1.10:11434") == "http://192.168.1.10:11434/v1"
