/// <reference types="vite/client" />

import "axios";

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "axios" {
  export interface AxiosRequestConfig {
    /** 為 true 時由攔截器觸發 subscribeApiLoading */
    showLoading?: boolean;
  }
  export interface InternalAxiosRequestConfig {
    __apiLoadingStarted?: boolean;
  }
}
