import { apiClient } from "@/api/client";
import type { IngestUploadResponse } from "@/types/api";

export async function postIngestUpload(
  files: File | File[],
  chatId?: string | null,
  options?: { showLoading?: boolean },
): Promise<IngestUploadResponse> {
  const form = new FormData();
  const list = Array.isArray(files) ? files : [files];
  for (const file of list) {
    form.append("files", file);
  }
  if (chatId != null && chatId !== "") {
    form.append("chat_id", chatId);
  }
  const { data } = await apiClient.post<IngestUploadResponse>(
    "/api/v1/ingest/upload",
    form,
    {
      showLoading: options?.showLoading,
    },
  );
  return data;
}
