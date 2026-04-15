import type { ChatMessage } from "@/types/api";
import type { ConversationMessage } from "@/types/conversation";

/** 對齊 Streamlit：僅 role + content 傳給後端；history 不含本輪 user message。 */
export function conversationToChatHistory(
  messages: ConversationMessage[],
): ChatMessage[] {
  return messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));
}
