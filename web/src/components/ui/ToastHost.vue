<script setup lang="ts">
import { toastItems, dismissToast } from "@/state/toast";

const list = toastItems();

function formatDetails(d: unknown): string {
  if (d === undefined || d === null) {
    return "";
  }
  if (typeof d === "string") {
    return d;
  }
  try {
    return JSON.stringify(d, null, 2);
  } catch {
    return String(d);
  }
}
</script>

<template>
  <div class="toast-host" aria-live="assertive" aria-relevant="additions">
    <TransitionGroup name="toast">
      <article
        v-for="t in list"
        :key="t.id"
        class="toast"
        :data-variant="t.variant"
        role="status"
      >
        <div class="toast-head">
          <span v-if="t.code" class="toast-code">{{ t.code }}</span>
          <button
            type="button"
            class="toast-close"
            aria-label="關閉通知"
            @click="dismissToast(t.id)"
          >
            ×
          </button>
        </div>
        <p class="toast-msg">{{ t.message }}</p>
        <details v-if="t.details != null" class="toast-details">
          <summary>詳情（API error.details）</summary>
          <pre class="toast-pre">{{ formatDetails(t.details) }}</pre>
        </details>
      </article>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  right: var(--space-3);
  bottom: var(--space-3);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: min(420px, calc(100vw - var(--space-6)));
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-strong);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-popover);
  font-size: var(--text-body-sm-size);
}

.toast[data-variant="error"] {
  border-color: var(--color-danger);
  background: var(--color-danger-muted);
}

.toast-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.toast-code {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  font-weight: 700;
  color: var(--color-danger);
}

.toast-msg {
  margin: 0;
  color: var(--color-text-primary);
  line-height: var(--text-body-sm-leading);
}

.toast-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0 var(--space-1);
  color: var(--color-text-muted);
}

.toast-close:hover {
  color: var(--color-text-primary);
}

.toast-close:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.toast-details {
  margin-top: var(--space-2);
  font-size: var(--text-caption-size);
}

.toast-details summary {
  cursor: pointer;
  color: var(--color-accent);
}

.toast-pre {
  margin: var(--space-2) 0 0;
  padding: var(--space-2);
  max-height: 160px;
  overflow: auto;
  font-size: var(--text-caption-size);
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
