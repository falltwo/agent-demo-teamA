import type { ChunkItem } from "@/types/api";

export interface UserConversationMessage {
  role: "user";
  content: string;
}

export interface AssistantConversationMessage {
  role: "assistant";
  content: string;
  sources: string[];
  chunks: ChunkItem[];
  tool_name: string;
  extra: Record<string, unknown> | null;
}

export type ConversationMessage =
  | UserConversationMessage
  | AssistantConversationMessage;

/** 多對話分頁一則（含前端標題與訊息；updatedAt 供側欄排序） */
export interface ConversationEntry {
  id: string;
  title: string;
  messages: ConversationMessage[];
  updatedAt: number;
}

export function isAssistantMessage(
  m: ConversationMessage,
): m is AssistantConversationMessage {
  return m.role === "assistant";
}
