/**
 * 對齊 streamlit_app._split_answer_and_refs：內文與「**參考連結：**」之後分離。
 */
export function splitAnswerAndRefs(content: string): {
  main: string;
  refs: string | null;
} {
  if (!content || !content.includes("**參考連結：**")) {
    return { main: content || "", refs: null };
  }
  const parts = content.split("**參考連結：**", 2);
  const mainPart = (parts[0] ?? "").trim();
  const refsPart =
    parts.length > 1 ? (parts[1] ?? "").trim() || null : null;
  return { main: mainPart, refs: refsPart };
}
