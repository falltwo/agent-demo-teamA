"""Unit tests for _LAW_REF_PATTERN / _extract_law_refs_from_text (B4-07).

涵蓋：
- 合約常見法規（勞基、公司、著作權、個資、公平法等）
- 別稱（勞基法 / 勞動基準法、個資法 / 個人資料保護法、公平法 / 公平交易法）
- 條號含 dash（如勞基法 84-1）
- 條號後接「第 N 項 第 N 款」不影響抽取
- 去重（同法同條只出現一次）
- 空字串與純文字返回 []
"""
from __future__ import annotations

from agent_router import _extract_law_refs_from_text


def test_empty_text_returns_empty() -> None:
    assert _extract_law_refs_from_text("") == []
    assert _extract_law_refs_from_text("   ") == []


def test_plain_text_no_match() -> None:
    assert _extract_law_refs_from_text("這份合約沒有提到任何法條") == []


def test_civil_code() -> None:
    refs = _extract_law_refs_from_text("依民法第184條，侵權行為須負損害賠償責任。")
    assert "民法第184條" in refs


def test_labor_standards_law_with_alias() -> None:
    """勞基法 / 勞動基準法 兩種名稱都要抓得到。"""
    refs = _extract_law_refs_from_text("勞基法第84條 以及 勞動基準法第14條")
    assert "勞基法第84條" in refs
    assert "勞動基準法第14條" in refs


def test_labor_standards_law_dash_article() -> None:
    """勞基法 84-1 條（有 dash）。"""
    refs = _extract_law_refs_from_text("勞基法第 84-1 條")
    # 可能被標準化為 '勞基法第84-1條'
    assert any(ref.startswith("勞基法第84-1") for ref in refs), refs


def test_copyright_and_trademark() -> None:
    text = "著作權法第 65 條與商標法第 35 條"
    refs = _extract_law_refs_from_text(text)
    assert "著作權法第65條" in refs
    assert "商標法第35條" in refs


def test_personal_data_law_aliases() -> None:
    refs = _extract_law_refs_from_text("個資法第5條、個人資料保護法第20條")
    assert "個資法第5條" in refs
    assert "個人資料保護法第20條" in refs


def test_company_law_and_fair_trade() -> None:
    text = "公司法第23條 及 公平法第20條、公平交易法第25條"
    refs = _extract_law_refs_from_text(text)
    assert "公司法第23條" in refs
    assert "公平法第20條" in refs
    assert "公平交易法第25條" in refs


def test_article_with_paragraph_and_item() -> None:
    """條號後接「第 N 項 第 N 款」仍能抽到主條號。"""
    refs = _extract_law_refs_from_text("民法第184條第1項第1款")
    assert "民法第184條" in refs


def test_dedup_same_law_same_article() -> None:
    text = "民法第184條，又說民法第184條"
    refs = _extract_law_refs_from_text(text)
    assert refs.count("民法第184條") == 1


def test_limit_max_refs() -> None:
    """最多回傳 15 條（實作上限）。"""
    text = " ".join(f"民法第{i}條" for i in range(1, 30))
    refs = _extract_law_refs_from_text(text)
    assert len(refs) <= 15
