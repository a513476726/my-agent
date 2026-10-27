export type LogLevel = "debug" | "info" | "warn" | "error";

export interface EnvConfig {
  APP_TITLE: string;
  API_BASE_URL: string;
  API_TIMEOUT: number;
  DEBUG: boolean;
  LOG_LEVEL: LogLevel;
}

function parseBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined || value === "") return fallback;
  return value === "true" || value === "1";
}

const envConfig: EnvConfig = {
  APP_TITLE: import.meta.env.VITE_APP_TITLE || "个人工作助理 Agent 平台",
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || "",
  API_TIMEOUT: Number(import.meta.env.VITE_API_TIMEOUT || 15000),
  DEBUG: parseBoolean(import.meta.env.VITE_APP_DEBUG, import.meta.env.DEV),
  LOG_LEVEL: (import.meta.env.VITE_APP_DEBUG ? "debug" : "info") as LogLevel,
};

export default envConfig;
