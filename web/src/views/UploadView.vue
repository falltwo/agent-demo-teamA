<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import ApiErrorBlock from "@/components/ui/ApiErrorBlock.vue";
import { ApiError } from "@/api/client";
import { postIngestUpload } from "@/api/ingest";
import type { IngestUploadResponse } from "@/types/api";
import { pushToast } from "@/state/toast";
import { useConversationStore } from "@/stores/conversation";
import { syncRagScopeFromSourcesForChat } from "@/utils/syncRagScopeFromSources";

const conversation = useConversationStore();

const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const uploadError = ref<unknown>(null);
const validationHint = ref<string | null>(null);
const lastResult = ref<IngestUploadResponse | null>(null);
const refreshScopeAfterUpload = ref(true);
const scopeRefreshed = ref<string | null>(null);

const activeId = () => conversation.activeConversationId;

const activeTitle = computed(() => {
  const c = conversation.activeConversation;
  return c?.title?.trim() ? c.title : "—";
});

async function onSubmit() {
  const input = fileInput.value;
  const files = input?.files;
  if (!files?.length || uploading.value) {
    return;
  }
  const cid = activeId();
  if (!cid) {
    validationHint.value = "沒有作用中對話，請先至「對話」建立或切換對話。";
    return;
  }
  validationHint.value = null;
  const list = Array.from(files);
  uploading.value = true;
  uploadError.value = null;
  lastResult.value = null;
  scopeRefreshed.value = null;
  try {
    const res = await postIngestUpload(list, cid, { showLoading: true });
    lastResult.value = res;
    if (input) {
      input.value = "";
    }
    if (refreshScopeAfterUpload.value) {
      const r = await syncRagScopeFromSourcesForChat(cid, {
        showLoading: false,
      });
      scopeRefreshed.value = r.ok
        ? r.hasUploads
          ? "已更新：本對話有來源，檢索範圍已同步。"
          : "已更新：仍無來源紀錄。"
        : "檢索範圍未更新（來源 API 失敗）。";
    }
  } catch (e) {
    uploadError.value = e;
    if (e instanceof ApiError) {
      pushToast({
        variant: "error",
        code: e.code,
        message: e.message,
        details: e.details,
      });
    } else {
      pushToast({
        variant: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
  } finally {
    uploading.value = false;
  }
}

async function refreshScopeOnly() {
  const cid = activeId();
  if (!cid) {
    return;
  }
  uploadError.value = null;
  const r = await syncRagScopeFromSourcesForChat(cid, { showLoading: true });
  scopeRefreshed.value = r.ok
    ? r.hasUploads
      ? "已同步：本對話有來源。"
      : "已同步：本對話尚無來源。"
    : "無法取得來源列表。";
}
</script>

<template>
  <div class="page">
    <header class="ds-page-head">
      <h1 class="ds-page-title">上傳檔案</h1>
      <p class="ds-page-desc">
        選好檔案後上傳並處理，內容會掛在<strong>目前使用中</strong>的那一則對話；完成後到「對話」頁提問，助理就能引用這些內容。
      </p>
    </header>

    <section class="ds-card">
      <p class="meta">
        目前對話：<span class="meta-title">{{ activeTitle }}</span>
        <RouterLink class="ds-inline-link" to="/chat">前往對話</RouterLink>
      </p>

      <form class="form" @submit.prevent="onSubmit">
        <label class="field" for="upload-files-input">
          <span class="label">檔案（可多選）</span>
          <input
            id="upload-files-input"
            ref="fileInput"
            type="file"
            class="file"
            name="files"
            multiple
            accept=".txt,.md,.pdf,.docx"
            :disabled="uploading"
          />
        </label>
        <label class="field check" for="upload-refresh-scope">
          <input
            id="upload-refresh-scope"
            v-model="refreshScopeAfterUpload"
            type="checkbox"
            :disabled="uploading"
          />
          <span>上傳完成後，自動在對話頁開啟「只找本對話檔案」，避免混到其他對話的內容。</span>
        </label>
        <div class="actions">
          <button
            type="submit"
            class="ds-btn ds-btn--primary"
            :disabled="uploading"
          >
            {{ uploading ? "處理中…" : "上傳並處理" }}
          </button>
          <button
            type="button"
            class="ds-btn ds-btn--secondary"
            :disabled="uploading"
            @click="refreshScopeOnly"
          >
            僅重新整理檔案範圍
          </button>
        </div>
      </form>

      <p v-if="scopeRefreshed" class="scope-hint" role="status">
        {{ scopeRefreshed }}
      </p>

      <p v-if="validationHint" class="validation-hint" role="status">
        {{ validationHint }}
      </p>

      <ApiErrorBlock
        v-if="uploadError"
        :error="uploadError"
        title="上傳請求失敗"
      />

      <div
        v-if="uploading"
        class="upload-skel"
        aria-busy="true"
        aria-label="上傳處理中"
      >
        <div class="ds-skeleton ds-skeleton-line" style="width: 100%" />
        <div class="ds-skeleton ds-skeleton-line" style="width: 88%" />
        <div class="ds-skeleton ds-skeleton-line" style="width: 72%" />
      </div>

      <div v-if="lastResult" class="result">
        <h2 class="result-title">本次結果</h2>
        <p>
          <strong>chunks_ingested：</strong> {{ lastResult.chunks_ingested }}
        </p>
        <p v-if="(lastResult.skipped_files ?? []).length > 0">
          <strong>skipped_files：</strong>
        </p>
        <ul v-if="(lastResult.skipped_files ?? []).length > 0" class="skipped">
          <li v-for="(f, i) in lastResult.skipped_files ?? []" :key="i">
            {{ f }}
          </li>
        </ul>
        <h3 class="sub-title">sources_updated</h3>
        <div v-if="(lastResult.sources_updated ?? []).length === 0" class="muted">
          （無）
        </div>
        <table
          v-else
          class="table"
        >
          <thead>
            <tr>
              <th>source</th>
              <th>chunk_count</th>
              <th>chat_id</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in lastResult.sources_updated ?? []"
              :key="i"
            >
              <td>{{ row.source }}</td>
              <td>{{ row.chunk_count }}</td>
              <td>{{ row.chat_id ?? "—" }}</td>
            </tr>
          </tbody>
        </table>
        <p class="footer-links">
          <RouterLink to="/sources">查看已加入的檔案</RouterLink>
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.meta {
  margin: 0 0 var(--space-3);
  font-size: var(--text-body-sm-size);
  color: var(--color-text-secondary);
}

.meta-title {
  font-weight: 600;
  color: var(--color-text-primary);
  word-break: break-word;
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-body-sm-size);
  color: var(--color-text-secondary);
}

.field.check {
  flex-direction: row;
  align-items: flex-start;
  gap: var(--space-2);
}

.label {
  font-weight: 600;
}

.file {
  font-size: var(--text-body-sm-size);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.scope-hint {
  margin: var(--space-3) 0 0;
  font-size: var(--text-caption-size);
  color: var(--color-success);
}

.validation-hint {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-warning-muted);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
  color: var(--color-warning);
  font-size: var(--text-body-sm-size);
}

.upload-skel {
  margin-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.result {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.result-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-title-size);
}

.sub-title {
  margin: var(--space-3) 0 var(--space-2);
  font-size: var(--text-body-size);
}

.skipped {
  margin: var(--space-1) 0 var(--space-3);
  padding-left: var(--space-4);
  color: var(--color-warning);
  font-size: var(--text-body-sm-size);
}

.muted {
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
  padding: var(--space-2) var(--space-3);
  text-align: left;
}

.table th {
  background: var(--color-bg-muted);
  font-weight: 600;
}

.footer-links {
  margin: var(--space-4) 0 0;
}

.footer-links a {
  color: var(--color-accent);
  font-weight: 600;
}
</style>
