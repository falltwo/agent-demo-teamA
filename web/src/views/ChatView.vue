<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import ChatAssistantMessage from "@/components/chat/ChatAssistantMessage.vue";
import ChatRetrievalSettingsModal from "@/components/chat/ChatRetrievalSettingsModal.vue";
import ApiErrorBlock from "@/components/ui/ApiErrorBlock.vue";
import { ApiError } from "@/api/client";
import { postChat } from "@/api/chat";
import { pushToast } from "@/state/toast";
import { syncRagScopeFromSourcesForChat } from "@/utils/syncRagScopeFromSources";
import type { ChatRequest } from "@/types/api";
import { useConversationStore } from "@/stores/conversation";
import { useSettingsStore } from "@/stores/settings";
import { isAssistantMessage } from "@/types/conversation";
import { conversationToChatHistory } from "@/utils/chatHistory";

const conversation = useConversationStore();
const settings = useSettingsStore();

const input = ref("");
const sending = ref(false);
const chatError = ref<unknown>(null);

const listEl = ref<HTMLElement | null>(null);
const stickToBottom = ref(true);

const settingsOpen = ref(false);

/** 首次提示：每次重新整理頁面都會再顯示；「知道了」僅隱藏本次工作階段 */
const showRetrievalHint = ref(true);

function dismissRetrievalHint() {
  showRetrievalHint.value = false;
}

/** 進入對話／切換對話時依 sources 同步 rag scope */
const scopeSyncState = ref<"loading" | "has" | "none" | "error">("loading");

watch(
  () => conversation.activeConversationId,
  async (id) => {
    scopeSyncState.value = "loading";
    const r = await syncRagScopeFromSourcesForChat(id, { showLoading: false });
    if (!r.ok) {
      scopeSyncState.value = "error";
      return;
    }
    scopeSyncState.value = r.hasUploads ? "has" : "none";
  },
  { immediate: true },
);

function onListScroll() {
  const el = listEl.value;
  if (!el) {
    return;
  }
  const threshold = 80;
  stickToBottom.value =
    el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

function scrollToBottom() {
  const el = listEl.value;
  if (!el) {
    return;
  }
  el.scrollTop = el.scrollHeight;
}

watch(
  () => conversation.activeConversation?.messages.length,
  async () => {
    await nextTick();
    if (stickToBottom.value) {
      scrollToBottom();
    }
  },
);

watch(
  () => conversation.activeConversationId,
  async () => {
    stickToBottom.value = true;
    await nextTick();
    scrollToBottom();
  },
);

watch(sending, async (v) => {
  if (!v) {
    await nextTick();
    if (stickToBottom.value) {
      scrollToBottom();
    }
  }
});

function onTextareaKeydown(e: KeyboardEvent) {
  if (e.key !== "Enter" || e.shiftKey) {
    return;
  }
  e.preventDefault();
  void sendMessage();
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

  const priorWeb = conversation.pendingWebVsRagOriginalQuestion;
  const priorChart = conversation.pendingChartConfirmationQuestion;
  const priorHistory = conversationToChatHistory(
    conversation.conversations[convId].messages,
  );
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
  } catch (e) {
    conversation.pendingWebVsRagOriginalQuestion = priorWeb;
    conversation.pendingChartConfirmationQuestion = priorChart;
    conversation.removeLastMessage(convId);
    chatError.value = e;
    if (e instanceof ApiError) {
      pushToast({
        variant: "error",
        code: e.code,
        message: e.message,
        details: e.details,
      });
    } else {
      pushToast({
        variant: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <div class="chat-page">
    <!-- 頁面標題：僅供螢幕閱讀器／文件大綱，不佔版面高度 -->
    <h1 class="sr-only">
      對話
    </h1>

    <ChatRetrievalSettingsModal
      v-model:open="settingsOpen"
      :scope-sync-state="scopeSyncState"
    />

    <div class="chat-main">
        <h2 id="chat-log-heading" class="sr-only">
          對話訊息
        </h2>
        <div
          v-if="!conversation.activeConversation?.messages.length"
          class="ds-callout empty-hint"
          role="status"
        >
          <p class="empty-hint-title">
            建議流程（約三步）
          </p>
          <ol>
            <li>到「上傳檔案」頁選好檔案（.pdf／.docx／.txt／.md）</li>
            <li>按「灌入」，完成後助理才能引用內容</li>
            <li>回到這裡輸入問題；需要時點「檢索設定」調整參考範圍</li>
          </ol>
        </div>

        <div
          ref="listEl"
          class="message-list"
          role="log"
          aria-live="polite"
          aria-relevant="additions"
          aria-labelledby="chat-log-heading"
          @scroll="onListScroll"
        >
          <template
            v-for="(msg, idx) in conversation.activeConversation?.messages"
            :key="idx"
          >
            <div
              v-if="msg.role === 'user'"
              class="msg-row user"
            >
              <div class="user-bubble">{{ msg.content }}</div>
            </div>
            <div
              v-else-if="isAssistantMessage(msg)"
              class="msg-row assistant"
            >
              <ChatAssistantMessage :message="msg" />
            </div>
          </template>
          <div
            v-if="sending"
            class="skeleton-reply"
            aria-hidden="true"
          >
            <div class="ds-skeleton ds-skeleton-block reply-skel" />
            <p class="typing">正在生成回覆…</p>
          </div>
        </div>

        <ApiErrorBlock
          v-if="chatError"
          :error="chatError"
          title="對話請求失敗"
        />

        <div class="composer">
          <div
            v-if="showRetrievalHint"
            class="composer-first-tip"
            role="status"
          >
            <p class="composer-first-tip-text">
              首次使用？點<strong>檢索設定</strong>可調整助理參考幾段內容、是否只依本對話檔案。
            </p>
            <button
              type="button"
              class="composer-first-tip-dismiss ds-btn-secondary-inline"
              @click="dismissRetrievalHint"
            >
              知道了
            </button>
          </div>

          <div class="composer-row">
            <button
              type="button"
              class="composer-settings"
              aria-label="檢索設定：調整回答參考範圍與是否只依本對話檔案"
              title="檢索設定"
              aria-haspopup="dialog"
              :aria-expanded="settingsOpen"
              :disabled="sending"
              @click="settingsOpen = true"
            >
              <svg
                class="composer-settings-ico"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                aria-hidden="true"
                focusable="false"
              >
                <path
                  fill="currentColor"
                  d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.31-.07.63-.07.94 0 .31.02.63.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"
                />
              </svg>
              <span class="composer-settings-text">檢索設定</span>
            </button>
            <textarea
              id="chat-input"
              v-model="input"
              class="ds-textarea composer-input"
              rows="3"
              name="message"
              aria-label="輸入訊息"
              placeholder="輸入問題…"
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
              送出
            </button>
          </div>
        </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 0;
}

.empty-hint-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-body-size);
  font-weight: 600;
  color: var(--color-text-primary);
}

.message-list {
  flex: 1 1 auto;
  min-height: 240px;
  max-height: min(68vh, 780px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-3);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-inset);
}

.msg-row {
  margin-bottom: var(--space-4);
}

.msg-row:last-child {
  margin-bottom: 0;
}

.msg-row.user {
  display: flex;
  justify-content: flex-end;
}

.user-bubble {
  max-width: min(100%, var(--prose-measure));
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  white-space: pre-wrap;
  font-size: var(--text-body-size);
  line-height: var(--text-body-leading);
  color: var(--color-text-primary);
}

.skeleton-reply {
  padding: var(--space-2) 0;
}

.reply-skel {
  max-width: 85%;
  height: 72px;
}

.typing {
  margin: var(--space-2) 0 0;
  font-size: var(--text-caption-size);
  color: var(--color-text-muted);
}

.composer {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-subtle);
}

.composer-first-tip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3);
  margin-bottom: var(--space-1);
  color: var(--color-text-secondary);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

.composer-first-tip-text {
  margin: 0;
  flex: 1 1 200px;
  min-width: 0;
  font-size: var(--text-body-size);
  line-height: var(--text-body-leading);
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--color-text-primary);
}

.ds-btn-secondary-inline {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-caption-size);
  font-weight: 600;
  font-family: var(--font-body);
  color: var(--color-text-primary);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
  flex-shrink: 0;
}

.ds-btn-secondary-inline:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.composer-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: end;
  gap: var(--space-3);
  width: 100%;
}

.composer-input {
  flex: 1;
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  resize: vertical;
  min-height: 5rem;
}

.composer-send {
  flex-shrink: 0;
  min-height: 2.75rem;
  padding-left: var(--space-4);
  padding-right: var(--space-4);
}

.composer-settings {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  padding: 0 var(--space-2);
  color: var(--color-text-secondary);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  cursor: pointer;
  box-sizing: border-box;
  font-family: var(--font-body);
  font-size: var(--text-caption-size);
  font-weight: 600;
}

.composer-settings-text {
  white-space: nowrap;
}

.composer-settings:hover:not(:disabled) {
  background: var(--color-accent-muted);
  color: var(--color-text-primary);
}

.composer-settings:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.composer-settings:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.composer-settings-ico {
  display: block;
}

@media (max-width: 900px) {
  .message-list {
    max-height: min(52dvh, 560px);
  }

  .composer-row {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto;
  }

  .composer-input {
    grid-column: 1 / -1;
    grid-row: 1;
  }

  .composer-settings {
    grid-column: 1;
    grid-row: 2;
    justify-self: start;
    max-width: 100%;
  }

  .composer-send {
    grid-column: 2;
    grid-row: 2;
    justify-self: stretch;
    width: 100%;
  }
}
</style>
