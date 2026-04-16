<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { useConversationStore } from "@/stores/conversation";

const conversation = useConversationStore();
const router = useRouter();

const editingId = ref<string | null>(null);
const draftTitle = ref("");

watch(editingId, async (id) => {
  if (!id) {
    return;
  }
  draftTitle.value = conversation.conversations[id]?.title ?? "";
  await nextTick();
  const el = document.querySelector(".conv-panel .conv-input-rename") as HTMLInputElement | null;
  el?.focus();
  el?.select();
});

function selectConv(id: string) {
  conversation.setActiveConversation(id);
  if (router.currentRoute.value.path !== "/chat") {
    void router.push("/chat");
  }
}

function startRename(id: string, e: Event) {
  e.stopPropagation();
  editingId.value = id;
}

function commitRename() {
  if (!editingId.value) {
    return;
  }
  conversation.renameConversation(editingId.value, draftTitle.value);
  editingId.value = null;
}

function cancelRename() {
  editingId.value = null;
}

function onRenameKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    e.preventDefault();
    commitRename();
  }
  if (e.key === "Escape") {
    e.preventDefault();
    cancelRename();
  }
}

function confirmDelete(id: string, title: string, e: Event) {
  e.stopPropagation();
  const ok = window.confirm(`Delete "${title}" from recent?`);
  if (!ok) {
    return;
  }
  conversation.deleteConversation(id);
  if (editingId.value === id) {
    editingId.value = null;
  }
}

function formatUpdatedAt(value: number): string {
  return new Intl.DateTimeFormat("zh-TW", {
    month: "numeric",
    day: "numeric",
  }).format(value);
}
</script>

<template>
  <section class="conv-panel" aria-label="Recent documents">
    <ul class="conv-list">
      <li
        v-for="id in conversation.conversationIdsByRecency"
        :key="id"
        class="conv-item-wrap"
      >
        <div v-if="editingId === id" class="conv-edit" @click.stop>
          <input
            v-model="draftTitle"
            type="text"
            class="conv-input conv-input-rename"
            maxlength="120"
            aria-label="Rename recent document"
            @keydown="onRenameKeydown"
            @blur="commitRename"
          >
        </div>
        <div
          v-else
          class="conv-row"
          :class="{ active: conversation.activeConversationId === id }"
          role="button"
          tabindex="0"
          @click="selectConv(id)"
          @keydown.enter.prevent="selectConv(id)"
          @keydown.space.prevent="selectConv(id)"
        >
          <div class="doc-icon" aria-hidden="true">▥</div>
          <div class="conv-main">
            <span class="conv-title">{{ conversation.conversations[id]?.title || "新對話" }}</span>
            <span class="conv-meta">{{ formatUpdatedAt(conversation.conversations[id]?.updatedAt ?? Date.now()) }}</span>
          </div>
          <div class="conv-actions">
            <button
              type="button"
              class="icon-btn"
              title="Rename"
              aria-label="Rename"
              @click="startRename(id, $event)"
            >
              ✎
            </button>
            <button
              type="button"
              class="icon-btn danger"
              title="Delete"
              aria-label="Delete"
              @click="confirmDelete(id, conversation.conversations[id]?.title ?? '', $event)"
            >
              ×
            </button>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.conv-panel {
  min-height: 0;
}

.conv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: min(26vh, 220px);
  overflow-y: auto;
}

.conv-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 12px;
  border-radius: 0.95rem;
  border: 1px solid rgba(89, 170, 255, 0.18);
  cursor: pointer;
  color: rgba(220, 232, 245, 0.92);
  background: rgba(255, 255, 255, 0.03);
}

.conv-row.active {
  background: rgba(17, 107, 214, 0.24);
  border-color: rgba(90, 171, 255, 0.3);
}

.conv-row:hover {
  background: rgba(255, 255, 255, 0.06);
}

.conv-row:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 2px;
}

.doc-icon {
  display: grid;
  place-items: center;
  width: 1.8rem;
  height: 1.8rem;
  border-radius: 0.55rem;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.9rem;
}

.conv-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: white;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-meta {
  font-size: 0.72rem;
  color: rgba(220, 232, 245, 0.54);
}

.conv-actions {
  display: flex;
  gap: 2px;
}

.icon-btn {
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: none;
  border-radius: 0.55rem;
  background: transparent;
  color: rgba(220, 232, 245, 0.5);
  cursor: pointer;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

.icon-btn.danger:hover {
  color: #ff9f9f;
}

.conv-edit {
  padding: 4px 0;
}

.conv-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 0.8rem;
  border: 1px solid rgba(120, 177, 240, 0.28);
  background: rgba(255, 255, 255, 0.08);
  color: white;
  font: inherit;
}

.conv-input:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 2px;
}
</style>
