<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";

const props = defineProps<{
  tagLabel: string;
  body: string;
}>();

const open = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const panelId = `orig-pop-${Math.random().toString(36).slice(2, 11)}`;

const panelStyle = ref<Record<string, string>>({});

const hasBody = computed(() => props.body.trim().length > 0);
const ariaLabel = computed(() =>
  props.tagLabel.trim()
    ? `原文對照：${props.tagLabel}`
    : "原文對照",
);

function syncPanelPosition() {
  const el = triggerRef.value;
  if (!el) {
    return;
  }
  const margin = 8;
  const maxW = 400;
  const width = Math.min(maxW, window.innerWidth - margin * 2);
  const r = el.getBoundingClientRect();
  let left = r.right - width;
  if (left < margin) {
    left = margin;
  }
  if (left + width > window.innerWidth - margin) {
    left = Math.max(margin, window.innerWidth - margin - width);
  }
  let top = r.bottom + margin;
  const maxHeight = Math.min(360, window.innerHeight - top - margin);
  if (maxHeight < 120) {
    top = Math.max(margin, r.top - margin - Math.min(360, window.innerHeight * 0.45));
  }
  const finalMaxH = Math.min(
    360,
    window.innerHeight - top - margin,
  );
  panelStyle.value = {
    position: "fixed",
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    maxHeight: `${Math.max(120, finalMaxH)}px`,
    zIndex: "3000",
  };
}

function close() {
  open.value = false;
}

function toggle(e: MouseEvent) {
  e.stopPropagation();
  open.value = !open.value;
  if (open.value) {
    void nextTick(() => {
      syncPanelPosition();
      panelRef.value?.focus();
    });
  }
}

function onDocMouseDown(e: MouseEvent) {
  const t = e.target as Node;
  if (triggerRef.value?.contains(t)) {
    return;
  }
  if (panelRef.value?.contains(t)) {
    return;
  }
  close();
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") {
    close();
    triggerRef.value?.focus();
  }
}

function onResize() {
  if (open.value) {
    syncPanelPosition();
  }
}

watch(open, (v) => {
  if (v) {
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("mousedown", onDocMouseDown, true);
    window.addEventListener("resize", onResize);
  } else {
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("mousedown", onDocMouseDown, true);
    window.removeEventListener("resize", onResize);
  }
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKey, true);
  document.removeEventListener("mousedown", onDocMouseDown, true);
  window.removeEventListener("resize", onResize);
});
</script>

<template>
  <div class="orig-wrap">
    <button
      ref="triggerRef"
      type="button"
      class="orig-trigger"
      :disabled="!hasBody"
      :aria-expanded="open"
      :aria-controls="panelId"
      :title="hasBody ? '在側邊開啟完整原文' : '無原文可對照'"
      @click="toggle"
    >
      原文
    </button>
    <Teleport to="body">
      <div
        v-show="open"
        :id="panelId"
        ref="panelRef"
        class="orig-panel"
        role="region"
        :aria-label="ariaLabel"
        tabindex="-1"
        :style="panelStyle"
      >
        <div class="orig-panel-inner">
          <p v-if="tagLabel.trim()" class="orig-tag">
            {{ tagLabel }}
          </p>
          <pre class="orig-text">{{ body }}</pre>
          <button type="button" class="orig-close ds-btn-secondary-inline" @click="close">
            關閉
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.orig-wrap {
  flex-shrink: 0;
}

.orig-trigger {
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-body);
  font-size: var(--text-caption-size);
  font-weight: 600;
  line-height: 1.2;
  color: var(--color-accent);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.orig-trigger:hover:not(:disabled) {
  background: var(--color-accent-muted);
  color: var(--color-text-primary);
}

.orig-trigger:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.orig-trigger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.orig-panel {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-popover);
  overflow: hidden;
}

.orig-panel-inner {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  max-height: inherit;
  min-height: 0;
  box-sizing: border-box;
}

.orig-tag {
  margin: 0;
  font-size: var(--text-caption-size);
  font-weight: 600;
  color: var(--color-text-muted);
  word-break: break-word;
}

.orig-text {
  margin: 0;
  flex: 1 1 auto;
  overflow: auto;
  min-height: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-sm-size);
  line-height: var(--text-body-sm-leading);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.orig-close {
  align-self: flex-end;
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
}

.ds-btn-secondary-inline:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
