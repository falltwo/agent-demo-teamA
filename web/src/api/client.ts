import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
  isAxiosError,
} from "axios";

import type { ApiErrorBody, ErrorDetail } from "@/types/api";

export class ApiError extends Error {
  readonly code: string;
  readonly details: unknown;
  readonly status?: number;

  constructor(detail: ErrorDetail, status?: number) {
    super(detail.message);
    this.name = "ApiError";
    this.code = detail.code;
    this.details = detail.details;
    this.status = status;
  }
}

let loadingDepth = 0;
const loadingListeners = new Set<(active: boolean) => void>();

export function subscribeApiLoading(listener: (active: boolean) => void): () => void {
  loadingListeners.add(listener);
  return () => {
    loadingListeners.delete(listener);
  };
}

function notifyLoading(active: boolean): void {
  loadingListeners.forEach((fn) => {
    fn(active);
  });
}

function beginLoading(): void {
  loadingDepth += 1;
  if (loadingDepth === 1) {
    notifyLoading(true);
  }
}

function endLoading(): void {
  loadingDepth = Math.max(0, loadingDepth - 1);
  if (loadingDepth === 0) {
    notifyLoading(false);
  }
}

function isErrorBody(data: unknown): data is ApiErrorBody {
  if (!data || typeof data !== "object") {
    return false;
  }
  const err = (data as ApiErrorBody).error;
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    "message" in err &&
    typeof (err as ErrorDetail).code === "string" &&
    typeof (err as ErrorDetail).message === "string"
  );
}

function toApiError(error: AxiosError): ApiError {
  const status = error.response?.status;
  const data = error.response?.data;
  if (isErrorBody(data)) {
    return new ApiError(data.error, status);
  }
  const msg = error.message || "網路或伺服器錯誤";
  return new ApiError({ code: "UNKNOWN_ERROR", message: msg, details: data }, status);
}

export const apiClient = axios.create({
  baseURL: "",
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.showLoading) {
    beginLoading();
    config.__apiLoadingStarted = true;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const cfg = response.config;
    if (cfg.__apiLoadingStarted) {
      endLoading();
    }
    return response;
  },
  (error: unknown) => {
    if (isAxiosError(error)) {
      const cfg = error.config as InternalAxiosRequestConfig | undefined;
      if (cfg?.__apiLoadingStarted) {
        endLoading();
      }
      return Promise.reject(toApiError(error));
    }
    return Promise.reject(error);
  },
);
