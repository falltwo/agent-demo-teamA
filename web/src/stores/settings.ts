import { defineStore } from "pinia";

import type { ChatRequest } from "@/types/api";

const STORAGE_KEY = "agent-demo-web:settings";

export interface SettingsSnapshot {
  topK: number;
  strict: boolean;
  ragScopeToActiveChat: boolean;
}

function clampTopK(n: number): number {
  return Math.min(20, Math.max(1, Math.round(n)));
}

function loadSnapshot(): Partial<SettingsSnapshot> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    return parsed as Partial<SettingsSnapshot>;
  } catch {
    return {};
  }
}

export const useSettingsStore = defineStore("settings", {
  state: (): SettingsSnapshot => {
    const saved = loadSnapshot();
    return {
      topK: clampTopK(typeof saved.topK === "number" ? saved.topK : 5),
      strict: typeof saved.strict === "boolean" ? saved.strict : false,
      ragScopeToActiveChat:
        typeof saved.ragScopeToActiveChat === "boolean"
          ? saved.ragScopeToActiveChat
          : false,
    };
  },
  actions: {
    setTopK(value: number) {
      this.topK = clampTopK(value);
      this.persist();
    },
    setStrict(value: boolean) {
      this.strict = value;
      this.persist();
    },
    setRagScopeToActiveChat(value: boolean) {
      this.ragScopeToActiveChat = value;
      this.persist();
    },
    persist() {
      try {
        const payload: SettingsSnapshot = {
          topK: this.topK,
          strict: this.strict,
          ragScopeToActiveChat: this.ragScopeToActiveChat,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      } catch {
        /* ignore quota / private mode */
      }
    },
    /**
     * 對齊 Streamlit：`rag_scope_chat_id = active_conv_id` 僅在勾選「只搜此對話上傳」時。
     */
    resolveRagScopeChatId(activeConversationId: string | null): ChatRequest["rag_scope_chat_id"] {
      if (!this.ragScopeToActiveChat || !activeConversationId) {
        return null;
      }
      return activeConversationId;
    },
  },
});
