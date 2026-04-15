import { apiClient } from "@/api/client";
import type { SourcesListResponse } from "@/types/api";

export async function getSources(
  chatId?: string | null,
  options?: { showLoading?: boolean },
): Promise<SourcesListResponse> {
  const params =
    chatId != null && chatId !== "" ? { chat_id: chatId } : undefined;
  const { data } = await apiClient.get<SourcesListResponse>("/api/v1/sources", {
    params,
    showLoading: options?.showLoading,
  });
  return data;
}
