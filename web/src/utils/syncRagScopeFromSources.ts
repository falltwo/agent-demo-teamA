import { getSources } from "@/api/sources";
import { useSettingsStore } from "@/stores/settings";

/**
 * 對齊 Streamlit：`has_uploads_here = len(list_sources(chat_id=...)) > 0`
 * → checkbox「只搜尋此對話上傳」預設為該值。
 */
export async function syncRagScopeFromSourcesForChat(
  chatId: string | null,
  options?: { showLoading?: boolean },
): Promise<{ ok: boolean; hasUploads: boolean }> {
  const settings = useSettingsStore();
  if (!chatId) {
    settings.setRagScopeToActiveChat(false);
    return { ok: true, hasUploads: false };
  }
  try {
    const { entries } = await getSources(chatId, options);
    const has = Array.isArray(entries) && entries.length > 0;
    settings.setRagScopeToActiveChat(has);
    return { ok: true, hasUploads: has };
  } catch {
    return { ok: false, hasUploads: false };
  }
}
