import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from google import genai
from streamlit_echarts import st_echarts
from chat_service import answer_with_rag_and_log
from eval_log import is_enabled as eval_log_enabled, load_runs
from llm_client import get_chat_client_and_model
from rag_common import get_clients_and_index
from ingest_service import ingest_uploaded_files
from sources_registry import load_registry, save_registry, list_sources


def _inject_custom_css() -> None:
    """注入自訂 CSS：從 assets/custom.css 讀取，若無則不注入。"""
    css_path = Path(__file__).resolve().parent / "assets" / "custom.css"
    if css_path.is_file():
        st.markdown(
            f"<style>\n{css_path.read_text(encoding='utf-8')}\n</style>",
            unsafe_allow_html=True,
        )


def _split_answer_and_refs(content: str) -> tuple[str, str | None]:
    """若回答內含「**參考連結：**」區塊，拆成主文與參考連結兩部分，否則回傳 (content, None)。"""
    if not content or "**參考連結：**" not in content:
        return (content or "", None)
    parts = content.split("**參考連結：**", 1)
    main_part = (parts[0] or "").strip()
    refs_part = (parts[1] or "").strip() if len(parts) > 1 else None
    return (main_part, refs_part if refs_part else None)


def _render_sources_expander(sources: list[str]) -> None:
    """將來源／參考連結以折疊區塊顯示。"""
    if not sources:
        return
    with st.expander("參考連結", expanded=False):
        for s in sources:
            st.markdown(f"- {s}")


def _render_chart_chunks(extra_or_msg: dict[str, Any] | None) -> None:
    """若有圖表依據的檢索片段，顯示可展開區塊「圖表依據的檢索片段（點擊展開）」。"""
    if not extra_or_msg:
        return
    chart_chunks = extra_or_msg.get("chart_chunks")
    if not chart_chunks or not isinstance(chart_chunks, list):
        return
    with st.expander("圖表依據的檢索片段（點擊展開）"):
        for c in chart_chunks:
            if isinstance(c, dict) and c.get("tag") is not None:
                st.markdown(f"**{c.get('tag', '')}**\n\n{c.get('text', '')}")
            else:
                st.markdown(str(c))


@st.cache_resource
def _cached_get_clients_and_index():
    """Streamlit 專用：快取 get_clients_and_index，避免每次重連。"""
    return get_clients_and_index()


def _render_eval_view() -> None:
    """Eval 運行記錄頁：讀取 log、篩選、表格、展開看詳情。"""
    st.markdown('<p class="eval-dashboard-head">線上驗證</p>', unsafe_allow_html=True)
    st.subheader("Eval 運行記錄")
    st.caption("啟用後，每次問答會記錄 Tool、延遲與內容，供檢視與除錯。")
    if not eval_log_enabled():
        st.info("請在 .env 設定 `EVAL_LOG_ENABLED=1` 並重新執行問答，才會寫入記錄。日誌路徑：`EVAL_LOG_PATH`（預設 eval_runs.jsonl）。")
    runs = load_runs(limit=500)
    if not runs:
        st.caption("尚無記錄。")
        return
    # 篩選區：用 container + 小標包起來，層級更清楚
    with st.container():
        st.caption("**篩選**")
        col1, col2 = st.columns(2)
        with col1:
            tool_filter = st.selectbox(
                "Tool",
                options=["全部"] + sorted({r.get("tool_name") or "" for r in runs if r.get("tool_name")}),
                key="eval_tool_filter",
            )
        with col2:
            keyword = st.text_input("問題關鍵字", key="eval_keyword", placeholder="留空不篩選")
        if tool_filter and tool_filter != "全部":
            runs = [r for r in runs if r.get("tool_name") == tool_filter]
        if keyword.strip():
            runs = [r for r in runs if keyword.strip() in (r.get("question") or "")]
        st.caption(f"共 {len(runs)} 筆（顯示最近 500 筆）")
    for i, r in enumerate(runs):
        ts = r.get("timestamp", "")[:19] if r.get("timestamp") else ""
        tool_name = r.get("tool_name") or ""
        lat = r.get("latency_sec")
        lat_str = f"{lat:.1f}s" if isinstance(lat, (int, float)) else ""
        q = (r.get("question") or "")[:80] + ("…" if len(r.get("question") or "") > 80 else "")
        with st.expander(f"{ts} | {tool_name} | {lat_str} | {q}"):
            st.markdown("**問題**")
            st.text(r.get("question") or "")
            st.markdown("**回答**")
            st.text_area("", value=(r.get("answer") or "")[:3000], height=120, disabled=True, key=f"eval_ans_{i}")
            st.caption(f"Tool: {tool_name} | 延遲: {lat_str} | top_k: {r.get('top_k')} | 來源數: {r.get('source_count')}")


def _render_eval_batch_view() -> None:
    """Eval 批次結果頁：讀取 eval/runs/*.jsonl，選 run 後顯示每題問題與回答。"""
    st.markdown('<p class="eval-dashboard-head">批次評測</p>', unsafe_allow_html=True)
    st.subheader("Eval 批次結果")
    st.caption("以題集執行 `uv run python eval/run_eval.py` 後，在此選 Run 檢視 Routing／Tool／延遲指標與逐題結果。")
    runs_dir = Path(os.getenv("EVAL_RUNS_DIR", "eval/runs"))
    if not runs_dir.is_dir():
        st.info(f"尚無批次結果目錄：`{runs_dir}`。請先執行 `uv run python eval/run_eval.py`（可加 `--groq`）產生結果。")
        return

    results_files = sorted(runs_dir.glob("run_*_results.jsonl"), key=lambda p: p.name, reverse=True)
    if not results_files:
        st.info(f"目錄 `{runs_dir}` 中沒有找到 run_*_results.jsonl 檔案。")
        return

    run_options = [f.stem.replace("_results", "") for f in results_files]
    selected = st.selectbox("選擇一次 Eval Run", options=run_options, key="eval_batch_run")
    if not selected:
        return

    results_path = runs_dir / f"{selected}_results.jsonl"
    metrics_path = runs_dir / f"{selected}_metrics.json"
    if not results_path.exists():
        st.warning(f"找不到 {results_path}")
        return

    with st.spinner("載入 Run…"):
        results: list[dict[str, Any]] = []
        with results_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        metrics: dict[str, Any] = {}
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    if metrics:
        st.markdown('<p class="eval-dashboard-head">核心指標</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("總題數", metrics.get("total", 0))
        with c2:
            acc = metrics.get("routing_accuracy")
            n = metrics.get("routing_accuracy_n", 0)
            st.metric("Routing 準確率", f"{acc}%" if acc is not None else "—", f"n={n}")
        with c3:
            rate = metrics.get("tool_success_rate")
            st.metric("Tool 成功率", f"{rate}%" if rate is not None else "—")
        with c4:
            p95 = metrics.get("latency_p95_sec")
            st.metric("Latency P95", f"{p95}s" if p95 is not None else "—")
        with st.expander("📌 指標說明"):
            st.markdown("""
            - **Routing 準確率**：意圖是否被正確路由到預期 Tool（有標註 expected_tool 的題目才計入）。
            - **Tool 成功率**：整次 Run 中無 exception、成功回覆的題目比例。
            - **Latency P95**：單次問答延遲的 95 分位（秒），可代表「多數請求」的響應時間；與 AI 輕量化、作品完整性驗證相關。
            """)

    st.divider()
    st.caption("各題結果（可展開看問題與回答；✓/✗ 表示該題是否成功，括號內為該題延遲）")
    for idx, r in enumerate(results):
        rid = r.get("id", "")
        q = (r.get("question") or "")[:60] + ("…" if len(r.get("question") or "") > 60 else "")
        pred = r.get("predicted_tool") or "—"
        exp = r.get("expected_tool") or "—"
        ok = "✓" if r.get("success") else "✗"
        lat = r.get("latency_sec")
        lat_str = f"{lat}s" if isinstance(lat, (int, float)) else "—"
        label = f"#{rid} {ok} {pred} ({lat_str}) | {q}"
        with st.expander(label):
            st.markdown("**問題**")
            st.text(r.get("question") or "")
            st.markdown("**預期 Tool / 實際 Tool**")
            st.text(f"{exp} → {pred}")
            st.markdown("**回答**")
            answer_text = r.get("answer")
            if answer_text is None or (isinstance(answer_text, str) and not answer_text.strip()):
                answer_text = "(此 run 未記錄答案內容，僅有 answer_len)"
                if r.get("answer_len") is not None:
                    answer_text += f" 字數：{r.get('answer_len')}"
            st.text_area("", value=answer_text, height=180, disabled=True, key=f"batch_ans_{selected}_{idx}")
            if r.get("error"):
                st.caption(f"錯誤：{str(r.get('error'))[:500]}")


def main() -> None:
    st.set_page_config(
        page_title="合約／法遵審閱助理｜RAG 多工具 Agent",
        page_icon="⚖️",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _inject_custom_css()

    try:
        chat_client, embed_client, index, index_dim, _cached_llm, embed_model, index_name = _cached_get_clients_and_index()
        # 強制載入專案根目錄 .env，確保側欄與請求使用正確的 GEMINI_CHAT_MODEL
        load_dotenv(Path(__file__).resolve().parent / ".env")
        _, llm_model = get_chat_client_and_model()
    except Exception as e:
        st.error(f"初始化失敗：{e}")
        st.stop()

    # 初始化多對話狀態
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
    if "active_conv_id" not in st.session_state or st.session_state.active_conv_id not in st.session_state.conversations:
        first_id = "chat-1"
        st.session_state.conversations[first_id] = {"title": "新對話", "messages": []}
        st.session_state.active_conv_id = first_id

    conversations = st.session_state.conversations
    active_conv_id = st.session_state.active_conv_id
    current_conv = conversations[active_conv_id]

    with st.sidebar:
        st.markdown(
            '<p class="sidebar-brand">合約／法遵助理</p>'
            '<p class="sidebar-section-title">導覽</p>',
            unsafe_allow_html=True,
        )
        view = st.radio("畫面", ["對話", "Eval 運行記錄", "Eval 批次結果"], key="nav_view")
        st.markdown('<p class="sidebar-section-title">連線與檢索</p>', unsafe_allow_html=True)
        st.subheader("設定")
        st.caption(f"Pinecone index：`{index_name}`（dim={index_dim}）")
        st.caption(f"Chat model：`{llm_model}`")
        st.caption(f"Embed model：`{embed_model}`")
        top_k = st.slider("TOP_K", min_value=1, max_value=20, value=int(os.getenv("TOP_K", "5")), step=1)
        strict_mode = st.checkbox("嚴格只根據知識庫回答", value=False, help="勾選時一律只依知識庫回答、不經合約／法條工具。合約審閱建議不勾選以啟用合約專家與法條查詢。")
        # 若此對話有上傳過檔案，預設勾選「只搜尋此對話上傳的檔案」，避免參考連結／檢索片段參雜其他來源
        has_uploads_here = len(list_sources(chat_id=active_conv_id)) > 0
        filter_by_chat = st.checkbox(
            "只搜尋此對話上傳的檔案",
            value=has_uploads_here,
            help="勾選時，參考連結與檢索片段僅來自本對話上傳的檔案；不勾選則搜尋整個知識庫。",
        )
        rag_scope_chat_id = active_conv_id if filter_by_chat else None
        with st.expander("合約審閱提示", expanded=True):
            st.caption("上傳合約後可問：「請審閱這份合約的風險條款」「合約風險評估並查相關法條」，或使用下方一鍵審閱。")
            if st.button("一鍵審閱（僅知識庫）", use_container_width=True, key="one_click_knowledge"):
                st.session_state["one_click_review_question"] = "請根據目前已灌入的文件做合約條款分析與風險標註，僅依文件內容、不查外部法條。"
                st.session_state["one_click_review_chat_id"] = active_conv_id
                st.rerun()
            if st.button("一鍵審閱（含法條查詢）", use_container_width=True, key="one_click_law"):
                st.session_state["one_click_review_question"] = "請審閱這份合約的風險條款並查相關法條。"
                st.session_state["one_click_review_chat_id"] = active_conv_id
                st.rerun()

        st.divider()
        st.markdown('<p class="sidebar-section-title">對話與維護</p>', unsafe_allow_html=True)
        st.subheader("對話")
        conv_ids = list(conversations.keys())
        current_index = conv_ids.index(active_conv_id)
        selected_id = st.radio(
            "選擇對話",
            options=conv_ids,
            index=current_index,
            format_func=lambda cid: conversations[cid].get("title") or "未命名對話",
        )
        if selected_id != active_conv_id:
            st.session_state.active_conv_id = selected_id
            st.rerun()

        if st.button("＋ 新對話", use_container_width=True):
            new_id = f"chat-{len(conversations) + 1}"
            conversations[new_id] = {"title": "新對話", "messages": []}
            st.session_state.active_conv_id = new_id
            st.rerun()

        if st.button("清除此對話", use_container_width=True):
            # 刪除目前對話欄位本身
            if len(conversations) > 1:
                conversations.pop(active_conv_id, None)
                # 切到剩餘的第一個對話
                st.session_state.active_conv_id = next(iter(conversations.keys()))
            else:
                # 若只剩一個，則重置成新的空對話
                conversations[active_conv_id] = {"title": "新對話", "messages": []}
            st.rerun()

        st.divider()
        st.markdown(
            '<div class="sidebar-danger-block">'
            '<p class="sidebar-danger-label">危險操作</p>'
            '<p class="sidebar-danger-hint">將清空向量庫與來源註冊表，無法復原。</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("清空資料庫", type="secondary", use_container_width=True, key="btn_clear_db"):
            try:
                index.delete(delete_all=True)
                save_registry([])
                st.success("已清空向量庫與來源註冊表。")
            except Exception as e:
                st.error(f"清空失敗：{e}")
            st.rerun()

    # 主標題；Eval 頁改為情境化小標，對話頁保留完整副標
    st.title("合約／法遵審閱助理")
    if view == "對話":
        st.markdown(
            '<div class="app-hero-pills" aria-label="功能摘要">'
            "<span>RAG</span><span>合約審閱</span><span>法條</span><span>圖表</span><span>多輪</span>"
            "</div>"
            '<p class="app-tagline">上傳灌入後提問，或由側欄一鍵審閱；支援檢索片段與參考連結對照。</p>',
            unsafe_allow_html=True,
        )
    elif view == "Eval 運行記錄":
        st.caption("線上單次問答之執行紀錄")
    elif view == "Eval 批次結果":
        st.caption("批次題集之指標與逐題結果")

    if view == "Eval 運行記錄":
        _render_eval_view()
        return
    if view == "Eval 批次結果":
        _render_eval_batch_view()
        return

    if "messages" not in current_conv:
        current_conv["messages"] = []

    # 空對話時顯示引導文案（強調合約審閱流程）
    if not current_conv["messages"]:
        st.info(
            "**開始方式（三步）**  \n"
            "1. 展開下方「為此對話上傳並灌入文件」，上傳 .pdf／.docx／.txt／.md  \n"
            "2. 按「灌入到向量庫」  \n"
            "3. 於側欄使用「一鍵審閱」或在下方輸入問題（例：審閱合約風險條款）"
        )
        st.markdown("")

    # 整理給模型用的對話歷史（只保留 role + content），傳入 RAG/專家以記得上下文
    history_for_model: list[dict[str, Any]] = []
    for i, msg in enumerate(current_conv["messages"]):
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            history_for_model.append({"role": role, "content": content})
        with st.chat_message(msg["role"]):
            main_content, refs_content = _split_answer_and_refs(msg.get("content") or "")
            st.markdown(main_content or "(空)")
            if refs_content:
                with st.expander("參考連結", expanded=False):
                    st.markdown(refs_content)
            if msg.get("chart_image_base64"):
                try:
                    st.image(BytesIO(base64.b64decode(msg["chart_image_base64"])), use_container_width=True)
                except Exception:
                    pass
            elif msg.get("chart_option"):
                st_echarts(options=msg["chart_option"], height="400px")
            _render_chart_chunks(msg)
            if msg.get("sources"):
                _render_sources_expander(msg["sources"])
            _is_contract_tool = msg.get("tool_name") in ("contract_risk_agent", "contract_risk_with_law_search")
            if _is_contract_tool and msg.get("chunks"):
                st.caption("以下為合約風險分析，可展開檢索片段對照原文。")
            if msg.get("chunks"):
                with st.expander("查看檢索片段", expanded=_is_contract_tool):
                    for c in msg["chunks"]:
                        st.markdown(f"**{c['tag']}**\n\n{c['text']}")

    with st.expander("為此對話上傳並灌入文件"):
        st.caption("支援 `.txt` / `.md` / `.pdf` / `.docx`。上傳後按「灌入到向量庫」，即可立刻用來問答。")
        uploads = st.file_uploader(
            "選擇檔案",
            type=["txt", "md", "pdf", "docx"],
            accept_multiple_files=True,
            key=f"uploads-{active_conv_id}",
        )
        if st.button(
            "灌入到向量庫",
            use_container_width=True,
            disabled=not uploads,
            key=f"ingest-{active_conv_id}",
        ):
            try:
                with st.spinner("向量化並寫入 Pinecone 中…（檔案越大越久）"):
                    n = ingest_uploaded_files(
                        embed_client=embed_client,
                        index=index,
                        index_dim=index_dim,
                        embed_model=embed_model,
                        uploaded_files=list(uploads or []),
                        chat_id=active_conv_id,
                    )
                if n == 0:
                    st.warning("沒有可灌入的內容（請確認檔案不是空的）。")
                else:
                    st.success(f"已灌入 {n} 個 chunks，可直接在下方問答。")
            except Exception as e:
                st.error(f"灌入失敗：{e}")

    question = st.chat_input("輸入你的問題…")
    # 一鍵審閱：側欄按鈕觸發後，以預設問題當作本輪使用者輸入
    if question is None and st.session_state.get("one_click_review_chat_id") == active_conv_id and st.session_state.get("one_click_review_question"):
        question = st.session_state.pop("one_click_review_question", "")
        st.session_state.pop("one_click_review_chat_id", None)
    if not question:
        return

    current_conv["messages"].append({"role": "user", "content": question})
    # 第一則使用者問題時，將對話標題設為問題前 20 字
    if current_conv.get("title") == "新對話" and len(current_conv["messages"]) == 1:
        q = (question or "").strip()
        current_conv["title"] = (q[:20] + ("…" if len(q) > 20 else "")) or "新對話"
    with st.chat_message("user"):
        st.markdown(question)

    # 若上一輪已問「需要幫我生成圖表嗎？」，本輪使用者說要 → 直接產圖
    pending_chart = current_conv.pop("pending_chart_question", None)
    if pending_chart is not None:
        with st.chat_message("assistant"):
            with st.spinner("正在生成圖表…"):
                answer, sources, chunks, tool_name, extra = answer_with_rag_and_log(
                    question=question,
                    top_k=top_k,
                    history=history_for_model,
                    strict=strict_mode,
                    chat_id=active_conv_id,
                    rag_scope_chat_id=rag_scope_chat_id,
                    chart_confirmation_question=pending_chart,
                    chart_confirmation_reply=question,
                )
            main_content, refs_content = _split_answer_and_refs(answer or "")
            st.markdown(main_content or "(空回覆)")
            if refs_content:
                with st.expander("參考連結", expanded=False):
                    st.markdown(refs_content)
            if extra and extra.get("chart_image_base64"):
                try:
                    st.image(BytesIO(base64.b64decode(extra["chart_image_base64"])), use_container_width=True)
                except Exception:
                    pass
            elif extra and extra.get("chart_option"):
                st_echarts(options=extra["chart_option"], height="400px")
            _render_chart_chunks(extra)
            if sources:
                _render_sources_expander(sources)
            if chunks:
                with st.expander("查看檢索片段"):
                    for c in chunks:
                        st.markdown(f"**{c['tag']}**\n\n{c['text']}")
        current_conv["messages"].append({
            "role": "assistant",
            "content": answer or "(空回覆)",
            "sources": sources,
            "chunks": chunks,
            "tool_name": tool_name,
            "chart_option": (extra or {}).get("chart_option"),
            "chart_image_base64": (extra or {}).get("chart_image_base64"),
            "chart_chunks": (extra or {}).get("chart_chunks"),
            "chart_sources": (extra or {}).get("chart_sources"),
        })
        return

    # 若上一輪是「知識庫 vs 網路」澄清，本輪使用使用者的回覆決定執行哪個 tool
    pending = current_conv.pop("pending_web_vs_rag_question", None)
    if pending is not None:
        with st.chat_message("assistant"):
            with st.spinner("依您的選擇執行中…"):
                answer, sources, chunks, tool_name, extra = answer_with_rag_and_log(
                    question=question,
                    top_k=top_k,
                    history=history_for_model,
                    strict=strict_mode,
                    chat_id=active_conv_id,
                    rag_scope_chat_id=rag_scope_chat_id,
                    original_question=pending,
                    clarification_reply=question,
                )
            main_content, refs_content = _split_answer_and_refs(answer or "")
            st.markdown(main_content or "(空回覆)")
            if refs_content:
                with st.expander("參考連結", expanded=False):
                    st.markdown(refs_content)
            if extra and extra.get("chart_image_base64"):
                try:
                    st.image(BytesIO(base64.b64decode(extra["chart_image_base64"])), use_container_width=True)
                except Exception:
                    pass
            elif extra and extra.get("chart_option"):
                st_echarts(options=extra["chart_option"], height="400px")
            _render_chart_chunks(extra)
            if sources:
                _render_sources_expander(sources)
            if chunks:
                with st.expander("查看檢索片段"):
                    for c in chunks:
                        st.markdown(f"**{c['tag']}**\n\n{c['text']}")
        current_conv["messages"].append({
            "role": "assistant",
            "content": answer or "(空回覆)",
            "sources": sources,
            "chunks": chunks,
            "tool_name": tool_name,
            "chart_option": (extra or {}).get("chart_option"),
            "chart_image_base64": (extra or {}).get("chart_image_base64"),
            "chart_chunks": (extra or {}).get("chart_chunks"),
            "chart_sources": (extra or {}).get("chart_sources"),
        })
        return

    with st.chat_message("assistant"):
        with st.spinner("檢索並生成答案中…"):
            answer, sources, chunks, tool_name, extra = answer_with_rag_and_log(
                question=question,
                top_k=top_k,
                history=history_for_model,
                strict=strict_mode,
                chat_id=active_conv_id,
                rag_scope_chat_id=rag_scope_chat_id,
            )
        main_content, refs_content = _split_answer_and_refs(answer or "")
        st.markdown(main_content or "(空回覆)")
        if refs_content:
            with st.expander("參考連結", expanded=False):
                st.markdown(refs_content)
        if extra and extra.get("chart_image_base64"):
            try:
                st.image(BytesIO(base64.b64decode(extra["chart_image_base64"])), use_container_width=True)
            except Exception:
                pass
        elif extra and extra.get("chart_option"):
            st_echarts(options=extra["chart_option"], height="400px")
        _render_chart_chunks(extra)
        if sources:
            _render_sources_expander(sources)
        _contract_tool = tool_name in ("contract_risk_agent", "contract_risk_with_law_search")
        if _contract_tool and chunks:
            st.caption("以下為合約風險分析，可展開檢索片段對照原文。")
        if chunks:
            with st.expander("查看檢索片段", expanded=_contract_tool):
                for c in chunks:
                    st.markdown(f"**{c['tag']}**\n\n{c['text']}")

    # 若本輪是「意圖模糊」追問，下一輪要帶 original_question + clarification_reply
    if tool_name == "ask_web_vs_rag":
        current_conv["pending_web_vs_rag_question"] = question
    # 若本輪是「分析並詢問是否產圖」，下一輪使用者說「要」時會走 chart_confirmation 產圖
    if tool_name == "analyze_and_chart" and extra and extra.get("asked_chart_confirmation"):
        current_conv["pending_chart_question"] = extra.get("chart_query") or question

    current_conv["messages"].append({
        "role": "assistant",
        "content": answer or "(空回覆)",
        "sources": sources,
        "chunks": chunks,
        "tool_name": tool_name,
        "chart_option": (extra or {}).get("chart_option"),
        "chart_image_base64": (extra or {}).get("chart_image_base64"),
        "chart_chunks": (extra or {}).get("chart_chunks"),
        "chart_sources": (extra or {}).get("chart_sources"),
    })


if __name__ == "__main__":
    main()

