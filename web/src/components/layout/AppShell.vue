<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { getSources } from "@/api/sources";
import ConversationListPanel from "@/components/layout/ConversationListPanel.vue";
import { IS_ADMIN_TARGET } from "@/config/runtime";
import { useConversationStore } from "@/stores/conversation";
import { parseSourceRow } from "@/utils/sourceEntry";

type LibraryDoc = {
  id: string;
  title: string;
  chatId: string | null;
};

const router = useRouter();
const conversation = useConversationStore();

const isFrontWorkspace = computed(() => !IS_ADMIN_TARGET);
const uploadDocs = ref<LibraryDoc[]>([]);

const documentCount = computed(() => uploadDocs.value.length);
const pendingCount = computed(
  () =>
    conversation.conversationIdsByRecency.filter((id) => {
      const entry = conversation.conversations[id];
      return entry && entry.messages.length === 0;
    }).length,
);

function createConversation() {
  conversation.addConversation();
  void router.push("/chat");
}

function displaySourceName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const leaf = normalized.split("/").pop() || path;
  return leaf.replace(/#chunk\d+$/i, "");
}

function uniqueDocs(rows: { source: string; chat_id: string | null }[]): LibraryDoc[] {
  const seen = new Set<string>();
  return rows
    .map((row, index) => ({
      id: `${row.chat_id ?? "global"}-${index}`,
      title: displaySourceName(row.source),
      chatId: row.chat_id,
    }))
    .filter((item) => {
      const key = `${item.title}-${item.chatId ?? "none"}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

function fallbackDocs(): LibraryDoc[] {
  return conversation.conversationIdsByRecency.slice(0, 8).map((id) => ({
    id,
    title: conversation.conversations[id]?.title || "未命名文件",
    chatId: id,
  }));
}

async function loadLibrary() {
  try {
    const response = await getSources(null, { showLoading: false });
    const rows = Array.isArray(response.entries) ? response.entries : [];
    const docs = uniqueDocs(
      rows.map((row) => parseSourceRow(row as Record<string, unknown>)),
    );
    uploadDocs.value = docs.length > 0 ? docs : fallbackDocs();
  } catch {
    uploadDocs.value = fallbackDocs();
  }
}

function openLibraryDoc(doc: LibraryDoc) {
  if (doc.chatId && conversation.conversations[doc.chatId]) {
    conversation.setActiveConversation(doc.chatId);
  } else {
    const id = conversation.addConversation();
    conversation.renameConversation(id, doc.title);
  }
  void router.push("/chat");
}

onMounted(() => {
  void loadLibrary();
});
</script>

<template>
  <div class="shell" :class="{ 'shell--admin': IS_ADMIN_TARGET }">
    <aside class="sidebar" :aria-label="isFrontWorkspace ? '文件側欄' : '管理側欄'">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">L</div>
        <div class="brand-copy">
          <p class="brand-title">合約法遵助理</p>
          <p class="brand-subtitle">
            {{ isFrontWorkspace ? "Contract review workspace" : "System operations" }}
          </p>
        </div>
      </div>

      <div v-if="isFrontWorkspace" class="workspace-tools">
        <label class="search-box" for="workspace-search">
          <span class="search-icon" aria-hidden="true">⌕</span>
          <input
            id="workspace-search"
            type="search"
            class="search-input"
            placeholder="Search documents..."
          >
        </label>
        <div class="action-row">
          <button type="button" class="action-btn action-btn--primary" @click="createConversation">
            <span aria-hidden="true">＋</span>
            <span>New</span>
          </button>
          <RouterLink class="action-btn action-btn--ghost" to="/upload">Upload</RouterLink>
        </div>
      </div>

      <div v-if="isFrontWorkspace" class="sidebar-section">
        <div class="section-head">
          <p class="section-label">Recent</p>
        </div>
        <ConversationListPanel />
      </div>

      <div class="sidebar-section">
        <div class="section-head">
          <p class="section-label">Documents</p>
        </div>
        <div class="library-list">
          <button
            v-for="doc in uploadDocs"
            :key="doc.id"
            type="button"
            class="tree-doc"
            :class="{ 'tree-doc--active': doc.chatId != null && conversation.activeConversationId === doc.chatId }"
            @click="openLibraryDoc(doc)"
          >
            <span class="tree-doc__icon" aria-hidden="true">▥</span>
            <span class="tree-doc__title">{{ doc.title }}</span>
          </button>
          <p v-if="uploadDocs.length === 0" class="tree-empty">No uploaded documents</p>
        </div>
      </div>

      <footer v-if="isFrontWorkspace" class="sidebar-footer">
        <p>{{ documentCount }} documents</p>
        <p>{{ pendingCount }} pending review</p>
      </footer>
    </aside>

    <main class="main">
      <div class="main-inner">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 242px minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
  background:
    radial-gradient(circle at top left, rgba(36, 112, 189, 0.22), transparent 24%),
    linear-gradient(180deg, #0c1b2f 0%, #09131f 100%);
}

.shell--admin {
  background: var(--color-bg-app);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 16px 14px;
  background: linear-gradient(180deg, #0a2743 0%, #091a2c 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  color: #dce8f5;
}

.shell--admin .sidebar {
  background: linear-gradient(180deg, #121821 0%, #0c1017 100%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.7rem;
  background: linear-gradient(160deg, #2490ff 0%, #1663c7 100%);
  color: white;
  font-size: 1.1rem;
  font-weight: 800;
  box-shadow: 0 10px 24px rgba(18, 109, 209, 0.35);
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  margin: 0;
  font-size: 1.55rem;
  line-height: 1;
  color: white;
  font-family: var(--font-body);
  font-weight: 800;
}

.brand-subtitle {
  margin: 4px 0 0;
  color: rgba(220, 232, 245, 0.72);
  font-size: 0.76rem;
}

.workspace-tools {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  min-height: 36px;
  border-radius: 0.85rem;
  background: rgba(125, 165, 209, 0.1);
  border: 1px solid rgba(189, 214, 242, 0.14);
}

.search-icon {
  color: rgba(220, 232, 245, 0.72);
}

.search-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: white;
  font: inherit;
}

.search-input::placeholder {
  color: rgba(220, 232, 245, 0.5);
}

.action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-2);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 36px;
  border-radius: 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  text-decoration: none;
  font-weight: 700;
  font-size: var(--text-body-sm-size);
  cursor: pointer;
}

.action-btn--primary {
  background: linear-gradient(180deg, #1f8bff 0%, #1367d0 100%);
  color: white;
  box-shadow: 0 16px 28px rgba(20, 96, 190, 0.32);
}

.action-btn--ghost {
  color: #dce8f5;
  background: rgba(255, 255, 255, 0.06);
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-height: 0;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-label {
  margin: 0;
  color: rgba(220, 232, 245, 0.7);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.library-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tree-doc {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 0.7rem;
  background: transparent;
  color: #dce8f5;
  text-align: left;
  cursor: pointer;
}

.tree-doc:hover {
  background: rgba(255, 255, 255, 0.06);
}

.tree-doc--active {
  background: rgba(17, 107, 214, 0.24);
  outline: 1px solid rgba(90, 171, 255, 0.26);
}

.tree-doc__icon {
  flex: 0 0 auto;
}

.tree-doc__title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tree-empty {
  margin: 0;
  padding: 6px 10px;
  color: rgba(220, 232, 245, 0.48);
  font-size: 0.8rem;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: var(--space-3);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(220, 232, 245, 0.54);
  font-size: 0.8rem;
}

.sidebar-footer p {
  margin: 0;
}

.main {
  min-width: 0;
  min-height: 100vh;
  padding: 8px 12px;
  background: #edf2f7;
}

.shell--admin .main {
  background: #0f1218;
}

.main-inner {
  width: 100%;
  min-height: calc(100vh - 16px);
}

@media (max-width: 1100px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .main {
    padding: var(--space-3);
  }
}
</style>
