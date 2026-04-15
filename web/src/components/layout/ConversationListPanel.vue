<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { useConversationStore } from "@/stores/conversation";

const conversation = useConversationStore();
const router = useRouter();

const editingId = ref<string | null>(null);
const draftTitle = ref("");

watch(editingId, async (id) => {
  if (id) {
    const c = conversation.conversations[id];
    draftTitle.value = c?.title ?? "";
    await nextTick();
    const el = document.querySelector(
      ".conv-panel .conv-input-rename",
    ) as HTMLInputElement | null;
    el?.focus();
    el?.select();
  }
});

function selectConv(id: string) {
  conversation.setActiveConversation(id);
  if (router.currentRoute.value.path !== "/chat") {
    void router.push("/chat");
  }
}

function onNewChat() {
  conversation.addConversation();
  void router.push("/chat");
}

function startRename(id: string, e: Event) {
  e.stopPropagation();
  editingId.value = id;
  const c = conversation.conversations[id];
  draftTitle.value = c?.title ?? "";
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
  const ok = window.confirm(
    `確定要刪除「${title}」嗎？此對話訊息將自本機清除，不會刪除向量庫資料。`,
  );
  if (!ok) {
    return;
  }
  conversation.deleteConversation(id);
  if (editingId.value === id) {
    editingId.value = null;
  }
}
</script>

<template>
  <section
    class="conv-panel"
    aria-label="對話列表"
  >
    <p class="conv-panel-title">
      對話
    </p>
    <button
      type="button"
      class="new-chat-btn"
      @click="onNewChat"
    >
      ＋ 新對話
    </button>
    <ul class="conv-list">
      <li
        v-for="id in conversation.conversationIdsByRecency"
        :key="id"
        class="conv-item-wrap"
      >
        <div
          v-if="editingId === id"
          class="conv-edit"
          @click.stop
        >
          <input
            v-model="draftTitle"
            type="text"
            class="conv-input conv-input-rename"
            maxlength="120"
            :aria-label="`重新命名：${conversation.conversations[id]?.title}`"
            @keydown="onRenameKeydown"
            @blur="commitRename"
          >
        </div>
        <div
          v-else
          class="conv-row"
          :class="{
            active: conversation.activeConversationId === id,
          }"
          role="button"
          tabindex="0"
          @click="selectConv(id)"
          @keydown.enter.prevent="selectConv(id)"
          @keydown.space.prevent="selectConv(id)"
        >
          <div class="conv-main">
            <span class="conv-title">{{
              conversation.conversations[id]?.title || "新對話"
            }}</span>
          </div>
          <div class="conv-actions">
            <button
              type="button"
              class="icon-btn"
              title="重新命名"
              aria-label="重新命名"
              @click="startRename(id, $event)"
            >
              ✎
            </button>
            <button
              type="button"
              class="icon-btn danger"
              title="刪除對話"
              aria-label="刪除對話"
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
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border-subtle);
}

.conv-panel-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-caption-size);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.new-chat-btn {
  width: 100%;
  margin-bottom: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-body-sm-size);
  font-weight: 600;
  color: var(--color-accent);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.new-chat-btn:hover {
  background: var(--color-accent-muted);
}

.new-chat-btn:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.conv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: min(40vh, 320px);
  overflow-y: auto;
}

.conv-item-wrap + .conv-item-wrap {
  margin-top: var(--space-1);
}

.conv-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.conv-row:hover {
  background: var(--color-bg-muted);
}

.conv-row.active {
  background: var(--color-accent-muted);
  border-color: var(--color-border-subtle);
}

.conv-row:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 2px;
}

.conv-main {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: var(--text-body-sm-size);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
}

.icon-btn {
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.icon-btn:hover {
  background: var(--color-bg-surface);
  color: var(--color-accent);
}

.icon-btn:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 1px;
}

.icon-btn.danger:hover {
  color: var(--color-danger);
}

.conv-edit {
  padding: var(--space-1);
}

.conv-input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-body);
  font-size: var(--text-body-sm-size);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
}

.conv-input:focus {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

@media (max-width: 720px) {
  .conv-list {
    max-height: 200px;
  }
}
</style>
