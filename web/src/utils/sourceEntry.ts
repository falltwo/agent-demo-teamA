/** 將 /api/v1/sources 的 entries 列正規化為表格列 */
export function parseSourceRow(row: Record<string, unknown>): {
  source: string;
  chunk_count: number;
  chat_id: string | null;
} {
  return {
    source: String(row.source ?? ""),
    chunk_count:
      typeof row.chunk_count === "number"
        ? row.chunk_count
        : Number(row.chunk_count) || 0,
    chat_id:
      row.chat_id == null || row.chat_id === ""
        ? null
        : String(row.chat_id),
  };
}
