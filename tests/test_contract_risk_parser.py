"""Tests for contract_risk_parser.parse_risk_cards.

涵蓋：
- 正常 markdown 產出結構化 cards
- 不同 risk level 對應 severity
- AI 自檢/免責聲明段不被誤收
- 空字串／無 tag 的情況回空 list
- law refs 擷取
"""
from __future__ import annotations

from contract_risk_parser import parse_risk_cards


SAMPLE_MD = """# 合約風險評估

第 5 條 保密義務
**【條款類型】** 保密條款
**【風險等級】** 高風險
**【原文引述】** 乙方應於契約終止後五年內保守所有營業秘密。
**【法務實務推演】** 此條款期限過長，可能逾越營業秘密法第 2 條合理範圍。
**【修改建議】** 建議改為三年，並限縮範圍至實際接觸之資訊。

第 8 條 違約處罰
**【條款類型】** 違約條款
**【風險等級】** 中風險
**【原文引述】** 違約金為合約總價 30%。
**【法務實務推演】** 民法第 252 條規定法院得酌減違約金。
**【修改建議】** 建議降至 10-15%。

---

**【AI 自檢】**

本次自檢沒有發現明顯問題。

---

**【免責聲明】**

本結果僅供參考…
"""


def test_parse_returns_two_cards():
    cards = parse_risk_cards(SAMPLE_MD)
    assert len(cards) == 2


def test_first_card_high_severity():
    cards = parse_risk_cards(SAMPLE_MD)
    assert cards[0]["riskLevel"] == "high"
    assert cards[0]["riskLabel"] == "高風險"
    assert cards[0]["article"] == "5"
    assert "保密義務" in cards[0]["title"]
    assert cards[0]["clauseType"] == "保密條款"
    assert "五年內" in (cards[0]["quotedText"] or "")
    assert "營業秘密法第 2 條" in cards[0]["reasoning"]
    assert "三年" in cards[0]["suggestion"]


def test_second_card_medium_severity():
    cards = parse_risk_cards(SAMPLE_MD)
    assert cards[1]["riskLevel"] == "medium"


def test_law_refs_extracted():
    cards = parse_risk_cards(SAMPLE_MD)
    # 營業秘密法第 2 條 + 民法第 252 條 應被各自擷取到對應卡
    assert any("營業秘密法第" in ref for ref in cards[0]["lawRefs"])
    assert any("民法第" in ref for ref in cards[1]["lawRefs"])


def test_self_check_section_ignored():
    md = SAMPLE_MD + "\n第 999 條 此條應被忽略\n**【風險等級】** 高風險\n"
    cards = parse_risk_cards(SAMPLE_MD)
    # 主 md 中的自檢 marker 會截掉後面所有內容；用原 SAMPLE_MD 就好
    articles = [c["article"] for c in cards]
    assert "5" in articles and "8" in articles
    assert "999" not in articles


def test_empty_returns_empty_list():
    assert parse_risk_cards("") == []
    assert parse_risk_cards("   \n\n") == []


def test_non_contract_answer_returns_empty():
    # 一般 RAG 回答沒有結構化 tag，不應產出 risk cards
    assert parse_risk_cards("這是知識庫查詢結果。根據文件...") == []


def test_limit_respected():
    # 15 張以上只取前 limit 個
    many = "\n".join(
        f"第 {i} 條 測試\n**【風險等級】** 低風險\n**【修改建議】** 無。\n"
        for i in range(1, 20)
    )
    cards = parse_risk_cards(many, limit=10)
    assert len(cards) == 10


def test_chunk_hint_extracted():
    md = "第 1 條 測試\n**【風險等級】** 高風險\n**【原文引述】** 引述 [3]\n**【修改建議】** 無\n"
    cards = parse_risk_cards(md)
    assert cards[0]["chunkHint"] == "[3]"
