import { apiClient } from "@/api/client";
import type {
  EvalBatchDetailResponse,
  EvalBatchListResponse,
  EvalConfigResponse,
  EvalRunsResponse,
} from "@/types/api";

export async function getEvalConfig(
  options?: { showLoading?: boolean },
): Promise<EvalConfigResponse> {
  const { data } = await apiClient.get<EvalConfigResponse>("/api/v1/eval/config", {
    showLoading: options?.showLoading,
  });
  return data;
}

export async function getEvalRuns(
  limit = 200,
  options?: { showLoading?: boolean },
): Promise<EvalRunsResponse> {
  const safeLimit = Math.max(1, Math.min(limit, 500));
  const { data } = await apiClient.get<EvalRunsResponse>("/api/v1/eval/runs", {
    params: { limit: safeLimit },
    showLoading: options?.showLoading,
  });
  return data;
}

export async function listEvalBatchRuns(
  options?: { showLoading?: boolean },
): Promise<EvalBatchListResponse> {
  const { data } = await apiClient.get<EvalBatchListResponse>("/api/v1/eval/batch/runs", {
    showLoading: options?.showLoading,
  });
  return data;
}

export async function getEvalBatchDetail(
  runId: string,
  options?: { showLoading?: boolean },
): Promise<EvalBatchDetailResponse> {
  const { data } = await apiClient.get<EvalBatchDetailResponse>(
    `/api/v1/eval/batch/${encodeURIComponent(runId)}`,
    {
      showLoading: options?.showLoading,
    },
  );
  return data;
}

