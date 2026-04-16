<script setup lang="ts">
import { computed } from "vue";

import { ApiError } from "@/api/client";

const props = defineProps<{
  error: unknown;
  title?: string;
}>();

const parsed = computed(() => {
  const e = props.error;
  if (e instanceof ApiError) {
    return {
      code: e.code,
      message: e.message,
      details: e.details,
      status: e.status,
    };
  }
  if (e instanceof Error) {
    return {
      code: "CLIENT_ERROR",
      message: e.message,
      details: null as unknown,
      status: undefined as number | undefined,
    };
  }
  return {
    code: "UNKNOWN",
    message: String(e),
    details: null as unknown,
    status: undefined as number | undefined,
  };
});

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
  <div class="api-err" role="alert">
    <p class="api-err-title">
      {{ title ?? "發生錯誤" }}
      <span v-if="parsed.status" class="api-err-status">HTTP {{ parsed.status }}</span>
    </p>
    <p class="api-err-line">
      <span class="api-err-code">{{ parsed.code }}</span>
      {{ parsed.message }}
    </p>
    <details v-if="parsed.details != null" class="api-err-details">
      <summary>錯誤細節</summary>
      <pre class="api-err-pre">{{ formatDetails(parsed.details) }}</pre>
    </details>
  </div>
</template>

<style scoped>
.api-err {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-danger);
  background: var(--color-danger-muted);
  font-size: var(--text-body-sm-size);
}

.api-err-title {
  margin: 0 0 var(--space-2);
  font-weight: 700;
  color: var(--color-text-primary);
}

.api-err-status {
  margin-left: var(--space-2);
  font-size: var(--text-caption-size);
  font-weight: 500;
  color: var(--color-text-muted);
}

.api-err-line {
  margin: 0;
  color: var(--color-danger);
}

.api-err-code {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  font-weight: 700;
  margin-right: var(--space-2);
}

.api-err-details {
  margin-top: var(--space-2);
}

.api-err-details summary {
  cursor: pointer;
  color: var(--color-accent);
  font-weight: 600;
}

.api-err-pre {
  margin: var(--space-2) 0 0;
  padding: var(--space-2);
  max-height: 200px;
  overflow: auto;
  font-size: var(--text-caption-size);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-subtle);
}
</style>
