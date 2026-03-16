# 自主式合約風險評估代理系統

> 幫企業在**數分鐘內**完成合約第一輪審閱：自動標出風險條款、給出修改建議與法條出處，並可依對話僅檢索該次上傳檔案，兼顧效率與可追溯性。

本專案為 **2026 智慧創新大賞 AI 應用類** 參賽作品，以 **RAG + 多工具 Agent** 為核心，結合合約風險分析、司法院法條查詢、知識庫問答與 Eval 驗證；前端為 Streamlit 多對話介面，支援上傳合約（.txt / .md / .pdf / .docx）後一鍵審閱或自然語言提問。

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 快速開始

**1. 環境**

- 複製 `.env.example` 為 `.env`，填入 **PINECONE_API_KEY**、**PINECONE_INDEX**、**GOOGLE_API_KEY**（必填）。
- 合約＋法條查詢需 **TAVILY_API_KEY**；其餘見 `.env.example`。

**2. 依賴與灌入**

```bash
# 安裝依賴（需 uv：https://docs.astral.sh/uv/）
uv sync

# 將合約或文件放入 data/，建立好 Pinecone index 後執行灌入
uv run rag_ingest.py
```

**3. 啟動**

```bash
uv run streamlit run streamlit_app.py
```

瀏覽器開啟後可：展開「為此對話上傳並灌入文件」上傳合約並灌入，或直接對已灌入內容提問。**側欄「合約審閱提示」** 內有「一鍵審閱（僅知識庫）」與「一鍵審閱（含法條查詢）」按鈕；或輸入：「請審閱這份合約的風險條款」「合約風險評估並查相關法條」。

---

## 技術亮點

| 面向 | 說明 |
|------|------|
| **定位** | 單一對話入口完成：合約審閱、法條查詢、知識庫問答、圖表；依意圖自動路由至對應工具或專家。 |
| **RAG** | LangGraph（retrieve → generate）、雙 Prompt（調查員打包脈絡 → 判官風險判定）、可選多查詢檢索、**Hybrid（向量 + BM25）**、MMR／LLM rerank。 |
| **合約＋法條** | **contract_risk_with_law_search**：RAG 取合約 → 抽法條字號 → Tavily 查司法院／網路 → 整合風險評估與法條重點 → AI 自檢 → 免責聲明。 |
| **可觀測** | Eval 題集（`eval/eval_set.json`、`eval/eval_set_contract.json`）、`run_eval.py` 產出 routing 準確率、Tool 成功率、延遲；Streamlit 可檢視 Eval 運行記錄與批次結果。 |

**技術棧**：Google Gemini（LLM + embedding）、Pinecone、LangGraph、Streamlit；可選 Tavily、Firecrawl、ECharts、Groq（Eval）。

---

## 如何試用／Demo

1. 確認 `.env` 已填、側欄「嚴格只根據知識庫回答」**未勾選**（才能走合約工具）。
2. 若有先灌入：可問「列出目前知識庫有哪些文件」。
3. 點側欄「一鍵審閱（僅知識庫）」或輸入「請審閱這份合約的風險條款」→ 檢視風險條款與「查看檢索片段」。
4. 若有 TAVILY_API_KEY：點「一鍵審閱（含法條查詢）」或輸入「合約風險評估並查相關法條」→ 檢視風險＋法條重點＋免責聲明。

完整步驟與檢查清單見 **[docs/Demo_操作指南.md](docs/Demo_操作指南.md)**。

---

## 專案結構與文件

| 目錄／檔案 | 說明 |
|------------|------|
| **streamlit_app.py** | Streamlit 主程式（多對話、上傳灌入、問答、Eval 檢視）。 |
| **agent_router.py** | 總管 Agent：工具路由（RAG、合約／法條、專家、圖表、網路等）。 |
| **rag_graph.py** | RAG 核心：檢索、Hybrid、雙 Prompt、generate；`retrieve_only` 供專家使用。 |
| **rag_common.py** | 共用：chunk、embed、Pinecone/Gemini 初始化、BM25 語料與 RRF 合併。 |
| **expert_agents.py** | 專家子 Agent：合約法遵、財報、ESG、資料分析。 |
| **eval/** | 題集（eval_set.json、eval_set_contract.json）與 run_eval.py；結果寫入 eval/runs/。 |
| **data/** | 預設灌入來源（內含 sample.txt、sample_contract_NDA.txt 範例）。 |
| **docs/** | 競賽對齊、RAG 記憶、Demo 指南、痛點分析、專案檔案結構等；入口 [docs/README.md](docs/README.md)。 |

---

## Eval 與技術驗證

預設題集為**合約／法遵主題**（合約審閱、法條查詢、知識庫列舉與 RAG 問答），與作品定位一致。

```bash
# 預設：合約／法遵題集（eval_set.json）
uv run python eval/run_eval.py

# 合約專用題集（eval_set_contract.json，題數較少）
uv run python eval/run_eval.py --eval-set eval/eval_set_contract.json

# 使用 Groq（需 GROQ_API_KEY）
uv run python eval/run_eval.py --groq
```

輸出：`eval/runs/run_<timestamp>_results.jsonl`、`run_<timestamp>_metrics.json`（routing 準確率、Tool 成功率、Latency）。Streamlit 側欄「Eval 批次結果」可選 run 檢視各題與指標。

---

## 進階設定（.env）

- **合約審閱**：`RAG_USE_HISTORY_FOR_QUERY=1`、`RAG_MAX_HISTORY_TURNS=12`；可選 `RAG_MULTI_QUERY=1`、`RAG_USE_BM25=1`（Hybrid 檢索）。
- **檢索**：`RAG_INTERNAL_TOP_K`、`RAG_RERANK_TOP_N`、`RAG_MMR_LAMBDA`、`RAG_MIN_SCORE` 等見 `.env.example`。
- **Eval**：`EVAL_LOG_ENABLED=1`、`EVAL_LOG_PATH`、`EVAL_RUNS_DIR`；使用 Groq 時請以指令列 `--groq` 傳入，勿在 .env 設 `EVAL_USE_GROQ=1`（否則 Streamlit 也會改用 Groq）。

---

## 授權

本專案採用 **MIT License**，詳見 [LICENSE](LICENSE)。

---

# English

## Autonomous Contract Risk Assessment Agent System

> Complete a first-pass contract review in **minutes**: automatically flag risk clauses, suggest amendments, and cite legal provisions—with optional scope-limited search (this conversation’s uploads only) for efficiency and traceability.

This project is an entry for the **2026 Smart Innovation Awards (AI Application)**. It combines **RAG and a multi-tool agent** for contract risk analysis, judicial law lookup (e.g. Taiwan’s Judicial Yuan), knowledge-base Q&A, and Eval-based validation. The UI is a Streamlit multi-turn chat that supports uploading contracts (.txt / .md / .pdf / .docx) and one-click review or natural-language questions.

---

## Quick Start

**1. Environment**

- Copy `.env.example` to `.env` and set **PINECONE_API_KEY**, **PINECONE_INDEX**, and **GOOGLE_API_KEY** (required).
- For contract + law lookup, set **TAVILY_API_KEY**; see `.env.example` for the rest.

**2. Dependencies and ingest**

```bash
# Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# Put contracts or documents in data/, ensure Pinecone index exists, then run ingest
uv run rag_ingest.py
```

**3. Run**

```bash
uv run streamlit run streamlit_app.py
```

In the browser you can: expand “Upload and ingest documents for this conversation” to upload and ingest, or ask questions over already-ingested content. The sidebar **“Contract review prompts”** has “One-click review (knowledge base only)” and “One-click review (with law lookup)”; or type: “請審閱這份合約的風險條款” / “合約風險評估並查相關法條”.

---

## Technical highlights

| Area | Description |
|------|-------------|
| **Positioning** | Single conversational entry point for contract review, law lookup, knowledge-base Q&A, and charts; intent-based routing to the right tool or expert. |
| **RAG** | LangGraph (retrieve → generate), dual prompt (investigator packages context → judge assesses risk), optional multi-query retrieval, **Hybrid (vector + BM25)**, MMR / LLM rerank. |
| **Contract + law** | **contract_risk_with_law_search**: RAG fetches contract → extract law references → Tavily for Judicial Yuan / web → integrated risk assessment and law highlights → AI self-check → disclaimer. |
| **Observability** | Eval sets (`eval/eval_set.json`, `eval/eval_set_contract.json`), `run_eval.py` outputs routing accuracy, tool success rate, latency; Streamlit shows Eval run log and batch results. |

**Stack**: Google Gemini (LLM + embedding), Pinecone, LangGraph, Streamlit; optional Tavily, Firecrawl, ECharts, Groq (Eval).

---

## How to try / Demo

1. Ensure `.env` is set and the sidebar option “Strict: answer only from knowledge base” is **unchecked** (so contract tools are used).
2. If you ingested data: ask “列出目前知識庫有哪些文件” to list sources.
3. Click sidebar “One-click review (knowledge base only)” or ask “請審閱這份合約的風險條款” → view risk clauses and “View retrieved chunks”.
4. With TAVILY_API_KEY: click “One-click review (with law lookup)” or ask “合約風險評估並查相關法條” → view risk + law highlights + disclaimer.

Full steps and checklist: **[docs/Demo_操作指南.md](docs/Demo_操作指南.md)**.

---

## Project structure and docs

| Path | Description |
|------|-------------|
| **streamlit_app.py** | Streamlit app (multi-chat, upload/ingest, Q&A, Eval view). |
| **agent_router.py** | Main agent: tool routing (RAG, contract/law, experts, charts, web). |
| **rag_graph.py** | RAG core: retrieval, Hybrid, dual prompt, generate; `retrieve_only` for experts. |
| **rag_common.py** | Shared: chunk, embed, Pinecone/Gemini init, BM25 corpus and RRF merge. |
| **expert_agents.py** | Expert agents: contract compliance, financial, ESG, data analysis. |
| **eval/** | Eval sets and run_eval.py; results under eval/runs/. |
| **data/** | Default ingest source (includes sample.txt, sample_contract_NDA.txt). |
| **docs/** | Competition alignment, RAG memory, Demo guide, etc.; entry [docs/README.md](docs/README.md). |

---

## Eval and validation

The default Eval set is **contract/compliance** (contract review, law lookup, list sources, RAG Q&A).

```bash
# Default: contract/compliance set (eval_set.json)
uv run python eval/run_eval.py

# Contract-only set (eval_set_contract.json)
uv run python eval/run_eval.py --eval-set eval/eval_set_contract.json

# Use Groq (requires GROQ_API_KEY)
uv run python eval/run_eval.py --groq
```

Outputs: `eval/runs/run_<timestamp>_results.jsonl`, `run_<timestamp>_metrics.json` (routing accuracy, tool success rate, latency). In Streamlit sidebar, open “Eval batch results” and pick a run to inspect.

---

## Advanced settings (.env)

- **Contract review**: `RAG_USE_HISTORY_FOR_QUERY=1`, `RAG_MAX_HISTORY_TURNS=12`; optional `RAG_MULTI_QUERY=1`, `RAG_USE_BM25=1` (Hybrid).
- **Retrieval**: `RAG_INTERNAL_TOP_K`, `RAG_RERANK_TOP_N`, `RAG_MMR_LAMBDA`, `RAG_MIN_SCORE`; see `.env.example`.
- **Eval**: `EVAL_LOG_ENABLED=1`, `EVAL_LOG_PATH`, `EVAL_RUNS_DIR`; use `--groq` on the command line for Groq, do not set `EVAL_USE_GROQ=1` in .env (or Streamlit will use Groq too).

---

## License

**MIT License**; see [LICENSE](LICENSE).
