/**
 * 多對話狀態持久化（localStorage）；版本不符或損毀時回退為 null，由 store 建立預設單一對話。
 */
import type { ConversationEntry } from "@/types/conversation";

export const CONVERSATION_STORAGE_KEY = "agent-demo-web:conversations:v1";

export interface PersistedConversationState {
  conversations: Record<string, ConversationEntry>;
  activeConversationId: string | null;
  pendingWebVsRagOriginalQuestion: string | null;
  pendingChartConfirmationQuestion: string | null;
}

function isMessageArray(x: unknown): boolean {
  return Array.isArray(x);
}

function isValidEntry(x: unknown): x is ConversationEntry {
  if (!x || typeof x !== "object") {
    return false;
  }
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.title === "string" &&
    isMessageArray(o.messages) &&
    (typeof o.updatedAt === "number" || o.updatedAt === undefined)
  );
}

export function loadPersistedConversations():
  | Omit<PersistedConversationState, "conversations"> & {
      conversations: Record<string, ConversationEntry>;
    }
  | null {
  try {
    const raw = localStorage.getItem(CONVERSATION_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    const p = parsed as Record<string, unknown>;
    const convs = p.conversations;
    if (!convs || typeof convs !== "object") {
      return null;
    }
    const conversations: Record<string, ConversationEntry> = {};
    for (const [k, v] of Object.entries(convs)) {
      if (!isValidEntry(v)) {
        continue;
      }
      const entry = { ...v };
      if (typeof entry.updatedAt !== "number") {
        entry.updatedAt = 0;
      }
      conversations[k] = entry;
    }
    if (Object.keys(conversations).length === 0) {
      return null;
    }
    let active =
      typeof p.activeConversationId === "string"
        ? p.activeConversationId
        : null;
    if (!active || !(active in conversations)) {
      active = Object.keys(conversations)[0];
    }
    return {
      conversations,
      activeConversationId: active,
      pendingWebVsRagOriginalQuestion:
        typeof p.pendingWebVsRagOriginalQuestion === "string"
          ? p.pendingWebVsRagOriginalQuestion
          : null,
      pendingChartConfirmationQuestion:
        typeof p.pendingChartConfirmationQuestion === "string"
          ? p.pendingChartConfirmationQuestion
          : null,
    };
  } catch {
    return null;
  }
}

export function savePersistedConversations(state: PersistedConversationState): void {
  try {
    localStorage.setItem(CONVERSATION_STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* quota / private mode */
  }
}
