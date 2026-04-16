import { apiClient } from "@/api/client";
import type { ChatRequest, ChatResponse } from "@/types/api";

export async function postChat(
  body: ChatRequest,
  options?: { showLoading?: boolean },
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/api/v1/chat", body, {
    showLoading: options?.showLoading,
    timeout: 45000,
  });
  return data;
}
