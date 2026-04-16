<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import { ApiError } from "@/api/client";
import { postChat } from "@/api/chat";
import { getSourcePreview, getSources, type SourcePreviewResponse } from "@/api/sources";
import ChatAssistantMessage from "@/components/chat/ChatAssistantMessage.vue";
import ChatRetrievalSettingsModal from "@/components/chat/ChatRetrievalSettingsModal.vue";
import ApiErrorBlock from "@/components/ui/ApiErrorBlock.vue";
import { pushToast } from "@/state/toast";
import { useConversationStore } from "@/stores/conversation";
import { useSettingsStore } from "@/stores/settings";
import type { ChatRequest } from "@/types/api";
import { isAssistantMessage } from "@/types/conversation";
import { conversationToChatHistory } from "@/utils/chatHistory";
import { parseSourceRow } from "@/utils/sourceEntry";
import { syncRagScopeFromSourcesForChat } from "@/utils/syncRagScopeFromSources";

type SourceRow = {
  source: string;
  chunk_count: number;
  chat_id: string | null;
};

const conversation = useConversationStore();
const settings = useSettingsStore();

const input = ref("");
const sending = ref(false);
const chatError = ref<unknown>(null);
const settingsOpen = ref(false);
const showRetrievalHint = ref(true);
const scopeSyncState = ref<"loading" | "has" | "none" | "error">("loading");

const messageListEl = ref<HTMLElement | null>(null);
const stickToBottom = ref(true);

const sourceRows = ref<SourceRow[]>([]);
const preview = ref<SourcePreviewResponse | null>(null);
const previewLoading = ref(false);
const currentPreviewPage = ref(0);

const activeConversation = computed(() => conversation.activeConversation);

const latestAssistant = computed(() => {
  const messages = activeConversation.value?.messages ?? [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (isAssistantMessage(message)) {
      return message;
    }
  }
  return null;
});

const latestContractAssistant = computed(() => {
  const latest = latestAssistant.value;
  if (!latest) {
    return null;
  }
  if (
    latest.tool_name === "contract_risk_agent" ||
    latest.tool_name === "contract_risk_with_law_search"
  ) {
    return latest;
  }
  return null;
});

const currentDocumentTitle = computed(() => {
  if (preview.value?.title) {
    return preview.value.title;
  }
  return activeConversation.value?.title || "新對話";
});

const previewParagraphs = computed(() => {
  const text = preview.value?.content?.trim() ?? "";
  if (!text) {
    return [];
  }
  return text
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 24);
});

const previewPages = computed(() => {
  const pageSize = 5;
  const pages: string[][] = [];
  for (let index = 0; index < previewParagraphs.value.length; index += pageSize) {
    pages.push(previewParagraphs.value.slice(index, index + pageSize));
  }
  return pages;
});

const activePreviewPageParagraphs = computed(() => {
  if (previewPages.value.length === 0) {
    return [];
  }
  const safeIndex = Math.min(currentPreviewPage.value, previewPages.value.length - 1);
  return previewPages.value[safeIndex] ?? [];
});

const pageLabel = computed(() => {
  const total = Math.max(1, previewPages.value.length);
  return `第 ${Math.min(currentPreviewPage.value + 1, total)} / ${total} 頁`;
});

const canGoToPreviousPreviewPage = computed(() => currentPreviewPage.value > 0);
const canGoToNextPreviewPage = computed(
  () => currentPreviewPage.value < previewPages.value.length - 1,
);

const issueCards = computed(() => {
  const chunks = latestContractAssistant.value?.chunks ?? [];
  return chunks.slice(0, 4).map((chunk, index) => ({
    id: `${index}-${chunk.tag || "issue"}`,
    title: chunk.tag || `條款 ${index + 1}`,
    summary: chunk.text || "此條款需要進一步審閱。",
    severity: index === 0 ? "high" : index === 1 ? "medium" : "low",
  }));
});

const categoryRows = computed(() => {
  const chunks = latestContractAssistant.value?.chunks ?? [];
  if (chunks.length === 0) {
    return [
      { name: "責任限制", score: 0, tone: "high" },
      { name: "智慧財產", score: 0, tone: "high" },
      { name: "終止條款", score: 0, tone: "low" },
      { name: "保密義務", score: 0, tone: "low" },
      { name: "付款條件", score: 0, tone: "medium" },
    ];
  }
  const chunkCount = chunks.length;
  return [
    { name: "責任限制", score: Math.min(100, 48 + chunkCount * 8), tone: "high" },
    { name: "智慧財產", score: Math.min(100, 40 + chunkCount * 7), tone: "high" },
    { name: "終止條款", score: Math.min(100, 34 + chunkCount * 6), tone: "low" },
    { name: "保密義務", score: Math.min(100, 36 + chunkCount * 6), tone: "low" },
    { name: "付款條件", score: Math.min(100, 32 + chunkCount * 6), tone: "medium" },
  ];
});

const overallRiskScore = computed(() => {
  const values = categoryRows.value.map((item) => item.score);
  if (values.every((value) => value === 0)) {
    return 0;
  }
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
});

function onMessageListScroll() {
  const el = messageListEl.value;
  if (!el) {
    return;
  }
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
}

function scrollMessagesToBottom() {
  const el = messageListEl.value;
  if (!el) {
    return;
  }
  el.scrollTop = el.scrollHeight;
}

async function loadPreview(chatId: string | null | undefined) {
  preview.value = null;
  previewLoading.value = true;
  currentPreviewPage.value = 0;
  try {
    const entries = await getSources(chatId ?? null, { showLoading: false });
    sourceRows.value = Array.isArray(entries.entries)
      ? entries.entries.map((row) => parseSourceRow(row as Record<string, unknown>))
      : [];

    const firstSource = sourceRows.value[0];
    if (!firstSource?.source) {
      preview.value = null;
      return;
    }

    preview.value = await getSourcePreview(firstSource.source, firstSource.chat_id, {
      showLoading: false,
    });
  } catch {
    sourceRows.value = [];
    preview.value = null;
  } finally {
    previewLoading.value = false;
  }
}

watch(
  () => activeConversation.value?.messages.length,
  async () => {
    await nextTick();
    if (stickToBottom.value) {
      scrollMessagesToBottom();
    }
  },
);

watch(
  () => conversation.activeConversationId,
  async (id) => {
    scopeSyncState.value = "loading";
    const syncResult = await syncRagScopeFromSourcesForChat(id, { showLoading: false }).catch(() => null);
    if (!syncResult) {
      scopeSyncState.value = "error";
    } else if (!syncResult.ok) {
      scopeSyncState.value = "error";
    } else {
      scopeSyncState.value = syncResult.hasUploads ? "has" : "none";
    }

    await loadPreview(id);
    stickToBottom.value = true;
    await nextTick();
    scrollMessagesToBottom();
  },
  { immediate: true },
);

function dismissRetrievalHint() {
  showRetrievalHint.value = false;
}

function goToPreviousPreviewPage() {
  if (!canGoToPreviousPreviewPage.value) {
    return;
  }
  currentPreviewPage.value -= 1;
}

function goToNextPreviewPage() {
  if (!canGoToNextPreviewPage.value) {
    return;
  }
  currentPreviewPage.value += 1;
}

function onTextareaKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    void sendMessage();
  }
}

async function sendMessage() {
  const raw = input.value.trim();
  if (!raw || sending.value) {
    return;
  }

  const convId = conversation.activeConversationId;
  if (!convId || !conversation.conversations[convId]) {
    return;
  }

  const priorHistory = conversationToChatHistory(conversation.conversations[convId].messages);
  const pendingPart = conversation.consumePendingForNextUserMessage(raw);

  conversation.appendUserMessage(convId, raw);
  input.value = "";
  sending.value = true;
  chatError.value = null;

  try {
    const body: ChatRequest = {
      message: raw,
      history: priorHistory,
      top_k: settings.topK,
      strict: settings.strict,
      chat_id: convId,
      rag_scope_chat_id: settings.resolveRagScopeChatId(convId),
      ...pendingPart,
    };
    const res = await postChat(body, { showLoading: true });
    conversation.appendAssistantFromResponse(convId, res);
    conversation.applyChatResponseNextFields(res);
  } catch (error) {
    conversation.removeLastMessage(convId);
    chatError.value = error;
    if (error instanceof ApiError) {
      pushToast({
        variant: "error",
        code: error.code,
        message: error.message,
        details: error.details,
      });
    } else {
      pushToast({
        variant: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  } finally {
    sending.value = false;
  }
}

async function rerunLatestRequest() {
  const messages = activeConversation.value?.messages ?? [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (message.role === "user") {
      input.value = message.content;
      await nextTick();
      void sendMessage();
      return;
    }
  }
}
</script>

<template>
  <div class="workspace-page">
    <ChatRetrievalSettingsModal
      v-model:open="settingsOpen"
      :scope-sync-state="scopeSyncState"
    />

    <section class="review-workspace">
      <div class="document-frame ds-card">
        <header class="doc-toolbar">
          <div class="doc-meta">
            <h1 class="doc-title">{{ currentDocumentTitle }}</h1>
            <span class="doc-status">待審閱</span>
          </div>
          <div class="doc-toolbar__right">
            <button type="button" class="toolbar-pill" @click="settingsOpen = true">分析設定</button>
            <span class="toolbar-pill toolbar-pill--plain">100%</span>
            <div class="preview-pager">
              <button
                type="button"
                class="toolbar-pill toolbar-pill--icon"
                :disabled="!canGoToPreviousPreviewPage"
                aria-label="上一頁"
                @click="goToPreviousPreviewPage"
              >
                ←
              </button>
              <button
                type="button"
                class="toolbar-pill toolbar-pill--icon"
                :disabled="!canGoToNextPreviewPage"
                aria-label="下一頁"
                @click="goToNextPreviewPage"
              >
                →
              </button>
            </div>
            <span class="toolbar-page">{{ pageLabel }}</span>
          </div>
        </header>

        <div class="document-scroll">
          <div v-if="previewLoading" class="document-empty">
            <p class="document-empty__eyebrow">預覽載入中</p>
            <h2>正在整理文件內容</h2>
            <p>系統會優先顯示原始文件的可讀預覽，而不是切片內容。</p>
          </div>

          <div v-else-if="previewParagraphs.length === 0" class="document-empty">
            <p class="document-empty__eyebrow">審閱工作台已就緒</p>
            <h2>目前還沒有合約預覽內容</h2>
            <p>先上傳合約，再輸入想檢查的法律問題。中間區域會顯示文件預覽，不再顯示 chunk 切片。</p>
            <p v-if="sourceRows.length > 0" class="document-empty__hint">
              這個對話目前綁定 {{ sourceRows.length }} 個已索引來源。若不想沿用舊資料，請按左側「New」建立新對話。
            </p>
          </div>

          <article v-else class="document-paper">
            <section
              v-for="(paragraph, index) in activePreviewPageParagraphs"
              :key="`${index}-${paragraph.slice(0, 24)}`"
              class="paper-section"
            >
              <p class="paper-body">{{ paragraph }}</p>
            </section>
          </article>
        </div>

        <div class="workspace-bottom">
          <div class="response-head">
            <p class="response-head__title">分析回覆</p>
            <p class="response-head__desc">你的提問與 AI 回覆會顯示在這裡。</p>
          </div>

          <div class="message-strip" ref="messageListEl" @scroll="onMessageListScroll">
            <template v-for="(msg, idx) in activeConversation?.messages" :key="idx">
              <div v-if="msg.role === 'user'" class="msg-row user">
                <div class="user-bubble">{{ msg.content }}</div>
              </div>
              <div v-else-if="isAssistantMessage(msg)" class="msg-row assistant">
                <ChatAssistantMessage :message="msg" />
              </div>
            </template>

            <p v-if="sending" class="typing">正在分析中...</p>
          </div>

          <ApiErrorBlock
            v-if="chatError"
            :error="chatError"
            title="分析請求失敗"
          />

          <div class="composer">
            <div v-if="showRetrievalHint" class="composer-first-tip" role="status">
              <p class="composer-first-tip-text">
                可以直接指定檢查角度，例如責任上限、智慧財產歸屬、賠償條款、終止條件等。
              </p>
              <button
                type="button"
                class="composer-first-tip-dismiss"
                @click="dismissRetrievalHint"
              >
                關閉
              </button>
            </div>

            <div class="composer-row">
              <textarea
                id="chat-input"
                v-model="input"
                class="ds-textarea composer-input"
                rows="4"
                name="message"
                aria-label="輸入分析問題"
                placeholder="請輸入你要合約法遵助理檢查的條款、比較風險，或提出修訂建議。"
                :disabled="sending"
                autocomplete="off"
                @keydown="onTextareaKeydown"
              />
              <button
                type="button"
                class="ds-btn ds-btn--primary composer-send"
                :disabled="sending || !input.trim()"
                @click="sendMessage()"
              >
                分析
              </button>
            </div>
          </div>
        </div>
      </div>

      <aside class="analysis-rail">
        <div class="analysis-brand ds-card">
          <div class="analysis-brand__icon" aria-hidden="true">✦</div>
          <div>
            <p class="analysis-brand__title">AI 分析</p>
            <p class="analysis-brand__subtitle">由合約法遵助理驅動</p>
          </div>
          <button
            type="button"
            class="rail-refresh"
            @click="rerunLatestRequest"
            :disabled="sending || !(activeConversation?.messages.length)"
          >
            重新分析
          </button>
        </div>

        <div class="analysis-card ds-card">
          <div class="score-head">
            <div>
              <p class="score-label">整體風險分數</p>
              <p class="score-caption">
                {{ latestContractAssistant ? "依最新契約分析結果估算" : "尚未進入契約分析模式" }}
              </p>
            </div>
            <p class="score-value">{{ overallRiskScore }}/100</p>
          </div>
          <div class="score-bar">
            <div class="score-bar__fill" :style="{ width: `${overallRiskScore}%` }" />
          </div>
        </div>

        <div class="analysis-card ds-card">
          <div class="rail-section-head">
            <p class="rail-title">分類風險</p>
          </div>
          <div class="category-list">
            <div
              v-for="item in categoryRows"
              :key="item.name"
              class="category-row"
            >
              <span class="category-name">{{ item.name }}</span>
              <div class="category-track">
                <div class="category-fill" :class="`tone-${item.tone}`" :style="{ width: `${item.score}%` }" />
              </div>
              <span class="category-score">{{ item.score }}</span>
            </div>
          </div>
        </div>

        <div class="analysis-card ds-card">
          <div class="rail-section-head">
            <p class="rail-title">已識別問題</p>
            <span class="rail-count">{{ issueCards.length || "未啟用" }}</span>
          </div>
          <div v-if="issueCards.length === 0" class="issue-empty">
            尚未開始契約分析。請先上傳文件並提出具體的契約風險問題。
          </div>
          <div v-else class="issue-list">
            <article
              v-for="issue in issueCards"
              :key="issue.id"
              class="issue-card"
            >
              <div class="issue-head">
                <h3>{{ issue.title }}</h3>
                <span class="severity" :class="`severity-${issue.severity}`">{{ issue.severity }}</span>
              </div>
              <p class="issue-summary">{{ issue.summary }}</p>
            </article>
          </div>
        </div>

        <div class="analysis-card ds-card">
          <div class="rail-section-head">
            <p class="rail-title">已索引來源</p>
          </div>
          <div v-if="sourceRows.length === 0" class="issue-empty">
            目前沒有可用的來源文件。
          </div>
          <ul v-else class="source-list">
            <li
              v-for="row in sourceRows"
              :key="row.source"
              class="source-item"
            >
              <p class="source-title">{{ row.source }}</p>
              <p class="source-meta">{{ row.chunk_count }} 個 chunk</p>
            </li>
          </ul>
        </div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.workspace-page {
  min-height: 100%;
}

.review-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 348px;
  gap: 16px;
  max-width: none;
  margin: 0;
  min-height: 100%;
  align-items: start;
}

.document-frame {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  height: calc(100vh - 16px);
  overflow: hidden;
  border: 1px solid #dbe6f2;
  background: #eef4fb;
  border-radius: 12px;
  box-shadow: none;
}

.doc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #dbe6f2;
  background: #fffdf9;
  padding: 10px 14px;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.doc-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 800;
  color: #0e2c4a;
}

.doc-status {
  border-radius: 999px;
  background: #ffe6a9;
  padding: 4px 10px;
  font-size: 0.92rem;
  font-weight: 700;
  color: #8a5b00;
}

.doc-toolbar__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar-pill {
  border: 1px solid #d4dfed;
  border-radius: 999px;
  background: #ffffff;
  padding: 8px 12px;
  font-size: 0.98rem;
  font-weight: 700;
  color: #27496a;
}

.toolbar-pill--plain {
  min-width: 56px;
  text-align: center;
}

.toolbar-pill--icon {
  min-width: 38px;
  padding: 8px 0;
}

.toolbar-pill:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.preview-pager {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-page {
  font-size: 0.98rem;
  font-weight: 700;
  color: #64748b;
}

.document-scroll {
  flex: none;
  min-height: 0;
  max-height: none;
  overflow: auto;
  padding: 12px 12px 8px;
}

.document-paper {
  margin: 0 auto;
  max-width: 780px;
  min-height: clamp(520px, 74vh, 940px);
  border: 1px solid #e3ebf4;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: none;
  padding: 26px 28px;
}

.paper-section + .paper-section {
  margin-top: 14px;
}

.paper-body {
  margin: 0;
  white-space: pre-wrap;
  font-size: 1.22rem;
  line-height: 1.72;
  color: #243b53;
}

.document-empty {
  margin: 24px auto 0;
  max-width: 760px;
  border: 1px solid #e3ebf4;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
  padding: 28px 32px;
  text-align: center;
}

.document-empty h2 {
  margin: 8px 0 12px;
  font-size: 3rem;
  color: #102a43;
}

.document-empty p {
  margin: 0;
  font-size: 1.45rem;
  line-height: 1.8;
  color: #486581;
}

.document-empty__eyebrow {
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #486581;
  text-transform: uppercase;
}

.document-empty__hint {
  margin-top: 16px;
  color: #0f5fa8;
  font-weight: 700;
}

.workspace-bottom {
  flex: none;
  border-top: 1px solid #dbe6f2;
  background: #ffffff;
  padding: 12px 14px 14px;
}

.response-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.response-head__title {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  color: #102a43;
}

.response-head__desc {
  margin: 0;
  font-size: 1.05rem;
  color: #829ab1;
}

.message-strip {
  max-height: 132px;
  overflow: auto;
  border: 1px solid #dbe6f2;
  border-radius: 12px;
  background: #f8fbff;
  padding: 10px;
  margin-bottom: 10px;
}

.msg-row + .msg-row {
  margin-top: 10px;
}

.msg-row.user {
  display: flex;
  justify-content: flex-end;
}

.msg-row.assistant {
  display: flex;
  justify-content: flex-start;
}

.user-bubble {
  max-width: min(520px, 100%);
  border-radius: 12px;
  background: linear-gradient(180deg, #2f8eff 0%, #1f74ea 100%);
  padding: 10px 14px;
  font-size: 1.4rem;
  font-weight: 700;
  color: #ffffff;
}

.typing {
  margin: 12px 0 0;
  font-size: 1.35rem;
  color: #486581;
  font-weight: 700;
}

.composer {
  margin-top: 0;
  padding-top: 12px;
  border-top: 1px solid #edf2f7;
}

.composer-first-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  border: 1px solid #c9def7;
  border-radius: 10px;
  background: #edf5ff;
  padding: 10px 12px;
}

.composer-first-tip-text {
  margin: 0;
  font-size: 1.35rem;
  color: #365b84;
}

.composer-first-tip-dismiss {
  border: 0;
  background: transparent;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f74ea;
}

.composer-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 10px;
  align-items: end;
}

.composer-input {
  min-height: 72px;
  resize: vertical;
}

.composer-send {
  min-height: 44px;
}

.analysis-rail {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 0;
  align-self: stretch;
}

.analysis-brand,
.analysis-card {
  border: 1px solid #dbe6f2;
  background: #ffffff;
}

.analysis-brand {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 14px;
  box-shadow: none;
}

.analysis-brand__icon {
  display: grid;
  height: 44px;
  width: 44px;
  place-items: center;
  border-radius: 14px;
  background: linear-gradient(180deg, #184f94 0%, #1f74ea 100%);
  color: #ffffff;
  font-size: 1.8rem;
}

.analysis-brand__title,
.rail-title,
.score-label {
  margin: 0;
  font-size: 1.62rem;
  font-weight: 800;
  color: #102a43;
}

.analysis-brand__subtitle,
.score-caption {
  margin: 4px 0 0;
  font-size: 1.05rem;
  color: #829ab1;
}

.rail-refresh {
  border: 1px solid #d4dfed;
  border-radius: 14px;
  background: #ffffff;
  padding: 9px 14px;
  font-size: 1rem;
  font-weight: 700;
  color: #27496a;
}

.analysis-card {
  padding: 14px;
  box-shadow: none;
}

.score-head,
.rail-section-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.score-value {
  margin: 0;
  font-size: 2.45rem;
  font-weight: 900;
  color: #d59000;
}

.score-bar,
.category-track {
  overflow: hidden;
  border-radius: 999px;
  background: #e8eef6;
}

.score-bar {
  height: 10px;
  margin-top: 14px;
}

.score-bar__fill,
.category-fill {
  height: 100%;
  border-radius: inherit;
}

.score-bar__fill {
  background: linear-gradient(90deg, #1f74ea 0%, #2f8eff 100%);
}

.category-list {
  margin-top: 10px;
}

.category-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 30px;
  gap: 12px;
  align-items: center;
}

.category-row + .category-row {
  margin-top: 8px;
}

.category-name,
.category-score,
.source-meta {
  font-size: 1rem;
  color: #627d98;
}

.tone-high {
  background: #f56565;
}

.tone-medium {
  background: #e6a700;
}

.tone-low {
  background: #31b35c;
}

.issue-empty {
  margin-top: 12px;
  font-size: 1.3rem;
  line-height: 1.7;
  color: #627d98;
}

.issue-list {
  margin-top: 12px;
}

.issue-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fbff;
  padding: 12px;
}

.issue-card + .issue-card {
  margin-top: 10px;
}

.issue-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.issue-head h3,
.source-title {
  margin: 0;
  font-size: 1.32rem;
  font-weight: 800;
  color: #102a43;
  word-break: break-word;
}

.issue-summary {
  margin: 10px 0 0;
  font-size: 1.3rem;
  line-height: 1.7;
  color: #486581;
}

.severity,
.rail-count {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 1.1rem;
  font-weight: 800;
}

.severity-high {
  background: #fde8e8;
  color: #d64545;
}

.severity-medium {
  background: #fff3d6;
  color: #b7791f;
}

.severity-low,
.rail-count {
  background: #edf2f7;
  color: #627d98;
}

.source-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.source-item + .source-item {
  margin-top: 10px;
  padding-top: 12px;
  border-top: 1px solid #edf2f7;
}

.message-strip :deep(.assistant-msg) {
  width: 100%;
}

.message-strip :deep(.bubble),
.message-strip :deep(.bubble--segmented),
.message-strip :deep(.bubble-part),
.message-strip :deep(.risk-clause),
.message-strip :deep(.markdown-body) {
  background: transparent;
  color: #243b53;
  box-shadow: none;
}

.message-strip :deep(.bubble),
.message-strip :deep(.bubble--segmented) {
  border: 1px solid #dbe6f2;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px 14px;
}

.message-strip :deep(pre) {
  overflow: auto;
  border-radius: 12px;
  background: #f4f7fb;
  padding: 12px;
}

@media (max-width: 1200px) {
  .review-workspace {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .analysis-rail {
    order: 2;
    padding-top: 0;
  }
}

@media (max-width: 720px) {
  .doc-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .doc-meta {
    flex-wrap: wrap;
  }

  .response-head {
    flex-direction: column;
    align-items: stretch;
  }

  .composer-row {
    grid-template-columns: 1fr;
  }

  .document-scroll {
    padding: 16px 12px 14px;
  }

  .document-paper,
  .document-empty {
    padding: 22px 18px;
  }

  .workspace-bottom {
    padding: 12px;
  }
}
</style>
