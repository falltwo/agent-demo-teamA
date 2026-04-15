/// <reference types="vite/client" />

import "axios";

declare module "axios" {
  export interface AxiosRequestConfig {
    /** 為 true 時由攔截器觸發 subscribeApiLoading */
    showLoading?: boolean;
  }
  export interface InternalAxiosRequestConfig {
    __apiLoadingStarted?: boolean;
  }
}
