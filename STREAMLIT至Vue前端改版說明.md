# 從 `streamlit_app.py` 到 Vue 前端：改版說明

本文整理本分支相對於「純 Streamlit 單體應用」的架構與檔案變更，方便推上 GitHub 前對齊認知與分工。

---

## 1. 改版目標（一句話）

在**保留既有 RAG／Agent 核心邏輯**的前提下，抽出 **HTTP API**，並以 **Vue 3 + Vite** 提供可部署的網頁前端；Streamlit 仍可與後端**雙軌並存**（見 `backend/main.py` 註解）。

---

## 2. 原架構：`streamlit_app.py`

| 面向 | 說明 |
|------|------|
| 角色 | 單一 Python 程式內含 UI + 呼叫 `answer_with_rag_and_log` + 上傳灌入 |
| 對話 | `st.session_state` 多對話、標題、訊息歷史 |
| 側欄 | TOP_K、嚴格模式、`rag_scope_chat_id`（只搜尋本對話上傳檔）、一鍵審閱、清空 DB 等 |
| 畫面 | **對話**、**Eval 運行記錄**、**Eval 批次結果**（讀 log／`eval/runs`） |
| 呈現 | Markdown、參考連結拆段、`streamlit_echarts` 圖表、合約工具檢索片段展開 |

---

## 3. 現況：前後端分離

```
瀏覽器  →  Vue（web/） axios  →  FastAPI（backend/）  →  chat_service / ingest_service  →  既有 Agent／RAG
         ↑
    可選：Streamlit 仍直接 import 同一套 Python 服務層
```

- **前端**：`web/`（Vue 3、Vue Router、Pinia、ECharts、marked、axios）。
- **後端**：`backend/`（FastAPI、Pydantic、CORS、統一例外處理）。
- **契約**：`contracts/openapi.json` 由後端匯出，前端以 `openapi-typescript` 產生 `web/src/types/openapi.generated.ts`。

---

## 4. 後端（`backend/`）重點

| 模組 | 用途 |
|------|------|
| `backend/main.py` | 建立 FastAPI app、掛 CORS、註冊路由 |
| `backend/api/routes/chat.py` | `POST /api/v1/chat`，對應 `chat_service.answer_with_rag_and_log` |
| `backend/api/routes/ingest.py` | `POST /api/v1/ingest/upload`（multipart）、`GET /api/v1/sources` |
| `backend/api/routes/eval.py` | Eval **唯讀**：config、線上 runs、批次 run 列表與詳情 |
| `backend/api/routes/health.py` | 健康檢查 |
| `backend/services/chat_adapter.py` | 將 HTTP body 對應到 `answer_with_rag_and_log`，並回傳 `next_original_question_for_clarification`／`next_chart_confirmation_question`（對齊 Streamlit 的 pending 流程） |
| `backend/services/ingest_adapter.py` | 上傳灌入與 `sources_registry` 對齊 Streamlit 行為 |

---

## 5. 共用 Python 服務層（與 Streamlit 共用）

| 檔案 | 說明 |
|------|------|
| `chat_service.py` | `answer_with_rag` / `answer_with_rag_and_log`：薄封裝 `agent_router.route_and_answer`，可選寫入 Eval 日誌 |
| `ingest_service.py` | 上傳位元組 → chunk／embed／Pinecone／registry／BM25，與 Streamlit「灌入到向量庫」一致 |

**重點**：Agent、RAG、`rag_graph.py` 等核心不必為了前端重寫一份；後端 adapter 只負責 HTTP 與型別。

---

## 6. Vue 前端（`web/`）功能對照

| 路由 | 對應 Streamlit／功能 |
|------|----------------------|
| `/chat` | 主對話：送訊、`postChat`、歷史、澄清／圖表確認參數、助理訊息（Markdown、圖表、參考連結、chunks） |
| `/upload` | 「為此對話上傳並灌入」→ `POST /api/v1/ingest/upload`，並可同步「只搜尋本對話上傳」範圍 |
| `/sources` | 檢視已註冊來源（可篩對話），對應 `GET /api/v1/sources` |

**UI／狀態**

- **版面**：`AppShell`（側欄品牌、**對話列表** `ConversationListPanel`、主要導覽）。
- **狀態**：Pinia（`stores/conversation.ts`、`settings.ts`、持久化相關）。
- **聊天元件**：`ChatAssistantMessage.vue`（含 ECharts 掛載、高風險比對 modal 等）、檢索設定 modal、錯誤與 Toast。
- **API**：`src/api/chat.ts`、`ingest.ts`、`sources.ts` + `client.ts`（axios、loading、錯誤型別）。

**與 Streamlit 的差異（組長需知）**

- **Eval 儀表板**：Streamlit 仍有「Eval 運行記錄」「Eval 批次結果」完整 UI；後端已提供 `/api/v1/eval/*`，但 **Vue 目前未做獨立 Eval 頁面**（型別已在 OpenAPI／generated ts 中，日後可加）。
- **清空向量庫**：Streamlit 側欄有按鈕；若網頁版也要同等能力，需再決定是否暴露 API 或僅限管理員操作（目前文件未列為一般使用者功能）。

---

## 7. API 契約與腳本

| 項目 | 說明 |
|------|------|
| `contracts/openapi.json` | OpenAPI 3.1 單一真實來源 |
| `scripts/export_openapi.py` | 從 `create_app()` 匯出 JSON |
| `web/package.json` | `openapi:export` / `openapi:gen` / `openapi:sync`、`contract:check`（型別與 `vue-tsc`） |

---

## 8. 測試與 CI（`.github/workflows/ci.yml`）

- **pytest**：`tests/test_chat_api.py`、`test_ingest_api.py`、`test_eval_api.py` 等（Chat 會 mock `route_and_answer`，不打真實 LLM／向量庫）。
- **Web job**：`npm ci`（`web/`）、`npm run contract:check`、`npm run build`。
- **Playwright**：`web/e2e/health-chat-mock.spec.ts`（健康與 chat mock 流程）。

---

## 9. 依賴與啟動（給部署／Code Review）

- **Python**：`pyproject.toml` 已加入 `fastapi`、`uvicorn`、`pydantic-settings` 等；既有 `streamlit` 仍保留。
- **後端**（專案根目錄）：  
  `uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- **Streamlit**（可選雙軌）：  
  `uv run streamlit run streamlit_app.py`
- **前端**：`cd web && npm ci && npm run dev`（開發）；`npm run build` 產出靜態檔。

環境變數請對齊 `.env.example`（本分支有修改時需一併說明部署方）。

---

## 9-1. Vue 前端開啟方式 

### A. 開發模式（本機看畫面）

1. 開一個終端機，先啟動後端（專案根目錄）  
   `uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. 再開第二個終端機，啟動 Vue（`web/`）  
   `cd web`  
   `npm ci`（首次或套件有更新時）  
   `npm run dev`
3. 瀏覽器打開 Vite 顯示的網址（通常是 `http://localhost:5173`）。

### B. 建置後預覽（模擬上線前）

1. 在 `web/` 執行：  
   `npm run build`
2. 接著執行：  
   `npm run preview`
3. 用終端機顯示的 preview 網址開啟頁面。

### C. 常見問題（快速排查）

- 頁面打得開但 API 失敗：先確認後端 `8000` 是否有啟動。
- 型別或契約錯誤：在 `web/` 先跑 `npm run openapi:sync`，再 `npm run contract:check`。
- 如果只要展示舊版 UI：可改跑 `uv run streamlit run streamlit_app.py`。

---

## 10. 本分支「新增／變動」目錄／檔案速查（推 GitHub 時）

| 類型 | 路徑 |
|------|------|
| FastAPI | `backend/**` |
| 前端 | `web/**`（含 `package-lock.json`） |
| 契約 | `contracts/openapi.json` |
| 腳本 | `scripts/export_openapi.py` |
| 共用服務 | `chat_service.py`、`ingest_service.py`（與 Streamlit 共用） |
| 測試 | `tests/test_chat_api.py`、`test_ingest_api.py`、`test_eval_api.py` 等 |
| CI | `.github/workflows/ci.yml` |
| 其他 | `git status` 中尚有 `rag_graph.py`、`streamlit_app.py`、`assets/custom.css`、`pyproject.toml`、`uv.lock`、`.env.example` 等變更，請以實際 diff 為準 |

---

## 11. 簡報用三句話

1. **核心智慧**仍在 Python Agent／RAG；我們只加了 **FastAPI 邊界**與 **Vue 客戶端**。  
2. **對話、上傳灌入、來源列表**在網頁上已可走完；**Eval 看板**仍以 Streamlit 為主、API 已備好擴充。  
3. **OpenAPI + CI** 確保前後端契約與建置可重現，適合團隊在 GitHub 上協作與接續迭代。

---

*文件產生目的：推分支至 GitHub 前，向組長說明「從 Streamlit 到 Vue」的範圍與責任切分；細節請以實際 commit／PR diff 為準。*
