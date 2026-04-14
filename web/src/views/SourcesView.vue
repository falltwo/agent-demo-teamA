<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import ApiErrorBlock from "@/components/ui/ApiErrorBlock.vue";
import { ApiError } from "@/api/client";
import { getSources } from "@/api/sources";
import { pushToast } from "@/state/toast";
import { useConversationStore } from "@/stores/conversation";
import { parseSourceRow } from "@/utils/sourceEntry";

const conversation = useConversationStore();

/** 空字串 = 不帶 chat_id，列出全部 */
const filterChatId = ref("");

const loading = ref(false);
const loadError = ref<unknown>(null);
const rows = ref<
  { source: string; chunk_count: number; chat_id: string | null }[]
>([]);

const filterOptions = computed(() => {
  const ids = conversation.conversationIds;
  return [{ value: "", label: "全部" }].concat(
    ids.map((id) => ({
      value: id,
      label: conversation.conversations[id]?.title
        ? `${conversation.conversations[id].title} (${id.slice(0, 8)}…)`
        : id,
    })),
  );
});

async function load() {
  loading.value = true;
  loadError.value = null;
  try {
    const cid = filterChatId.value.trim();
    const res = await getSources(cid === "" ? null : cid, {
      showLoading: true,
    });
    const list = Array.isArray(res.entries) ? res.entries : [];
    rows.value = list.map((e) =>
      parseSourceRow(e as Record<string, unknown>),
    );
  } catch (e) {
    rows.value = [];
    loadError.value = e;
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
    loading.value = false;
  }
}

watch(
  filterChatId,
  () => {
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <div class="page">
    <header class="ds-page-head">
      <h1 class="ds-page-title">已加入的檔案</h1>
      <p class="ds-page-desc">
        查看<strong>哪些檔案已加入</strong>、各檔大概分成幾段。可只看目前對話，或一次看全部，確認沒漏加、沒加錯對話。
      </p>
    </header>

    <section class="ds-card">
      <div class="toolbar">
        <label class="filter" for="sources-filter-chat">
          <span class="filter-label">篩選對話</span>
          <select
            id="sources-filter-chat"
            v-model="filterChatId"
            class="ds-select select"
            name="chat_id"
            :disabled="loading"
          >
            <option
              v-for="opt in filterOptions"
              :key="opt.value === '' ? 'all' : opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </label>
        <div class="toolbar-actions">
          <button
            type="button"
            class="ds-btn ds-btn--secondary"
            :disabled="loading"
            @click="load"
          >
            {{ loading ? "載入中…" : "重新整理" }}
          </button>
          <RouterLink class="ds-btn ds-btn--secondary" to="/chat">返回對話</RouterLink>
        </div>
      </div>

      <ApiErrorBlock
        v-if="loadError"
        :error="loadError"
        title="檔案列表載入失敗"
      />

      <div
        v-else-if="loading"
        class="table-skel"
        aria-busy="true"
        aria-label="載入檔案列表中"
      >
        <div
          v-for="n in 6"
          :key="n"
          class="ds-skeleton ds-skeleton-line skel-row"
        />
      </div>

      <div v-else-if="rows.length === 0" class="empty">
        尚無來源紀錄，或篩選條件下無資料。
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>source</th>
            <th>chunk_count</th>
            <th>chat_id</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i">
            <td class="cell-source">{{ r.source }}</td>
            <td>{{ r.chunk_count }}</td>
            <td class="cell-id">{{ r.chat_id ?? "—" }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.filter {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 220px;
}

.filter-label {
  font-size: var(--text-caption-size);
  color: var(--color-text-muted);
}

.select {
  padding: var(--space-2) var(--space-3);
  min-height: 40px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.toolbar-actions .ds-btn {
  text-decoration: none;
}

.table-skel {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2) 0;
}

.skel-row {
  height: 2.25rem;
  margin: 0;
}

.empty {
  font-size: var(--text-body-sm-size);
  color: var(--color-text-muted);
  padding: var(--space-3) 0;
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
  vertical-align: top;
}

.table th {
  background: var(--color-bg-muted);
  font-weight: 600;
}

.cell-source {
  word-break: break-word;
}

.cell-id {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  word-break: break-all;
}
</style>
