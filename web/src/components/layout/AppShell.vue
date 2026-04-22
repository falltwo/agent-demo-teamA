<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { postIngestUpload } from "@/api/ingest";
import { deleteSource, getSources } from "@/api/sources";
import { IS_ADMIN_TARGET } from "@/config/runtime";
import { pushToast } from "@/state/toast";
import { useConversationStore } from "@/stores/conversation";
import { isAssistantMessage } from "@/types/conversation";
import { parseSourceRow } from "@/utils/sourceEntry";
import { syncRagScopeFromSourcesForChat } from "@/utils/syncRagScopeFromSources";
import EmptyState from "@/components/common/EmptyState.vue";

type LibraryDoc = {
  id: string;
  title: string;
  chatId: string | null;
  source: string | null;
  updatedAt: number;
};

const route = useRoute();
const router = useRouter();
const conversation = useConversationStore();

const libraryQuery = ref("");
const uploadDocs = ref<LibraryDoc[]>([]);
const uploadInput = ref<HTMLInputElement | null>(null);
const uploadBusy = ref(false);
const deletingId = ref<string | null>(null);
const collapsedRecent = ref(false);
const collapsedIndexed = ref(false);

const deleteModalOpen = ref(false);
const itemToDelete = ref<{ id: string, title: string, type: 'chat' | 'doc', doc?: LibraryDoc } | null>(null);

const isFrontWorkspace = computed(() => !IS_ADMIN_TARGET);

const recentDocs = computed<LibraryDoc[]>(() =>
  conversation.conversationIdsByRecency.map((id) => ({
    id,
    title: conversation.conversations[id]?.title?.trim() || "未命名對話",
    chatId: id,
    source: null,
    updatedAt: conversation.conversations[id]?.updatedAt ?? Date.now(),
  })),
);

const filteredRecentDocs = computed(() => recentDocs.value.filter((doc) => matchesQuery(doc.title)));
const filteredIndexedDocs = computed(() =>
  uploadDocs.value.filter((doc) => matchesQuery(`${doc.title} ${doc.source ?? ""}`)),
);
const documentCount = computed(() => uploadDocs.value.length);

function matchesQuery(value: string): boolean {
  const query = libraryQuery.value.trim().toLowerCase();
  if (!query) {
    return true;
  }
  return value.toLowerCase().includes(query);
}

function displaySourceName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const leaf = normalized.split("/").pop() || path;
  return leaf.replace(/#chunk\d+$/i, "");
}

function uniqueDocs(rows: { source: string; chat_id: string | null }[]): LibraryDoc[] {
  const seen = new Set<string>();
  return rows
    .map((row) => ({
      id: `${row.chat_id ?? "global"}-${row.source}`,
      title: displaySourceName(row.source),
      chatId: row.chat_id,
      source: row.source,
      updatedAt: Date.now(),
    }))
    .filter((item) => {
      const key = `${item.source ?? item.title}-${item.chatId ?? "global"}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

function fallbackDocs(): LibraryDoc[] {
  return recentDocs.value.slice(0, 12);
}

function latestRiskTone(chatId: string | null): "high" | "medium" | "low" | "neutral" {
  if (!chatId || !conversation.conversations[chatId]) {
    return "neutral";
  }

  const messages = conversation.conversations[chatId].messages;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (!isAssistantMessage(message)) {
      continue;
    }
    const count = message.chunks?.length ?? 0;
    if (count >= 3) {
      return "high";
    }
    if (count >= 1) {
      return "medium";
    }
    return "low";
  }

  return messages.length > 0 ? "low" : "neutral";
}

function openRecentConversation(chatId: string) {
  conversation.setActiveConversation(chatId);
  void router.push("/chat");
}

function triggerUploadPicker() {
  if (!uploadBusy.value) {
    uploadInput.value?.click();
  }
}

function newConversation() {
  const id = conversation.addConversation();
  void router.push({ path: "/chat", query: { chat: id } });
}

async function onUploadFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const files = input?.files ? Array.from(input.files) : [];
  if (files.length === 0 || uploadBusy.value) {
    return;
  }

  let chatId = conversation.activeConversationId;
  if (!chatId) {
    chatId = conversation.addConversation();
  }

  uploadBusy.value = true;
  try {
    await postIngestUpload(files, chatId, { showLoading: true });
    await syncRagScopeFromSourcesForChat(chatId, { showLoading: false });
    await loadLibrary();
    pushToast({
      variant: "info",
      message: `已上傳 ${files.length} 份文件並完成索引。`,
    });
    conversation.setActiveConversation(chatId);
    void router.push({ path: "/chat", query: { chat: chatId } });
  } catch (error) {
    pushToast({
      variant: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  } finally {
    uploadBusy.value = false;
    if (input) {
      input.value = "";
    }
  }
}

function openIndexedDoc(doc: LibraryDoc) {
  let activeId = conversation.activeConversationId;
  if (doc.chatId && conversation.conversations[doc.chatId]) {
    conversation.setActiveConversation(doc.chatId);
    activeId = doc.chatId;
  } else if (!activeId) {
    activeId = conversation.addConversation();
    conversation.renameConversation(activeId, doc.title);
  }

  const targetChatId = doc.chatId ?? activeId;
  void router.push({
    path: "/chat",
    query: {
      ...(doc.source ? { source: doc.source } : {}),
      ...(targetChatId ? { chat: targetChatId } : {}),
    },
  });
}

function requestDeleteConversation(event: Event, chatId: string, title: string) {
  event.stopPropagation();
  itemToDelete.value = { id: chatId, title, type: 'chat' };
  deleteModalOpen.value = true;
}

function cancelDelete() {
  deleteModalOpen.value = false;
  itemToDelete.value = null;
}

function requestDeleteIndexedDoc(event: Event, doc: LibraryDoc) {
  event.stopPropagation();
  if (deletingId.value) return;
  itemToDelete.value = { id: doc.id, title: doc.title, type: 'doc', doc };
  deleteModalOpen.value = true;
}

async function confirmDelete() {
  if (!itemToDelete.value) return;
  const { id, type, doc } = itemToDelete.value;
  deleteModalOpen.value = false;

  if (type === 'chat') {
    conversation.deleteConversation(id);
  } else if (type === 'doc' && doc) {
    deletingId.value = id;
    try {
      await deleteSource(doc.source ?? doc.title, doc.chatId, { showLoading: true });
      await loadLibrary();
      pushToast({ variant: "info", message: `已從知識庫刪除「${doc.title}」。` });
    } catch (error) {
      pushToast({
        variant: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      deletingId.value = null;
    }
  }
  itemToDelete.value = null;
}

async function loadLibrary() {
  try {
    const response = await getSources(null, { showLoading: false });
    const rows = Array.isArray(response.entries)
      ? response.entries.map((row) => parseSourceRow(row as Record<string, unknown>))
      : [];
    const docs = uniqueDocs(rows);
    uploadDocs.value = docs.length > 0 ? docs : fallbackDocs();
  } catch {
    uploadDocs.value = fallbackDocs();
  }
}

watch(
  () => route.fullPath,
  () => {
    if (isFrontWorkspace.value) {
      void loadLibrary();
    }
  },
);

onMounted(() => {
  if (isFrontWorkspace.value) {
    void loadLibrary();
  }
});
</script>

<template>
  <div class="shell" :class="{ 'shell--admin': IS_ADMIN_TARGET }">
    <header class="topbar">
      <div class="topbar-brand">
        <div class="topbar-mark" aria-hidden="true">[]</div>
        <div class="topbar-copy">
          <p class="topbar-title">合約法遵助理</p>
          <p class="topbar-subtitle">Contract Review Workspace</p>
        </div>
      </div>

      <label v-if="isFrontWorkspace" class="topbar-search" for="global-doc-search">
        <span class="topbar-search__icon" aria-hidden="true">Q</span>
        <input
          id="global-doc-search"
          v-model="libraryQuery"
          type="search"
          class="topbar-search__input"
          placeholder="搜尋檔名、來源或審閱紀錄"
        >
      </label>

      <div v-if="isFrontWorkspace" class="topbar-actions"></div>
    </header>

    <aside class="sidebar" :aria-label="isFrontWorkspace ? '文件區' : '管理區'">
      <template v-if="isFrontWorkspace">
        <input
          ref="uploadInput"
          type="file"
          class="sr-only-upload"
          multiple
          accept=".txt,.md,.pdf,.docx"
          @change="onUploadFileChange"
        >

        <div class="sidebar-title">
          <h2>Documents</h2>
          <button type="button" class="sidebar-title__collapse" aria-label="收合側欄">
            &lt;
          </button>
        </div>

        <label class="sidebar-search" for="sidebar-doc-search">
          <span aria-hidden="true">Q</span>
          <input
            id="sidebar-doc-search"
            v-model="libraryQuery"
            type="search"
            placeholder="Search documents..."
          >
        </label>

        <div class="sidebar-actions">
          <button
            type="button"
            class="sidebar-upload"
            :disabled="uploadBusy"
            @click="triggerUploadPicker"
          >
            {{ uploadBusy ? "上傳中" : "上傳" }}
          </button>
          <button
            type="button"
            class="sidebar-new-chat"
            title="新對話"
            @click="newConversation"
          >
            +
          </button>
        </div>

        <section class="doc-group">
          <button
            type="button"
            class="doc-group__head"
            :aria-expanded="!collapsedRecent"
            @click="collapsedRecent = !collapsedRecent"
          >
            <span class="doc-group__chevron" :class="{ 'doc-group__chevron--collapsed': collapsedRecent }" aria-hidden="true"></span>
            <h3>最近審閱</h3>
          </button>
          <div v-show="!collapsedRecent" class="doc-group__list">
            <div
              v-for="doc in filteredRecentDocs"
              :key="doc.id"
              class="doc-node-wrap"
            >
              <button
                type="button"
                class="doc-node"
                :class="{ 'doc-node--active': conversation.activeConversationId === doc.chatId && route.path === '/chat' }"
                @click="openRecentConversation(doc.chatId || doc.id)"
              >
                <span class="doc-node__icon" aria-hidden="true"></span>
                <span class="doc-node__title">{{ doc.title }}</span>
                <span class="doc-node__dot" :class="`doc-node__dot--${latestRiskTone(doc.chatId)}`"></span>
              </button>
              <button
                type="button"
                class="doc-node__del"
                title="刪除對話"
                @click.stop="requestDeleteConversation($event, doc.chatId || doc.id, doc.title)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
            <div v-if="filteredRecentDocs.length === 0" class="sidebar-empty">
              <EmptyState
                icon='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>'
                title="尚無對話"
                description="點擊右上角的「+」建立新對話"
              />
            </div>
          </div>
        </section>

        <section class="doc-group doc-group--grow">
          <button
            type="button"
            class="doc-group__head"
            :aria-expanded="!collapsedIndexed"
            @click="collapsedIndexed = !collapsedIndexed"
          >
            <span class="doc-group__chevron" :class="{ 'doc-group__chevron--collapsed': collapsedIndexed }" aria-hidden="true"></span>
            <h3>已索引文件</h3>
            <span class="doc-group__count">{{ documentCount }}</span>
          </button>
          <div v-show="!collapsedIndexed" class="doc-group__list">
            <div
              v-for="doc in filteredIndexedDocs"
              :key="doc.id"
              class="doc-node-wrap"
            >
              <button
                type="button"
                class="doc-node"
                :disabled="deletingId === doc.id"
                @click="openIndexedDoc(doc)"
              >
                <span class="doc-node__icon" aria-hidden="true"></span>
                <span class="doc-node__title">{{ deletingId === doc.id ? "刪除中…" : doc.title }}</span>
                <span class="doc-node__dot" :class="`doc-node__dot--${latestRiskTone(doc.chatId)}`"></span>
              </button>
              <button
                type="button"
                class="doc-node__del doc-node__del--danger"
                title="從知識庫刪除文件"
                :disabled="deletingId === doc.id"
                @click.stop="requestDeleteIndexedDoc($event, doc)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
            <div v-if="filteredIndexedDocs.length === 0" class="sidebar-empty">
              <EmptyState
                icon='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>'
                title="尚無文件"
                description="點擊「上傳」按鈕加入文件"
                actionLabel="前往上傳"
                @action="triggerUploadPicker"
              />
            </div>
          </div>
        </section>

        <footer class="sidebar-footer">
          <p class="sidebar-footer__title">Risk Levels</p>
          <div class="risk-legend">
            <span><i class="legend-dot legend-dot--high"></i> High</span>
            <span><i class="legend-dot legend-dot--medium"></i> Medium</span>
            <span><i class="legend-dot legend-dot--low"></i> Low</span>
          </div>
        </footer>
      </template>

      <template v-else>
        <section class="doc-group doc-group--grow">
          <div class="doc-group__head">
            <h3>管理面板</h3>
          </div>
          <div class="doc-group__list">
            <RouterLink to="/admin" class="topbar-link topbar-link--block">前往後台</RouterLink>
          </div>
        </section>
      </template>
    </aside>

    <main class="main">
      <div class="main-inner">
        <slot />
      </div>

      <div v-if="deleteModalOpen" class="modal-overlay" @click="cancelDelete">
        <div class="modal" @click.stop>
          <div class="modal-header">
            <h3>刪除確認</h3>
          </div>
          <div class="modal-body">
            您確定要刪除「<strong>{{ itemToDelete?.title }}</strong>」嗎？此操作無法復原。
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="cancelDelete">取消</button>
            <button type="button" class="btn-danger" @click="confirmDelete">確認刪除</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.sidebar-empty {
  transform: scale(0.85);
  transform-origin: top center;
  margin: -10px 0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal {
  background: white;
  border-radius: 12px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  overflow: hidden;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #0f172a;
}

.modal-body {
  padding: 20px;
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.5;
}

.modal-footer {
  padding: 16px 20px;
  background: #f8fafc;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid #e2e8f0;
}

.btn-cancel {
  padding: 8px 16px;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn-danger {
  padding: 8px 16px;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn-danger:hover {
  background: #b91c1c;
}
.shell {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  grid-template-rows: 68px minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
  background:
    linear-gradient(180deg, #eef3f9 0%, #f5f8fc 100%);
}

.shell--admin {
  background: #111827;
}

.topbar {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  padding: 0 18px;
  background: #10293f;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #f8fbff;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.topbar-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.topbar-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.topbar-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
}

.topbar-subtitle {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(232, 240, 248, 0.7);
}

.topbar-search {
  display: flex;
  align-items: center;
  gap: 10px;
  width: min(540px, 100%);
  min-height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.topbar-search__icon {
  color: rgba(232, 240, 248, 0.72);
  font-size: 0.82rem;
  font-weight: 700;
}

.topbar-search__input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #f8fbff;
  font: inherit;
}

.topbar-search__input::placeholder {
  color: rgba(232, 240, 248, 0.52);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-link,
.topbar-upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 13px;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none;
}

.topbar-link {
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.topbar-link--block {
  width: 100%;
}

.topbar-upload {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: #ffffff;
  color: #10293f;
  cursor: pointer;
}

.topbar-upload:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  padding: 16px 10px 12px;
  background: #ffffff;
  border-right: 1px solid #d7e2ee;
}

.sidebar-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 4px;
}

.sidebar-title h2 {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 800;
  color: #0f172a;
}

.sidebar-title__collapse {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  font-size: 0.92rem;
  cursor: pointer;
}

.sidebar-title__collapse:hover {
  background: #f1f5f9;
}

.sidebar-search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f6f8fb;
  color: #64748b;
}

.sidebar-search input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #0f172a;
  font: inherit;
}

.sidebar-actions {
  display: flex;
  gap: 6px;
}

.sidebar-upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 38px;
  border: 1px solid #d7e2ee;
  border-radius: 10px;
  background: #ffffff;
  color: #10293f;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
}

.sidebar-upload:hover:not(:disabled) {
  background: #f8fbff;
}

.sidebar-upload:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.sidebar-new-chat {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  min-height: 38px;
  flex-shrink: 0;
  border: 1px solid #d7e2ee;
  border-radius: 10px;
  background: #ffffff;
  color: #10293f;
  font-size: 1.25rem;
  font-weight: 400;
  cursor: pointer;
  line-height: 1;
}

.sidebar-new-chat:hover {
  background: #f8fbff;
}

.doc-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.doc-group--grow {
  flex: 1;
}

.doc-group__head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 4px 4px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  text-align: left;
  transition: background-color 120ms ease;
}

.doc-group__head:hover {
  background: #f1f5f9;
}

.doc-group__head h3 {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 800;
  color: #344256;
}

.doc-group__chevron {
  display: inline-block;
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%2394a3b8' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: center;
  transition: transform 180ms ease;
}

.doc-group__chevron--collapsed {
  transform: rotate(-90deg);
}

.doc-group__count {
  margin-left: auto;
  border-radius: 999px;
  background: #edf2f7;
  padding: 2px 7px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #64748b;
}

.doc-group__list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
  overflow: auto;
}

.doc-node {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 10px 11px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: #0f172a;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}

.doc-node:hover {
  background: #f7fbff;
  border-color: #d7e2ee;
}

.doc-node--active {
  background: #10293f;
  border-color: #10293f;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(16, 41, 63, 0.16);
}

.doc-node__icon {
  position: relative;
  display: inline-block;
  width: 14px;
  height: 18px;
  border: 1.5px solid currentColor;
  border-radius: 3px;
  box-sizing: border-box;
  opacity: 0.72;
}

.doc-node__icon::before,
.doc-node__icon::after {
  content: "";
  position: absolute;
  left: 2px;
  right: 2px;
  height: 1.5px;
  background: currentColor;
  border-radius: 999px;
}

.doc-node__icon::before {
  top: 5px;
}

.doc-node__icon::after {
  top: 9px;
}

.doc-node__title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 0.92rem;
  font-weight: 600;
}

.doc-node__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.doc-node__dot--high,
.legend-dot--high {
  background: #ef4444;
}

.doc-node__dot--medium,
.legend-dot--medium {
  background: #eab308;
}

.doc-node__dot--low,
.legend-dot--low {
  background: #22c55e;
}

.doc-node__dot--neutral {
  background: #cbd5e1;
}

.doc-empty {
  margin: 0;
  padding: 8px 4px;
  font-size: 0.86rem;
  color: #94a3b8;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.sidebar-footer__title {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 800;
  color: #64748b;
}

.risk-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 10px;
  font-size: 0.78rem;
  color: #64748b;
}

.risk-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

/* ── 對話 / 文件列表 row wrapper（hover 顯示刪除鈕）── */
.doc-node-wrap {
  position: relative;
  display: flex;
  align-items: stretch;
}

.doc-node-wrap .doc-node {
  flex: 1;
  min-width: 0;
  /* 右側留空間給刪除鈕 */
  padding-right: 32px;
}

.doc-node__del {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  opacity: 1; /* Always visible */
  z-index: 2;
  transition: opacity 120ms ease, background-color 120ms ease, color 120ms ease;
  flex-shrink: 0;
}

.doc-node__del:hover {
  background: #fee2e2;
  color: #dc2626;
}

.doc-node__del--danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.doc-node__del--confirm {
  width: auto;
  padding: 0 8px;
  background: #dc2626;
  color: #ffffff;
  opacity: 1;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 6px;
}

.doc-node__del--confirm:hover {
  background: #b91c1c;
  color: #ffffff;
}

.doc-node-wrap--confirm .doc-node {
  opacity: 0.55;
}

.doc-node__del:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* active 狀態時刪除鈕用淡色 */
.doc-node-wrap:has(.doc-node--active) .doc-node__del {
  color: rgba(255, 255, 255, 0.7);
}

.doc-node-wrap:has(.doc-node--active) .doc-node__del:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.sr-only-upload {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.main {
  min-width: 0;
  min-height: 0;
  padding: 16px;
  background: transparent;
}

.main-inner {
  height: calc(100vh - 68px - 32px);
  min-height: 0;
}

@media (max-width: 1180px) {
  .shell {
    grid-template-columns: 1fr;
    grid-template-rows: 68px auto minmax(0, 1fr);
  }

  .topbar {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px 16px;
  }

  .topbar-search {
    width: 100%;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid #d7e2ee;
  }

  .main-inner {
    height: auto;
  }
}
</style>
