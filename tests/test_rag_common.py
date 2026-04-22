"""rag_common 單元測試（純函式，不打 API）。"""
import os
from unittest.mock import patch

import pytest

from rag_common import _bm25_tokenize, _char_tokenize, chunk_text, chunk_contract_by_article, is_contract_text, format_context, stable_id


class TestChunkText:
    def test_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   \n\n  ") == []

    def test_smaller_than_chunk_size(self):
        text = "一段短文字"
        out = chunk_text(text, chunk_size=900, overlap=150)
        assert len(out) == 1
        assert out[0] == text.strip()

    def test_chunk_size_and_overlap(self):
        # 造一段超過 chunk_size 的文字
        block = "a" * 500 + "\n\n" + "b" * 500
        out = chunk_text(block, chunk_size=400, overlap=50)
        assert len(out) >= 2

    def test_chunk_size_must_gt_overlap(self):
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_text("x", chunk_size=100, overlap=100)

    def test_contract_dai_x_tiao_becomes_own_chunk(self):
        contract = (
            "第一條 保密義務\n乙方對所取得之機密資訊負保密義務。\n"
            "第二條 保密期間\n自簽署日起生效，滿五年止。\n"
            "第三條 違約責任\n違約者應賠償全部損害。"
        )
        out = chunk_text(contract, chunk_size=1500, overlap=200)
        assert len(out) == 3
        assert out[0].startswith("第一條")
        assert out[1].startswith("第二條")
        assert out[2].startswith("第三條")

    def test_markdown_heading_clauses(self):
        contract = (
            "## 一、保密義務\n乙方應保密。\n\n"
            "## 二、保密期間\n五年。\n\n"
            "## 三、違約責任\n賠償全部損害。"
        )
        out = chunk_text(contract, chunk_size=1500, overlap=200)
        assert len(out) == 3
        assert "保密義務" in out[0]
        assert "保密期間" in out[1]

    def test_oversized_clause_keeps_header_on_continuation(self):
        long_body = "a" * 2000
        text = f"第一條 保密義務\n{long_body}"
        out = chunk_text(text, chunk_size=800, overlap=100)
        assert len(out) >= 2
        # 續段需補上條款首行以保留脈絡
        assert "第一條" in out[1]
        assert "（續）" in out[1]

    def test_clauses_merged_without_blank_line(self):
        # 某些 OCR 結果條款之間沒有空行
        contract = "第一條 保密\n乙方應保密。\n第二條 期間\n五年。"
        out = chunk_text(contract, chunk_size=1500, overlap=200)
        assert len(out) == 2
        assert out[0].startswith("第一條")
        assert out[1].startswith("第二條")


class TestStableId:
    def test_deterministic(self):
        a = stable_id("s", 0, "text")
        b = stable_id("s", 0, "text")
        assert a == b

    def test_different_input_different_id(self):
        a = stable_id("s", 0, "text1")
        b = stable_id("s", 0, "text2")
        assert a != b

    def test_length(self):
        uid = stable_id("source", 3, "hello")
        assert len(uid) == 32


class TestFormatContext:
    def test_empty_matches(self):
        ctx, sources, cleaned = format_context([])
        assert ctx == ""
        assert sources == []
        assert cleaned == []

    def test_single_match(self):
        matches = [
            {"metadata": {"source": "a.txt", "chunk_index": 0, "text": "內容一"}},
        ]
        ctx, sources, cleaned = format_context(matches)
        assert "a.txt#chunk0" in ctx
        assert "[a.txt#chunk0]" in ctx
        assert sources == ["a.txt#chunk0"]
        assert len(cleaned) == 1
        assert cleaned[0]["tag"] == "a.txt#chunk0"
        assert cleaned[0]["text"] == "內容一"

    def test_skips_empty_text(self):
        matches = [
            {"metadata": {"source": "a.txt", "chunk_index": 0, "text": ""}},
        ]
        ctx, sources, cleaned = format_context(matches)
        assert sources == []
        assert cleaned == []


class TestChunkContractByArticle:
    SAMPLE_CONTRACT = (
        "合約基本資訊\n甲方：銀峯資產股份有限公司\n乙方：恆耀科技整合有限公司\n\n"
        "第一條 定義\n本合約所稱「系統」指依附件一所載之企業IT系統。\n\n"
        "第二條 服務範圍\n乙方應依甲方需求提供以下服務：\n"
        "（一）系統設計與開發\n（二）系統整合\n（三）教育訓練\n\n"
        "第三條 服務水準（SLA）\n每月可用性不低於 99.5%。\n"
        "例外排除：\n（一）72小時前通知的維護\n（二）不可抗力\n\n"
        "第四條 驗收\n甲方應於交付後10個工作日內完成驗收測試。\n\n"
        "第五條 保密\n雙方應對下列資訊保密：\n（一）技術文件\n（二）商業機密\n（三）個人資料"
    )

    def test_each_article_is_separate_chunk(self):
        out = chunk_contract_by_article(self.SAMPLE_CONTRACT)
        # 前言 + 5 條 = 6 chunks
        assert len(out) == 6
        article_chunks = [c for c in out if "第" in c and "條" in c]
        assert len(article_chunks) == 5

    def test_articles_not_mixed(self):
        out = chunk_contract_by_article(self.SAMPLE_CONTRACT)
        third = next(c for c in out if "第三條" in c)
        # 第三條應包含 SLA 內容，不應包含第四條
        assert "99.5%" in third
        assert "第四條" not in third

    def test_full_article_content_preserved(self):
        out = chunk_contract_by_article(self.SAMPLE_CONTRACT)
        fifth = next(c for c in out if "第五條" in c)
        assert "技術文件" in fifth
        assert "商業機密" in fifth
        assert "個人資料" in fifth

    def test_long_article_subchunked_with_header(self):
        long_content = "詳細說明。" * 400  # 2000 chars
        text = f"第一條 總則\n{long_content}\n\n第二條 結語\n合約終止。"
        out = chunk_contract_by_article(text, max_article_chars=500)
        sub_chunks = [c for c in out if "第一條" in c]
        assert len(sub_chunks) >= 2
        # 後續子 chunk 應帶「（續）」標記
        assert any("（續）" in c for c in sub_chunks)

    def test_non_contract_falls_back_to_chunk_text(self):
        plain = "這是一份普通備忘錄，沒有任何條文結構。\n\n" * 10
        out = chunk_contract_by_article(plain)
        # 應退回到 chunk_text，不崩潰
        assert isinstance(out, list)
        assert len(out) >= 1

    def test_is_contract_text_detection(self):
        assert is_contract_text(self.SAMPLE_CONTRACT) is True
        assert is_contract_text("普通文字沒有條文") is False
        assert is_contract_text("第一條\n第二條\n只有兩條") is False  # < min_articles=3


class TestBm25Tokenize:
    def test_empty(self):
        assert _bm25_tokenize("") == []
        assert _bm25_tokenize("   ") == []

    def test_char_mode_fallback(self):
        with patch.dict(os.environ, {"BM25_TOKENIZER": "char"}):
            tokens = _bm25_tokenize("第一條 NDA 五百萬")
        # 舊版 char 模式：空白為分界，連續 alnum（含中文）成一 token
        assert "NDA" in tokens
        assert "第一條" in tokens
        assert "五百萬" in tokens

    def test_jieba_mode_merges_terms(self):
        pytest.importorskip("jieba")
        with patch.dict(os.environ, {"BM25_TOKENIZER": "jieba"}):
            tokens = _bm25_tokenize("管轄法院為臺灣臺北地方法院")
        # jieba 至少應把「管轄」或「法院」當作詞；逐字模式不會出現這些多字 token
        assert any(len(t) >= 2 for t in tokens)
        # 不應包含空白
        assert all(t.strip() for t in tokens)

    def test_jieba_consistency_query_matches_doc(self):
        pytest.importorskip("jieba")
        with patch.dict(os.environ, {"BM25_TOKENIZER": "jieba"}):
            doc_tokens = set(_bm25_tokenize("乙方應對機密資訊負保密義務"))
            query_tokens = set(_bm25_tokenize("保密義務"))
        # 查詢詞必須能命中文件（詞級一致性）
        assert query_tokens & doc_tokens

    def test_char_tokenize_pure_function(self):
        tokens = _char_tokenize("abc 123 第一條")
        assert "abc" in tokens
        assert "123" in tokens
        assert "第一條" in tokens
