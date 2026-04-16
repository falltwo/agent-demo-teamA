# 更新說明 — 2026-04-17

**commit**: `3c03fb1`  
**分支**: `main`  
**更新者**: falltwo  

---

## 本次更新概要

以後端工程師 + 模型工程師視角對整個專案進行除錯審查，修復了 **正確性、安全性、可觀測性** 三個面向的問題。  
83 個測試全部通過，CI 流程已更新。

---

## Batch 1 — 正確性修復

### B1-1：Ollama URL 重複 `/v1` 問題
**影響檔案**：`llm_client.py`、`rag_common.py`

`rag_common.py` 中有一份 `_normalize_ollama_base_url()` 的複製，與 `llm_client.py` 重複，維護時容易漏改其中一份。  
現在統一邏輯放在 `llm_client.py`，`rag_common.py` 改為 `from llm_client import _normalize_ollama_base_url`。

同時加固邏輯，確保即使 `OLLAMA_BASE_URL` 已含 `/v1` 也不會變成 `/v1/v1`。

> **組員注意**：若你本機 `.env` 設的是 `OLLAMA_BASE_URL=http://host:11434/v1`，現在可以放心，不會再有路徑重複問題。

---

### B1-2：LLM 錯誤不顯示完整 traceback
**影響檔案**：`rag_graph.py`（4 處）

`rag_graph.py` 中 4 個 `except` 區塊的 `logger.warning()` 少了 `exc_info=True`，導致 Ollama 或 Gemini 呼叫失敗時，`journalctl` 只看到錯誤訊息，看不到完整的 stack trace，除錯很困難。

現已全部補上，下次出問題可以直接看到完整 traceback：
```bash
journalctl -u contract-agent-api -f
```

---

### B1-3：`/health` 端點加入依賴探測
**影響檔案**：`backend/api/routes/health.py`、`backend/schemas/health.py`

原本 `/health` 只回傳靜態 `{"status":"ok"}`，即使 Ollama 掛掉也回傳 OK，讓部署腳本誤以為服務正常。

現在會實際探測依賴服務：
```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
# 正常時：
{
  "status": "ok",
  "service": "agent-demo-api",
  "version": "1.0.0",
  "deps": {
    "ollama": "ok",
    "pinecone": "ok"
  }
}
# Ollama 掛掉時：
{
  "status": "degraded",
  "deps": { "ollama": "unreachable", "pinecone": "ok" }
}
```

`status` 值為 `"ok"` 或 `"degraded"`。部署腳本現在接受兩者（避免 Pinecone 短暫波動阻斷部署）。

---

## Batch 2 — 安全性 & 穩定性

### B2-1：Admin 端點加入可選 Bearer Token 認證
**影響檔案**：`backend/config.py`、`backend/api/deps.py`、`backend/api/routes/admin.py`

`/api/v1/admin/*` 端點（服務重啟、Ollama 模型列表等）原本無任何認證保護。  
現在若在 `.env` 設定 `ADMIN_API_TOKEN`，所有 admin 端點都會要求 Bearer token：

```bash
# .env 加入（可選）
ADMIN_API_TOKEN=your-strong-token-here

# 呼叫時
curl -H "Authorization: Bearer your-strong-token-here" http://HOST:8000/api/v1/admin/services
```

> **向後相容**：若 `.env` 未設定 `ADMIN_API_TOKEN`，行為與之前相同（不驗證）。  
> **建議**：生產環境請務必設定。

---

### B2-2：移除版控中的硬編碼 IP
**影響檔案**：`web/.env.frontend`、`web/.env.admin`（已從 git 移除）  
**新增**：`web/.env.frontend.example`、`web/.env.admin.example`

`web/.env.frontend` 和 `web/.env.admin` 含有硬編碼的 Tailscale IP（`100.106.23.28`），已從版控移除。  
這兩個檔案現在：
- 加入 `.gitignore`，不再追蹤
- **由部署腳本自動產生**（會自動抓 Tailscale IP 或 LAN IP）

**本機開發者需要手動建立**：
```bash
# 複製 example 範本並填入你的 API server IP
cp web/.env.frontend.example web/.env.frontend
# 編輯 VITE_API_BASE_URL=http://YOUR_IP:8000
```

---

### B2-3：部署腳本健康檢查加強
**影響檔案**：`scripts/deploy_contract_agent.sh`

- 每次 `curl` 加上 `--max-time 5`，避免 API 無回應時 curl 掛死
- 解析 JSON 回應，`ok` 或 `degraded` 都算成功（Ollama model loading 慢時不再誤報失敗）
- `HEALTH_TIMEOUT_SEC` 預設從 30 秒增加到 60 秒

---

## Batch 3 — 測試 & CI 品質

### B3-1：新增 3 個測試模組
| 測試檔 | 測試項目 |
|--------|---------|
| `tests/test_llm_client.py` | 6 個 URL 正規化 case |
| `tests/test_health_route.py` | 4 個 health 端點 case（mock 依賴） |
| `tests/test_admin_auth.py` | 5 個 admin 認證 case |

全部 83 個測試通過：`uv run pytest --tb=short -q`

---

### B3-2：CI 加入 Gitleaks secret 掃描
**影響檔案**：`.github/workflows/ci.yml`、新增 `.gitleaks.toml`

CI 現在在 pytest/web/playwright 之前先跑 `gitleaks` 掃描，防止 API key 意外推上 GitHub。  
若有真實 secret 被提交，CI 會在 `secret-scan` job 立即失敗，阻止部署。

`.gitleaks.toml` 設定了 `allowlist`，以下為合法的「假值」不會觸發警報：
- `fake`、`test-secret`、`REPLACE_WITH_` 等測試用字串
- `tests/`、`*.example` 路徑下的檔案

---

## 組員需要做的事

### ⚡ 必做（本機開發）
1. **重建前端 env 檔**（因為 `web/.env.frontend` 已從版控移除）：
   ```bash
   cp web/.env.frontend.example web/.env.frontend
   # 編輯填入 API server IP（通常是 http://100.106.23.28:8000）
   cp web/.env.admin.example web/.env.admin
   # 同上
   ```

2. **拉取最新程式碼**：
   ```bash
   git pull origin main
   uv sync --extra dev
   ```

3. **確認測試通過**：
   ```bash
   uv run pytest --tb=short -q
   # 應看到：83 passed
   ```

### 🔧 可選（生產環境加強）
- 在 DGX 的 `~/.env` 加入 `ADMIN_API_TOKEN=<strong-random-token>`，開啟 admin 端點保護
- 可用 `openssl rand -hex 32` 產生一個強 token

---

## CI 流程變化

```
push to main
  ↓
secret-scan（新增）→ 掃描 secret 洩露
  ↓
pytest + web build + playwright（並行）
  ↓
deploy to DGX（全部通過才執行）
```

deploy 現在需要 4 個 job 全過（加了 secret-scan）。

---

## 快速驗證清單

```bash
# 後端測試
uv run pytest --tb=short -q

# API 健康（本地）
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

# Admin 認證（設定 ADMIN_API_TOKEN 後）
curl http://127.0.0.1:8000/api/v1/admin/services        # → 401
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/v1/admin/services  # → 200

# Ollama URL 測試
python3 -c "from llm_client import _normalize_ollama_base_url; print(_normalize_ollama_base_url('http://host:11434/v1'))"
# → http://host:11434/v1（不重複）
```
