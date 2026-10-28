export const STORAGE_KEYS = {
  ACCESS_TOKEN: "my-agent.access_token",
  USER_INFO: "my-agent.user_info",
  MENUS: "my-agent.menus",
} as const;

export const APP_MENU_NAME = "admin";

export const REPORT_KIND_OPTIONS = [
  { label: "日报", value: "daily" },
  { label: "周报", value: "weekly" },
  { label: "季报", value: "quarterly" },
] as const;
