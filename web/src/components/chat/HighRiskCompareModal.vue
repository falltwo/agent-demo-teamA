<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";

const props = defineProps<{
  open: boolean;
  title?: string;
  /** 標註／摘要（純文字或 markdown 來源，內部轉為 pre-wrap 顯示） */
  annotationText: string;
  /** 風險原因（後端 chunk 額外欄位等） */
  riskReason?: string;
  /** 原文片段 */
  sourceText: string;
}>();

const emit = defineEmits<{
  (e: "update:open", v: boolean): void;
}>();

const panelRef = ref<HTMLDivElement | null>(null);
const lastFocus = ref<HTMLElement | null>(null);

const mqNarrow = ref(false);
let mql: MediaQueryList | null = null;

const narrowTab = ref<"ann" | "src">("ann");

function syncMq() {
  mqNarrow.value =
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 719px)").matches;
}

onMounted(() => {
  mql = window.matchMedia("(max-width: 719px)");
  syncMq();
  mql.addEventListener("change", syncMq);
});


const hasReason = computed(
  () => typeof props.riskReason === "string" && props.riskReason.trim().length > 0,
);

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
      narrowTab.value = "ann";
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
  mql?.removeEventListener("change", syncMq);
  document.removeEventListener("keydown", onDocKeydown, true);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-show="open"
      class="hrm-backdrop"
      role="presentation"
      @click="onBackdropClick"
    >
      <div
        ref="panelRef"
        class="hrm-dialog"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="open ? 'hrm-dialog-title' : undefined"
        tabindex="-1"
        @keydown="onPanelKeydown"
        @click.stop
      >
        <header class="hrm-head">
          <div class="hrm-head-text">
            <h2 id="hrm-dialog-title" class="hrm-title">
              {{ title || "高風險標註與原文對照" }}
            </h2>
            <p class="hrm-subtitle">
              請以原始文件為準；畫面僅供輔助閱讀。
            </p>
          </div>
          <button
            type="button"
            class="hrm-close ds-btn-secondary-inline"
            aria-label="關閉對照視窗"
            @click="close"
          >
            關閉
          </button>
        </header>

        <div
          v-if="mqNarrow"
          class="hrm-tabs"
          role="tablist"
          aria-label="對照分頁"
        >
          <button
            type="button"
            role="tab"
            class="hrm-tab"
            :aria-selected="narrowTab === 'ann'"
            @click="narrowTab = 'ann'"
          >
            標註與摘要
          </button>
          <button
            type="button"
            role="tab"
            class="hrm-tab"
            :aria-selected="narrowTab === 'src'"
            @click="narrowTab = 'src'"
          >
            原文片段
          </button>
        </div>

        <div
          class="hrm-body"
          :class="{ 'hrm-body--stack': !mqNarrow }"
        >
          <section
            v-show="!mqNarrow || narrowTab === 'ann'"
            class="hrm-col"
            aria-labelledby="hrm-ann-label"
          >
            <h3 id="hrm-ann-label" class="hrm-col-title">
              標註與摘要
            </h3>
            <p v-if="hasReason" class="hrm-reason">
              <span class="hrm-reason-label">風險原因</span>
              {{ riskReason }}
            </p>
            <pre class="hrm-pre">{{ annotationText }}</pre>
          </section>

          <section
            v-show="!mqNarrow || narrowTab === 'src'"
            class="hrm-col"
            aria-labelledby="hrm-src-label"
          >
            <h3 id="hrm-src-label" class="hrm-col-title">
              原文片段
            </h3>
            <pre class="hrm-pre hrm-pre--source">{{ sourceText || "（無對應原文片段）" }}</pre>
          </section>
        </div>

        <p class="hrm-hint">
          窄螢幕請用上方分頁切換「標註」與「原文」。
        </p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.hrm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(15, 18, 28, 0.45);
  box-sizing: border-box;
}

.hrm-dialog {
  display: flex;
  flex-direction: column;
  max-width: min(960px, 100%);
  max-height: min(88vh, 900px);
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-popover);
  outline: none;
}

.hrm-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}

.hrm-head-text {
  min-width: 0;
  flex: 1;
}

.hrm-title {
  margin: 0;
  font-size: var(--text-body-size);
  font-weight: 700;
  color: var(--color-text-primary);
}

.hrm-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-caption-size);
  line-height: var(--text-caption-leading);
  color: var(--color-text-muted);
}

.hrm-body {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.hrm-tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.hrm-tab {
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-body-sm-size);
  font-weight: 600;
  color: var(--color-text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  margin-bottom: -1px;
}

.hrm-tab[aria-selected="true"] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

.hrm-tab:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

@media (min-width: 720px) {
  .hrm-body--stack {
    grid-template-columns: 1fr 1fr;
    align-items: stretch;
  }
}

.hrm-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-height: 0;
  min-width: 0;
}

.hrm-col-title {
  margin: 0;
  font-size: var(--text-caption-size);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hrm-reason {
  margin: 0;
  font-size: var(--text-body-sm-size);
  line-height: var(--text-body-sm-leading);
  color: var(--color-text-secondary);
}

.hrm-reason-label {
  display: block;
  font-size: var(--text-caption-size);
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: var(--space-1);
}

.hrm-pre {
  margin: 0;
  flex: 1 1 auto;
  min-height: 120px;
  max-height: min(42vh, 360px);
  overflow: auto;
  padding: var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-body-sm-size);
  line-height: var(--text-body-sm-leading);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

.hrm-pre--source {
  font-family: var(--font-mono);
  font-size: var(--text-code-size);
}

.hrm-hint {
  margin: 0;
  padding: 0 var(--space-4) var(--space-3);
  font-size: var(--text-caption-size);
  color: var(--color-text-muted);
}

@media (min-width: 720px) {
  .hrm-hint {
    display: none;
  }
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

.hrm-close:hover {
  background: var(--color-accent-muted);
}
</style>
