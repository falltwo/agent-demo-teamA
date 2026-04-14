/**
 * 從合約審閱類回答（markdown）中找出含「【風險等級】…高風險」的條款區塊，供 UI 並列對照原文。
 * 不自檢區段（【AI 自檢】之後）不納入，避免誤判。
 */

export interface HighRiskClause {
  /** 區塊於 main 內的 [start, end) 字元區間 */
  start: number;
  end: number;
  /** 與區間相同的 markdown，供渲染 */
  displayMd: string;
  /** 【原文引述】擷取（若無則空字串） */
  quotedExcerpt: string;
  /** 由 [n] 或 #chunkN 推得的 chunks 索引提示；無則 null */
  chunkHintIndex: number | null;
}

const SELF_CHECK_MARKER = "**【AI 自檢】**";

function lineAt(text: string, pos: number): { lineStart: number; lineEnd: number } {
  let lineStart = pos;
  while (lineStart > 0 && text[lineStart - 1] !== "\n") {
    lineStart -= 1;
  }
  let lineEnd = text.indexOf("\n", pos);
  if (lineEnd === -1) {
    lineEnd = text.length;
  }
  return { lineStart, lineEnd };
}

function isHighRiskLevelLine(line: string): boolean {
  const t = line.trim();
  if (!t.includes("【風險等級】")) {
    return false;
  }
  return /\b高風險\b/.test(t);
}

function extractQuotedExcerpt(block: string): string {
  const m = block.match(/【原文引述】\s*([\s\S]*?)(?=\n【|$)/);
  if (!m) {
    return "";
  }
  return m[1]?.trim() ?? "";
}

function extractChunkHintIndex(block: string): number | null {
  const m1 = block.match(/\[(\d+)\]/g);
  if (m1?.length) {
    const n = parseInt(m1[0].replace(/[[\]]/g, ""), 10);
    if (!Number.isNaN(n) && n >= 1) {
      return n - 1;
    }
  }
  const m2 = block.match(/#chunk(\d+)/i);
  if (m2) {
    const n = parseInt(m2[1] ?? "", 10);
    if (!Number.isNaN(n)) {
      return n;
    }
  }
  return null;
}

function expandClauseStart(main: string, riskLineStart: number): number {
  const before = main.slice(0, riskLineStart);
  const idx = before.lastIndexOf("\n第");
  if (idx === -1) {
    if (main.startsWith("第")) {
      return 0;
    }
    return 0;
  }
  return idx + 1;
}

function expandClauseEnd(main: string, clauseStart: number): number {
  const sub = main.slice(clauseStart);
  const m = /\n第\s/.exec(sub);
  if (m && m.index > 0) {
    return clauseStart + m.index;
  }
  return main.length;
}

/**
 * 在 head（不含 AI 自檢附錄）內找出所有高風險條款區塊。
 */
export function findHighRiskClausesInHead(head: string): HighRiskClause[] {
  const out: HighRiskClause[] = [];
  let searchFrom = 0;
  while (searchFrom < head.length) {
    const rel = head.slice(searchFrom).search(/【風險等級】/);
    if (rel === -1) {
      break;
    }
    const pos = searchFrom + rel;
    const { lineStart, lineEnd } = lineAt(head, pos);
    const line = head.slice(lineStart, lineEnd);
    if (!isHighRiskLevelLine(line)) {
      searchFrom = lineEnd + 1;
      continue;
    }
    const start = expandClauseStart(head, lineStart);
    const end = expandClauseEnd(head, start);
    const displayMd = head.slice(start, end).trimEnd();
    const quotedExcerpt = extractQuotedExcerpt(displayMd);
    const chunkHintIndex = extractChunkHintIndex(displayMd);
    out.push({
      start,
      end,
      displayMd,
      quotedExcerpt,
      chunkHintIndex,
    });
    searchFrom = end;
  }
  return out;
}

export type MainSegment =
  | { kind: "md"; text: string }
  | { kind: "risk"; clause: HighRiskClause };

/**
 * 將 main 切成一般 markdown 與高風險條款片段（用於插入「對照原文」按鈕）。
 * 若無高風險條款則回傳單一 md 片段。
 */
export function splitMainByHighRiskClauses(main: string): MainSegment[] {
  const selfIdx = main.indexOf(SELF_CHECK_MARKER);
  const head = selfIdx === -1 ? main : main.slice(0, selfIdx);
  const tail = selfIdx === -1 ? "" : main.slice(selfIdx);

  const clauses = findHighRiskClausesInHead(head);
  if (clauses.length === 0) {
    return [{ kind: "md", text: main }];
  }

  const segments: MainSegment[] = [];
  let cursor = 0;
  for (const c of clauses) {
    if (c.start > cursor) {
      segments.push({ kind: "md", text: head.slice(cursor, c.start) });
    }
    segments.push({ kind: "risk", clause: c });
    cursor = c.end;
  }
  if (cursor < head.length) {
    segments.push({ kind: "md", text: head.slice(cursor) });
  }
  if (tail.length > 0) {
    segments.push({ kind: "md", text: tail });
  }
  return segments;
}

/** 從 ChunkItem（允許額外欄位）取得原文對照字串 */
export function sourceTextFromChunk(chunk: {
  text?: string;
  [key: string]: unknown;
}): string {
  const raw =
    (typeof chunk.source_text === "string" && chunk.source_text) ||
    (typeof chunk.document_excerpt === "string" && chunk.document_excerpt) ||
    (typeof chunk.chunk === "string" && chunk.chunk) ||
    (typeof chunk.text === "string" && chunk.text) ||
    "";
  return raw.trim();
}

/** 從 ChunkItem 取得風險原因（若有） */
export function riskReasonFromChunk(chunk: { [key: string]: unknown }): string {
  const r = chunk.risk_reason ?? chunk.riskReason;
  return typeof r === "string" ? r.trim() : "";
}
