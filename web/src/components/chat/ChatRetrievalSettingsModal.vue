<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from "vue";

import { useSettingsStore } from "@/stores/settings";

const props = defineProps<{
  open: boolean;
  /** 與 ChatView 同步之來源狀態：loading | has | none | error */
  scopeSyncState: "loading" | "has" | "none" | "error";
}>();

const emit = defineEmits<{
  (e: "update:open", v: boolean): void;
}>();

const settings = useSettingsStore();

const panelRef = ref<HTMLDivElement | null>(null);
const lastFocus = ref<HTMLElement | null>(null);

function close() {
  emit("update:open", false);
}

function onBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    close();
  }
}

function focusableElements(root: HTMLElement): HTMLElement[] {
  const sel =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(root.querySelectorAll<HTMLElement>(sel)).filter(
    (el) => el.offsetParent !== null || el === document.activeElement,
  );
}

function onPanelKeydown(e: KeyboardEvent) {
  if (e.key !== "Tab" || !panelRef.value) {
    return;
  }
  const els = focusableElements(panelRef.value);
  if (els.length === 0) {
    return;
  }
  const first = els[0];
  const last = els[els.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else if (document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

function onDocKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    e.preventDefault();
    close();
  }
}

watch(
  () => props.open,
  async (v) => {
    if (v) {
      lastFocus.value = document.activeElement as HTMLElement | null;
      document.addEventListener("keydown", onDocKeydown, true);
      await nextTick();
      const el = panelRef.value;
      if (el) {
        const focusables = focusableElements(el);
        (focusables[0] ?? el).focus();
      }
    } else {
      document.removeEventListener("keydown", onDocKeydown, true);
      await nextTick();
      lastFocus.value?.focus?.();
      lastFocus.value = null;
    }
  },
);

onUnmounted(() => {
  document.removeEventListener("keydown", onDocKeydown, true);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-show="open"
      class="crs-backdrop"
      role="presentation"
      @click="onBackdropClick"
    >
      <div
        ref="panelRef"
        class="crs-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="crs-dialog-title"
        tabindex="-1"
        @keydown="onPanelKeydown"
        @click.stop
      >
        <header class="crs-head">
          <h2 id="crs-dialog-title" class="crs-title">
            檢索設定
          </h2>
          <button
            type="button"
            class="crs-close ds-btn-secondary-inline"
            aria-label="關閉設定"
            @click="close"
          >
            關閉
          </button>
        </header>

        <div class="crs-body">
          <p class="crs-lead">
            助理回答前，會先從你上傳的資料裡找相關內容；下方選項決定「找多少、找哪裡」。
          </p>
          <label class="field" for="chat-top-k-modal">
            <span class="label-with-meta">
              <span class="label">一次參考幾段內容（1–20）</span>
              <span class="label-value" aria-hidden="true">{{ settings.topK }}</span>
            </span>
            <input
              id="chat-top-k-modal"
              type="range"
              min="1"
              max="20"
              step="1"
              :value="settings.topK"
              class="range"
              name="top_k"
              :aria-valuemin="1"
              :aria-valuemax="20"
              :aria-valuenow="settings.topK"
              aria-describedby="chat-top-k-hint-modal"
              @input="
                settings.setTopK(
                  Number(($event.target as HTMLInputElement).value),
                )
              "
            />
            <span id="chat-top-k-hint-modal" class="field-hint">
              數字大：看較多段，內容可能較雜；數字小：較集中、較精準。
            </span>
          </label>
          <label class="field check" for="chat-strict-modal">
            <input
              id="chat-strict-modal"
              type="checkbox"
              :checked="settings.strict"
              name="strict"
              @change="
                settings.setStrict(($event.target as HTMLInputElement).checked)
              "
            />
            <span class="check-copy">
              <span class="check-title">只回答文件裡有的（不亂猜）</span>
              <span class="check-desc">開啟後不臆測、不補上文件裡沒寫的內容。</span>
            </span>
          </label>
          <label class="field check" for="chat-rag-scope-modal">
            <input
              id="chat-rag-scope-modal"
              type="checkbox"
              :checked="settings.ragScopeToActiveChat"
              name="rag_scope"
              @change="
                settings.setRagScopeToActiveChat(
                  ($event.target as HTMLInputElement).checked,
                )
              "
            />
            <span class="check-copy">
              <span class="check-title">只找這則對話裡的檔案</span>
              <span class="check-desc">適合已上傳附件、想避免用到其他對話檔案的狀況。</span>
            </span>
          </label>
          <div
            v-if="scopeSyncState === 'loading'"
            class="rail-skel"
            aria-hidden="true"
          >
            <div class="ds-skeleton ds-skeleton-line" style="width: 100%" />
            <div class="ds-skeleton ds-skeleton-line" style="width: 72%" />
          </div>
          <p v-else class="rail-caption" role="status">
            <template v-if="scopeSyncState === 'has'">
              本對話已有上傳檔案；已自動開啟「只找本對話檔案」。
            </template>
            <template v-else-if="scopeSyncState === 'none'">
              本對話尚無上傳檔案；已關閉「只找本對話檔案」。
            </template>
            <template v-else>
              無法取得檔案列表，請確認後端已啟動。
            </template>
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.crs-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(15, 18, 28, 0.45);
  box-sizing: border-box;
}

.crs-dialog {
  max-width: min(400px, 100%);
  width: 100%;
  max-height: min(90vh, 720px);
  overflow: auto;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-popover);
  outline: none;
}

.crs-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  position: sticky;
  top: 0;
  background: var(--color-bg-surface);
  z-index: 1;
}

.crs-title {
  margin: 0;
  font-size: var(--text-body-size);
  font-weight: 700;
  color: var(--color-text-primary);
}

.crs-body {
  padding: var(--space-3) var(--space-4) var(--space-4);
}

.crs-lead {
  margin: 0 0 var(--space-3);
  font-size: var(--text-body-sm-size);
  font-weight: 600;
  color: var(--color-text-primary);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
  font-size: var(--text-body-sm-size);
  color: var(--color-text-secondary);
}

.field.check {
  flex-direction: row;
  align-items: flex-start;
  gap: var(--space-2);
}

.label-with-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
}

.label {
  display: block;
  font-weight: 600;
  font-size: var(--text-body-sm-size);
  color: var(--color-text-primary);
}

.label-value {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  font-weight: 700;
  color: var(--color-accent);
  flex-shrink: 0;
}

.field-hint {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--text-caption-size);
  line-height: var(--text-caption-leading);
  color: var(--color-text-muted);
}

.check-copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.check-title {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--text-body-sm-size);
  line-height: 1.35;
}

.check-desc {
  font-size: var(--text-caption-size);
  line-height: var(--text-caption-leading);
  color: var(--color-text-muted);
}

.range {
  width: 100%;
  accent-color: var(--color-accent);
}

.range:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.field.check input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--color-accent);
}

.field.check input[type="checkbox"]:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.rail-caption {
  margin: calc(var(--space-2) * -1) 0 0;
  padding: 0;
  font-size: var(--text-caption-size);
  line-height: var(--text-caption-leading);
  color: var(--color-text-muted);
}

.rail-skel {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ds-btn-secondary-inline {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-caption-size);
  font-weight: 600;
  font-family: var(--font-body);
  color: var(--color-text-primary);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
  flex-shrink: 0;
}

.ds-btn-secondary-inline:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.crs-close:hover {
  background: var(--color-accent-muted);
}
</style>
