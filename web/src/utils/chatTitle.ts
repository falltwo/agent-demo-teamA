/** 對齊 streamlit_app：第一則使用者問題時，標題為問題前 20 字，超長加 … */
export const NEW_CONVERSATION_TITLE = "新對話";

export function titleFromFirstUserMessage(question: string): string {
  const q = (question || "").trim();
  if (!q) {
    return NEW_CONVERSATION_TITLE;
  }
  return q.length > 20 ? `${q.slice(0, 20)}…` : q;
}
