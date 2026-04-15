<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import ApiErrorBlock from "@/components/ui/ApiErrorBlock.vue";
import { ApiError } from "@/api/client";
import {
  getEvalBatchDetail,
  getEvalConfig,
  getEvalRuns,
  listEvalBatchRuns,
} from "@/api/eval";
import { pushToast } from "@/state/toast";
import type {
  EvalBatchDetailResponse,
  EvalRunEntry,
} from "@/types/api";

const onlineLimit = ref(120);

const loadingConfig = ref(false);
const loadingRuns = ref(false);
const loadingBatch = ref(false);
const loadingDetail = ref(false);

const configError = ref<unknown>(null);
const onlineError = ref<unknown>(null);
const batchError = ref<unknown>(null);
const detailError = ref<unknown>(null);

const evalLogEnabled = ref<boolean | null>(null);
const onlineRuns = ref<EvalRunEntry[]>([]);
const batchRunIds = ref<string[]>([]);
const selectedRunId = ref("");
const batchDetail = ref<EvalBatchDetailResponse | null>(null);

function asList<T>(value: T[] | undefined | null): T[] {
  return Array.isArray(value) ? value : [];
}

function toPrettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function tsText(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

function shortText(value: string | undefined, max = 80): string {
  const text = (value || "").trim();
  if (!text) {
    return "—";
  }
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, max)}…`;
}

const metricsText = computed(() => {
  if (!batchDetail.value?.metrics) {
    return "（此批次沒有 metrics 檔）";
  }
  return toPrettyJson(batchDetail.value.metrics);
});

const resultCount = computed(() => asList(batchDetail.value?.results).length);

const previewResultsText = computed(() => {
  const rows = asList(batchDetail.value?.results).slice(0, 20);
  if (!rows.length) {
    return "（此批次沒有 results）";
  }
  return rows.map((row) => toPrettyJson(row)).join("\n\n");
});

function notifyApiError(prefix: string, err: unknown): void {
  if (err instanceof ApiError) {
    pushToast({
      variant: "error",
      code: err.code,
      message: `${prefix}：${err.message}`,
      details: err.details,
    });
    return;
  }
  pushToast({
    variant: "error",
    message: `${prefix}：${err instanceof Error ? err.message : String(err)}`,
  });
}

async function loadConfig() {
  loadingConfig.value = true;
  configError.value = null;
  try {
    const res = await getEvalConfig({ showLoading: false });
    evalLogEnabled.value = res.eval_log_enabled;
  } catch (err) {
    evalLogEnabled.value = null;
    configError.value = err;
    notifyApiError("EVAL 設定載入失敗", err);
  } finally {
    loadingConfig.value = false;
  }
}

async function loadOnlineRuns() {
  loadingRuns.value = true;
  onlineError.value = null;
  try {
    const res = await getEvalRuns(onlineLimit.value, { showLoading: true });
    evalLogEnabled.value = res.eval_log_enabled;
    onlineRuns.value = asList(res.entries);
  } catch (err) {
    onlineRuns.value = [];
    onlineError.value = err;
    notifyApiError("線上 EVAL 記錄載入失敗", err);
  } finally {
    loadingRuns.value = false;
  }
}

async function loadBatchRuns() {
  loadingBatch.value = true;
  batchError.value = null;
  try {
    const res = await listEvalBatchRuns({ showLoading: true });
    batchRunIds.value = asList(res.run_ids);
    if (!batchRunIds.value.length) {
      selectedRunId.value = "";
      batchDetail.value = null;
      return;
    }
    if (!batchRunIds.value.includes(selectedRunId.value)) {
      selectedRunId.value = batchRunIds.value[0] || "";
    }
  } catch (err) {
    batchRunIds.value = [];
    selectedRunId.value = "";
    batchDetail.value = null;
    batchError.value = err;
    notifyApiError("批次 run 列表載入失敗", err);
  } finally {
    loadingBatch.value = false;
  }
}

async function loadBatchDetail(runId: string) {
  if (!runId) {
    batchDetail.value = null;
    return;
  }
  loadingDetail.value = true;
  detailError.value = null;
  try {
    batchDetail.value = await getEvalBatchDetail(runId, { showLoading: true });
  } catch (err) {
    batchDetail.value = null;
    detailError.value = err;
    notifyApiError("批次 detail 載入失敗", err);
  } finally {
    loadingDetail.value = false;
  }
}

watch(
  selectedRunId,
  (runId) => {
    void loadBatchDetail(runId);
  },
);

void Promise.all([
  loadConfig(),
  loadOnlineRuns(),
  loadBatchRuns(),
]);
</script>

<template>
  <div class="page">
    <header class="ds-page-head">
      <h1 class="ds-page-title">EVAL 面板</h1>
      <p class="ds-page-desc">
        在這裡查看線上 EVAL 記錄與批次評估結果，快速確認工具路由、延遲與最近的執行情況。
      </p>
    </header>

    <section class="ds-card card">
      <div class="toolbar">
        <p class="status">
          EVAL_LOG：
          <strong>
            {{
              evalLogEnabled == null
                ? "未知"
                : evalLogEnabled
                  ? "啟用中"
                  : "未啟用（可讀既有記錄）"
            }}
          </strong>
        </p>
        <div class="toolbar-actions">
          <button
            type="button"
            class="ds-btn ds-btn--secondary"
            :disabled="loadingConfig || loadingRuns || loadingBatch"
            @click="
              void Promise.all([
                loadConfig(),
                loadOnlineRuns(),
                loadBatchRuns(),
              ])
            "
          >
            重新整理全部
          </button>
          <RouterLink to="/chat" class="ds-btn ds-btn--secondary">
            返回對話
          </RouterLink>
        </div>
      </div>
      <ApiErrorBlock v-if="configError" :error="configError" title="設定載入失敗" />
    </section>

    <section class="ds-card card">
      <div class="section-head">
        <h2 class="section-title">線上記錄（/api/v1/eval/runs）</h2>
        <div class="section-actions">
          <label class="limit-field" for="eval-limit">
            筆數上限
            <select
              id="eval-limit"
              v-model.number="onlineLimit"
              class="ds-select limit-select"
            >
              <option :value="50">50</option>
              <option :value="120">120</option>
              <option :value="200">200</option>
              <option :value="500">500</option>
            </select>
          </label>
          <button
            type="button"
            class="ds-btn ds-btn--secondary"
            :disabled="loadingRuns"
            @click="void loadOnlineRuns()"
          >
            {{ loadingRuns ? "載入中…" : "更新線上記錄" }}
          </button>
        </div>
      </div>

      <ApiErrorBlock v-if="onlineError" :error="onlineError" title="線上記錄載入失敗" />

      <div v-else-if="loadingRuns" class="table-skel" aria-busy="true">
        <div v-for="n in 4" :key="n" class="ds-skeleton ds-skeleton-line skel-row" />
      </div>

      <div v-else-if="onlineRuns.length === 0" class="empty">
        目前沒有線上 EVAL 記錄。
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>timestamp</th>
            <th>tool</th>
            <th>latency(s)</th>
            <th>sources</th>
            <th>chat_id</th>
            <th>question</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in onlineRuns" :key="`${row.timestamp ?? 'na'}-${i}`">
            <td class="mono">{{ tsText(row.timestamp) }}</td>
            <td>{{ shortText(row.tool_name, 28) }}</td>
            <td>{{ row.latency_sec.toFixed(3) }}</td>
            <td>{{ row.source_count }}</td>
            <td class="mono">{{ tsText(row.chat_id) }}</td>
            <td>{{ shortText(row.question, 120) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="ds-card card">
      <div class="section-head">
        <h2 class="section-title">批次結果（/api/v1/eval/batch/*）</h2>
        <div class="section-actions">
          <button
            type="button"
            class="ds-btn ds-btn--secondary"
            :disabled="loadingBatch"
            @click="void loadBatchRuns()"
          >
            {{ loadingBatch ? "載入中…" : "更新批次列表" }}
          </button>
        </div>
      </div>

      <ApiErrorBlock v-if="batchError" :error="batchError" title="批次列表載入失敗" />

      <div v-else-if="batchRunIds.length === 0" class="empty">
        目前沒有批次 run（`eval/runs` 目錄尚無結果檔）。
      </div>

      <div v-else class="batch-tools">
        <label class="run-field" for="eval-run-id">
          批次 run_id
          <select
            id="eval-run-id"
            v-model="selectedRunId"
            class="ds-select run-select"
          >
            <option v-for="id in batchRunIds" :key="id" :value="id">
              {{ id }}
            </option>
          </select>
        </label>
        <button
          type="button"
          class="ds-btn ds-btn--secondary"
          :disabled="loadingDetail || !selectedRunId"
          @click="void loadBatchDetail(selectedRunId)"
        >
          {{ loadingDetail ? "載入中…" : "重新抓取 detail" }}
        </button>
      </div>

      <ApiErrorBlock
        v-if="detailError"
        :error="detailError"
        title="批次 detail 載入失敗"
      />

      <div v-else-if="loadingDetail" class="table-skel" aria-busy="true">
        <div v-for="n in 3" :key="n" class="ds-skeleton ds-skeleton-line skel-row" />
      </div>

      <div v-else-if="batchDetail" class="detail">
        <p class="detail-meta">
          run_id：<span class="mono">{{ batchDetail.run_id }}</span>
          ｜結果筆數：<strong>{{ resultCount }}</strong>
        </p>
        <h3 class="detail-title">metrics.json</h3>
        <pre class="json-block">{{ metricsText }}</pre>

        <h3 class="detail-title">results（前 20 筆預覽）</h3>
        <pre class="json-block">{{ previewResultsText }}</pre>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.toolbar,
.section-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
}

.section-actions,
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.status {
  margin: 0;
  color: var(--color-text-secondary);
}

.status strong {
  color: var(--color-text-primary);
}

.section-title {
  margin: 0;
  font-size: var(--text-heading-size);
  color: var(--color-text-primary);
}

.limit-field,
.run-field {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-body-sm-size);
  color: var(--color-text-secondary);
}

.limit-select,
.run-select {
  min-height: 36px;
  padding: var(--space-1) var(--space-2);
}

.batch-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.empty {
  color: var(--color-text-muted);
  font-size: var(--text-body-sm-size);
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-body-sm-size);
}

.table th,
.table td {
  border: 1px solid var(--color-border-subtle);
  padding: var(--space-2);
  text-align: left;
  vertical-align: top;
}

.table th {
  background: var(--color-bg-muted);
  font-weight: 600;
}

.mono {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  word-break: break-all;
}

.table-skel {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.skel-row {
  height: 2rem;
  margin: 0;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.detail-meta {
  margin: 0;
  color: var(--color-text-secondary);
}

.detail-title {
  margin: 0;
  font-size: var(--text-body-size);
  color: var(--color-text-primary);
}

.json-block {
  margin: 0;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--text-caption-size);
  line-height: 1.45;
}

@media (max-width: 720px) {
  .limit-field,
  .run-field {
    width: 100%;
    justify-content: space-between;
  }

  .limit-select,
  .run-select {
    flex: 1;
  }

  .table {
    display: block;
    overflow-x: auto;
  }
}
</style>

