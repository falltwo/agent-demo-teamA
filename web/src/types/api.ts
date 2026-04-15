/**
 * API 型別：由 `contracts/openapi.json` 經 openapi-typescript 產生（`openapi.generated.ts`），
 * 此檔僅重新匯出並保留未列入 OpenAPI 的錯誤本文型別。
 *
 * 更新契約：`npm run openapi:sync`（專案根目錄須能執行 `uv run python scripts/export_openapi.py`）。
 */
import type { components } from "@/types/openapi.generated";

type Schemas = components["schemas"];

export type ChatMessage = Schemas["ChatMessage"];
export type ChatRole = ChatMessage["role"];

export type ChatRequest = Schemas["ChatRequest"];
export type ChatResponse = Schemas["ChatResponse"];
export type ChunkItem = Schemas["ChunkItem"];
export type SourceEntry = Schemas["SourceEntry"];
export type IngestUploadResponse = Schemas["IngestUploadResponse"];
export type SourcesListResponse = Schemas["SourcesListResponse"];
export type HealthResponse = Schemas["HealthResponse"];
export type EvalConfigResponse = Schemas["EvalConfigResponse"];
export type EvalRunEntry = Schemas["EvalRunEntry"];
export type EvalRunsResponse = Schemas["EvalRunsResponse"];
export type EvalBatchListResponse = Schemas["EvalBatchListResponse"];
export type EvalBatchDetailResponse = Schemas["EvalBatchDetailResponse"];

/** 後端 ErrorResponse；例外處理器 JSON 未納入 OpenAPI components，維持手寫 */
export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiErrorBody {
  error: ErrorDetail;
}
