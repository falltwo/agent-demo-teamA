"""Parse 合約風險評估 markdown 為結構化 RiskCard list。

`contract_risk_agent` 與 `contract_risk_with_law_search` 兩條合約路徑都輸出
同一套 markdown 格式：
    第X條 [標題]
    **【條款類型】** ...
    **【風險等級】** 高風險 / 中風險 / 低風險
    **【原文引述】** ...
    **【法務實務推演】** ...
    **【修改建議】** ...

此模組把 answer 重新解析成結構化資料，放進 `ChatResponse.extra["risk_cards"]`，
前端就不必在 markdown 上用 regex 硬拆，LLM 回應格式小幅變動時也只要改這裡一處。

Parser 失敗或回傳空 list 時，前端會自動 fallback 到現有 markdown 渲染（不會壞畫面）。
"""
from __future__ import annotations

import re
from typing import Any

Severity = str  # Literal["high", "medium", "low"] 但 pydantic dump 時用 str 即可

ARTICLE_NUM = r"[\d一二三四五六七八九十百千萬]+"
_ARTICLE_SPLIT_RE = re.compile(rf"(?=第\s*{ARTICLE_NUM}\s*條[\s：:])")
_ARTICLE_HEADER_RE = re.compile(rf"第\s*({ARTICLE_NUM})\s*條[\s：:]*([^\n【]*)")
_FIELD_RE_CACHE: dict[str, re.Pattern[str]] = {}

_SELF_CHECK_MARKERS = (
    "**【AI 自檢】**",
    "**【免責聲明】**",
    "\n---\n\n**【AI 自檢】**",
)
_LAW_REF_RE = re.compile(
    r"[\u4e00-\u9fa5]+法第\s*[\d一二三四五六七八九十百千]+\s*條(?:之\d+)?(?:第[\d一二三四五六七八九十]+項)?"
)


def _field_re(label: str) -> re.Pattern[str]:
    if label not in _FIELD_RE_CACHE:
        _FIELD_RE_CACHE[label] = re.compile(rf"【{label}】([\s\S]*?)(?=【|$)")
    return _FIELD_RE_CACHE[label]


def _extract_field(block: str, label: str) -> str:
    m = _field_re(label).search(block)
    return (m.group(1).strip() if m else "").strip()


def _severity_from(label: str) -> Severity:
    if "高風險" in label:
        return "high"
    if "中風險" in label:
        return "medium"
    return "low"


_MD_EMPHASIS_RE = re.compile(r"\*{1,3}")


def _strip_md(s: str) -> str:
    return _MD_EMPHASIS_RE.sub("", s or "").strip()


def _find_law_refs(block: str) -> list[str]:
    """擷取「民法第188條」「政府採購法第XX條」等引用；去重保序。"""
    return list(dict.fromkeys(_LAW_REF_RE.findall(block)))


def _find_chunk_hint(block: str) -> str | None:
    m = re.search(r"\[(\d+)\]", block)
    if m:
        return f"[{m.group(1)}]"
    m = re.search(r"#chunk(\d+)", block, re.IGNORECASE)
    if m:
        return f"#chunk{m.group(1)}"
    return None


def _trim_to_main_assessment(answer: str) -> str:
    """截除 AI 自檢 / 免責聲明段落，只保留主評估區塊。"""
    head = answer
    for marker in _SELF_CHECK_MARKERS:
        idx = head.find(marker)
        if idx >= 0:
            head = head[:idx]
    return head


def parse_risk_cards(answer: str, *, limit: int = 15) -> list[dict[str, Any]]:
    """從合約風險評估 markdown 解析出 RiskCard list。

    * 主評估段落只取到 AI 自檢 / 免責聲明之前。
    * 以 `第X條` 為切分邊界，每段需同時含「條號」與至少一個結構化 tag
      （【風險等級】/【法務實務推演】/【修改建議】其一）才算一張卡。
    * 解析失敗時回傳空 list — 由前端 fallback 到 markdown 渲染。
    """
    if not answer or not answer.strip():
        return []

    head = _trim_to_main_assessment(answer)
    blocks = _ARTICLE_SPLIT_RE.split(head)

    cards: list[dict[str, Any]] = []
    seq = 0
    for block in blocks:
        if not re.search(rf"第\s*{ARTICLE_NUM}\s*條", block):
            continue
        if not re.search(r"【風險等級】|【法務實務推演】|【修改建議】", block):
            continue

        header = _ARTICLE_HEADER_RE.search(block)
        article = header.group(1).strip() if header else ""
        title = _strip_md(header.group(2).strip()) if header else ""
        if not title:
            title = f"第{article}條" if article else f"條款 {seq + 1}"

        clause_type = _strip_md(_extract_field(block, "條款類型"))
        risk_label = _strip_md(_extract_field(block, "風險等級"))
        quoted_text = _strip_md(_extract_field(block, "原文引述"))
        reasoning = _strip_md(_extract_field(block, "法務實務推演"))
        suggestion = _strip_md(_extract_field(block, "修改建議"))
        description = _strip_md(_extract_field(block, "具體內容描述"))

        cards.append(
            {
                "id": f"card-{seq}",
                "article": article or None,
                "title": title,
                "clauseType": clause_type or None,
                "riskLevel": _severity_from(risk_label),
                "riskLabel": risk_label or None,
                "quotedText": quoted_text or None,
                "reasoning": reasoning or description or None,
                "suggestion": suggestion or None,
                "lawRefs": _find_law_refs(block),
                "chunkHint": _find_chunk_hint(block),
            }
        )
        seq += 1
        if seq >= limit:
            break
    return cards
