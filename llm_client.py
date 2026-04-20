"""Chat model adapters and provider selection.

This module keeps the existing `client.models.generate_content(...) -> .text`
shape so upper layers (`agent_router`, `rag_graph`, Streamlit, FastAPI) do not
need to care which provider is active.
"""

from __future__ import annotations

import json
import os
from typing import Any, Tuple

from dotenv import load_dotenv

# 模組載入時 load 一次即可；後續 os.getenv 直接讀 process env。
# 保持此處而非 backend/main.py：Streamlit / eval CLI 也會 import 本模組，須確保環境變數載入。
# load_dotenv 預設不覆蓋已存在的 env，對已 export 的環境無副作用。
load_dotenv()

_STAGE_MODEL_ENV_MAP: dict[str, tuple[str, ...]] = {
    "router": ("CHAT_ROUTER_MODEL", "OLLAMA_ROUTER_MODEL"),
    "rag_rewrite": ("CHAT_RAG_REWRITE_MODEL", "OLLAMA_RAG_REWRITE_MODEL"),
    "rag_aux_query": ("CHAT_RAG_AUX_QUERY_MODEL", "OLLAMA_RAG_AUX_QUERY_MODEL"),
    "rag_rerank": ("CHAT_RAG_RERANK_MODEL", "OLLAMA_RAG_RERANK_MODEL"),
    "rag_package": ("CHAT_RAG_PACKAGE_MODEL", "OLLAMA_RAG_PACKAGE_MODEL"),
    "rag_generate": ("CHAT_RAG_GENERATE_MODEL", "OLLAMA_RAG_GENERATE_MODEL"),
    "rag_summary": ("CHAT_RAG_SUMMARY_MODEL", "OLLAMA_RAG_SUMMARY_MODEL"),
    "small_talk": ("CHAT_SMALL_TALK_MODEL", "OLLAMA_SMALL_TALK_MODEL"),
    "analysis": ("CHAT_ANALYSIS_MODEL", "OLLAMA_ANALYSIS_MODEL"),
    "research_generate": ("CHAT_RESEARCH_GENERATE_MODEL", "OLLAMA_RESEARCH_GENERATE_MODEL"),
    "contract_risk_generate": ("CHAT_CONTRACT_RISK_GENERATE_MODEL", "OLLAMA_CONTRACT_RISK_GENERATE_MODEL"),
    "contract_risk_verify": ("CHAT_CONTRACT_RISK_VERIFY_MODEL", "OLLAMA_CONTRACT_RISK_VERIFY_MODEL"),
}

_STAGE_TIMEOUT_ENV_MAP: dict[str, tuple[str, ...]] = {
    "router": ("CHAT_ROUTER_TIMEOUT_SEC", "OLLAMA_ROUTER_TIMEOUT_SEC"),
    "rag_rewrite": ("CHAT_RAG_REWRITE_TIMEOUT_SEC", "OLLAMA_RAG_REWRITE_TIMEOUT_SEC"),
    "rag_aux_query": ("CHAT_RAG_AUX_QUERY_TIMEOUT_SEC", "OLLAMA_RAG_AUX_QUERY_TIMEOUT_SEC"),
    "rag_rerank": ("CHAT_RAG_RERANK_TIMEOUT_SEC", "OLLAMA_RAG_RERANK_TIMEOUT_SEC"),
    "rag_package": ("CHAT_RAG_PACKAGE_TIMEOUT_SEC", "OLLAMA_RAG_PACKAGE_TIMEOUT_SEC"),
    "rag_generate": ("CHAT_RAG_GENERATE_TIMEOUT_SEC", "OLLAMA_RAG_GENERATE_TIMEOUT_SEC"),
    "analysis": ("CHAT_ANALYSIS_TIMEOUT_SEC", "OLLAMA_ANALYSIS_TIMEOUT_SEC"),
    "research_generate": ("CHAT_RESEARCH_GENERATE_TIMEOUT_SEC", "OLLAMA_RESEARCH_GENERATE_TIMEOUT_SEC"),
    "contract_risk_generate": ("CHAT_CONTRACT_RISK_GENERATE_TIMEOUT_SEC", "OLLAMA_CONTRACT_RISK_GENERATE_TIMEOUT_SEC"),
    "contract_risk_verify": ("CHAT_CONTRACT_RISK_VERIFY_TIMEOUT_SEC", "OLLAMA_CONTRACT_RISK_VERIFY_TIMEOUT_SEC"),
    "small_talk": ("CHAT_SMALL_TALK_TIMEOUT_SEC", "OLLAMA_SMALL_TALK_TIMEOUT_SEC"),
}


def _chat_provider() -> str:
    return (os.getenv("CHAT_PROVIDER", "") or "").strip().lower()


def _default_model_for_provider(chat_provider: str) -> str:
    if chat_provider in ("ollama", "local"):
        return (os.getenv("OLLAMA_CHAT_MODEL", "gemma3:27b") or "gemma3:27b").strip()
    use_groq = os.getenv("EVAL_USE_GROQ", "").strip().lower() in ("1", "true", "yes")
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if use_groq and groq_key:
        return (os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile").strip()
    return (os.getenv("GEMINI_CHAT_MODEL", "gemini-3.1-flash-lite-preview") or "gemini-3.1-flash-lite-preview").strip()


def get_model_for_stage(stage: str, default_model: str | None = None) -> str:
    """Resolve stage-specific model override, then fall back to default model."""
    chat_provider = _chat_provider()
    base_model = (default_model or _default_model_for_provider(chat_provider)).strip()
    env_keys = _STAGE_MODEL_ENV_MAP.get(stage, ())
    for key in env_keys:
        candidate = (os.getenv(key, "") or "").strip()
        if candidate:
            return candidate
    return base_model


def get_timeout_for_stage(stage: str, default_timeout_sec: float | None = None) -> float | None:
    """Resolve stage-specific timeout override in seconds."""
    env_keys = _STAGE_TIMEOUT_ENV_MAP.get(stage, ())
    for key in env_keys:
        raw = (os.getenv(key, "") or "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 0:
            return value
    return default_timeout_sec


class _TextResponse:
    """Minimal response object compatible with Gemini usage sites."""

    def __init__(self, text: str):
        self.text = text


def _normalize_ollama_base_url(base_url: str) -> str:
    base = (base_url or "http://127.0.0.1:11434").rstrip("/")
    # 統一剝掉末尾 /v1（若已有），再加回，防止 /v1/v1 重複
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    return f"{base}/v1"


def _extract_text_from_openai_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
                continue
            if isinstance(part, dict):
                text = part.get("text")
                if text:
                    parts.append(str(text))
                continue
            text = getattr(part, "text", None)
            if text:
                parts.append(str(text))
        return "\n".join(p.strip() for p in parts if p and p.strip())
    return str(content or "").strip()


def _normalize_contents(contents: Any) -> str:
    """將 Gemini 慣用的 contents（字串 / list-of-dict / list-of-parts）壓成純 user 字串。

    對 list 型輸入不再盲目 json.dumps，而是抽出 text parts 串接；最後退一步才用 json.dumps。
    這樣多輪訊息結構雖會被壓平但至少能保留語意，而非把 JSON 字面量當 prompt 餵給 LLM。
    """
    if isinstance(contents, str):
        return contents.strip()
    if contents is None:
        return ""
    if isinstance(contents, list):
        texts: list[str] = []
        for item in contents:
            if isinstance(item, str):
                if item.strip():
                    texts.append(item.strip())
                continue
            if isinstance(item, dict):
                # Gemini content 格式：{"role": "...", "parts": [{"text": "..."}]}
                parts = item.get("parts")
                if isinstance(parts, list):
                    for p in parts:
                        if isinstance(p, dict):
                            t = p.get("text")
                            if t:
                                texts.append(str(t).strip())
                        elif isinstance(p, str) and p.strip():
                            texts.append(p.strip())
                    continue
                # OpenAI 格式：{"role": "...", "content": "..."}
                t = item.get("text") or item.get("content")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
                    continue
            # 物件帶 .text 屬性
            t = getattr(item, "text", None)
            if isinstance(t, str) and t.strip():
                texts.append(t.strip())
        if texts:
            return "\n\n".join(texts)
    try:
        return json.dumps(contents, ensure_ascii=False)
    except Exception:
        return str(contents)


class GroqAdapter:
    """Adapt Groq to the same interface used by Gemini callsites."""

    def __init__(self, api_key: str, default_model: str = "llama-3.3-70b-versatile"):
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._default_model = default_model

    @property
    def models(self) -> Any:
        return self

    def generate_content(
        self,
        model: str | None = None,
        contents: str | None = None,
        config: Any = None,
        **kwargs: Any,
    ) -> _TextResponse:
        system = ""
        if config is not None and hasattr(config, "system_instruction"):
            system = (config.system_instruction or "").strip()
        user_content = (contents or "").strip() if isinstance(contents, str) else ""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content or "(empty prompt)"})

        model_name = model or self._default_model
        resp = self._client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        text = ""
        if resp.choices:
            msg = resp.choices[0].message
            if msg and getattr(msg, "content", None):
                text = (msg.content or "").strip()
        return _TextResponse(text=text)


class OllamaAdapter:
    """Use Ollama via OpenAI-compatible API while preserving Gemini-like shape."""

    def __init__(
        self,
        *,
        base_url: str,
        default_model: str = "gemma3:27b",
        api_key: str = "ollama",
        timeout_sec: float = 240.0,
    ):
        from openai import OpenAI

        self._supports_request_timeout = True
        self._client = OpenAI(
            base_url=_normalize_ollama_base_url(base_url),
            api_key=api_key,
            timeout=timeout_sec,
        )
        self._default_model = default_model

    @property
    def models(self) -> Any:
        return self

    def generate_content(
        self,
        model: str | None = None,
        contents: Any = None,
        config: Any = None,
        **kwargs: Any,
    ) -> _TextResponse:
        model_name = model or self._default_model
        prompt = _normalize_contents(contents)
        if not prompt:
            prompt = "(empty prompt)"

        system = ""
        if config is not None and hasattr(config, "system_instruction"):
            system = str(getattr(config, "system_instruction") or "").strip()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        req: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
        }

        if config is not None:
            temperature = getattr(config, "temperature", None)
            top_p = getattr(config, "top_p", None)
            max_tokens = getattr(config, "max_output_tokens", None)
            response_mime_type = getattr(config, "response_mime_type", None)
            if temperature is not None:
                req["temperature"] = float(temperature)
            if top_p is not None:
                req["top_p"] = float(top_p)
            if max_tokens is not None:
                req["max_tokens"] = int(max_tokens)
            if response_mime_type == "application/json":
                req["response_format"] = {"type": "json_object"}

        request_timeout_sec = kwargs.get("request_timeout_sec")
        if request_timeout_sec is not None:
            try:
                timeout_value = float(request_timeout_sec)
            except (TypeError, ValueError):
                timeout_value = None
            if timeout_value and timeout_value > 0:
                req["timeout"] = timeout_value

        resp = self._client.chat.completions.create(**req)
        text = ""
        if resp.choices:
            msg = resp.choices[0].message
            text = _extract_text_from_openai_message_content(getattr(msg, "content", None))
        return _TextResponse(text=text)


def get_chat_client_and_model() -> Tuple[Any, str]:
    """Return `(chat_client, model_name)` for configured provider.

    Providers:
    - `CHAT_PROVIDER=ollama`: local Ollama (recommended for DGX local deployment)
    - `EVAL_USE_GROQ=1` with `GROQ_API_KEY`: Groq
    - default fallback: Gemini
    """

    chat_provider = os.getenv("CHAT_PROVIDER", "").strip().lower()
    if chat_provider in ("ollama", "local"):
        model = os.getenv("OLLAMA_CHAT_MODEL", "gemma3:27b").strip() or "gemma3:27b"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"
        timeout_sec = float(os.getenv("OLLAMA_TIMEOUT_SEC", "240").strip() or "240")
        api_key = os.getenv("OLLAMA_API_KEY", "ollama").strip() or "ollama"
        return OllamaAdapter(
            base_url=base_url,
            default_model=model,
            api_key=api_key,
            timeout_sec=timeout_sec,
        ), model

    use_groq = os.getenv("EVAL_USE_GROQ", "").strip().lower() in ("1", "true", "yes")
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if use_groq and groq_key:
        model = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
        return GroqAdapter(api_key=groq_key, default_model=model), model

    from google import genai

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY in .env (or set CHAT_PROVIDER=ollama).")
    model = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.1-flash-lite-preview")
    client = genai.Client(api_key=google_api_key)
    return client, model
