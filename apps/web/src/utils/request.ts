import { client } from "@my-agent/shared-types";
import { message } from "ant-design-vue";

import envConfig from "@/config/env";
import { STORAGE_KEYS } from "@/constants";
import { showTruncatedError } from "@/utils/message-helper";

export interface Envelope<T> {
  code?: number;
  data: T;
  message?: string;
  success?: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code?: number,
    readonly payload?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let configured = false;

function clearSession(): void {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.USER_INFO);
  localStorage.removeItem(STORAGE_KEYS.MENUS);
}

function redirectToLogin(): void {
  if (window.location.pathname === "/login") return;
  const redirect = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.replace(`/login?redirect=${redirect}`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function setupApiClient(): void {
  if (configured) return;
  configured = true;

  client.setConfig({
    baseUrl: envConfig.API_BASE_URL || window.location.origin,
    auth: () => localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || undefined,
  });

  client.interceptors.error.use((body, response, request) => {
    const payload = isRecord(body) ? body : undefined;
    if (!response) {
      const text = "网络请求失败，请检查服务是否可用";
      showTruncatedError(text);
      return new ApiError(text, undefined, undefined, payload);
    }

    const status = response.status;
    const code = typeof payload?.code === "number" ? payload.code : status;
    const serverMessage =
      typeof payload?.message === "string" && payload.message ? payload.message : "";
    const requestPath = request ? new URL(request.url).pathname : "";

    if (status === 401 && requestPath !== "/auth/login") {
      clearSession();
      message.warning("登录状态已失效，请重新登录");
      redirectToLogin();
      return new ApiError("登录状态已失效", status, code, payload);
    }

    const text = serverMessage || `请求失败（${status}）`;
    showTruncatedError(text);
    return new ApiError(text, status, code, payload);
  });
}

export async function requestData<T>(request: Promise<{ data: Envelope<T> }>): Promise<T> {
  try {
    const { data } = await request;
    if (data.success === false) {
      const error = new ApiError(data.message || "请求失败", 200, data.code, data);
      showTruncatedError(error.message);
      throw error;
    }
    return data.data;
  } catch (error) {
    if (error instanceof ApiError) throw error;

    const text = "网络请求失败，请检查服务是否可用";
    showTruncatedError(text);
    throw new ApiError(text, undefined, undefined, error);
  }
}
