import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { getUserInfo as fetchUserInfo, login as loginApi } from "@/api/auth";
import { getUserMenus } from "@/api/admin";
import type { Menu, UserInfo } from "@/api/types";
import { STORAGE_KEYS } from "@/constants";

function readStorage<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function removeStorage(key: string): void {
  localStorage.removeItem(key);
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string>(localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || "");
  const userInfo = ref<UserInfo | null>(readStorage<UserInfo | null>(STORAGE_KEYS.USER_INFO, null));
  const menus = ref<Menu[]>(readStorage<Menu[]>(STORAGE_KEYS.MENUS, []));
  const roles = ref<string[]>(userInfo.value?.roles || []);
  const permissions = ref<Record<string, boolean>>({});

  const hasToken = computed(() => Boolean(accessToken.value));
  const isAuthenticated = computed(() => Boolean(accessToken.value && userInfo.value));
  const displayName = computed(
    () => userInfo.value?.nickname || userInfo.value?.username || "未登录",
  );

  function applyRolePermissions(): void {
    const next: Record<string, boolean> = {};
    roles.value.forEach((role) => {
      next[role] = true;
    });
    permissions.value = next;
  }

  async function loadUserInfo(): Promise<UserInfo> {
    const info = await fetchUserInfo();
    userInfo.value = info;
    roles.value = info.roles || [];
    applyRolePermissions();
    writeStorage(STORAGE_KEYS.USER_INFO, info);
    return info;
  }

  async function loadMenus(): Promise<Menu[]> {
    const result = await getUserMenus();
    menus.value = result;
    writeStorage(STORAGE_KEYS.MENUS, result);
    return result;
  }

  async function login(username: string, password: string): Promise<void> {
    const result = await loginApi(username, password);
    accessToken.value = result.access_token;
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, result.access_token);

    try {
      await loadUserInfo();
      await loadMenus();
    } catch (error) {
      logout();
      throw error;
    }
  }

  async function ensureSession(): Promise<void> {
    if (!accessToken.value) return;
    if (!userInfo.value) {
      await loadUserInfo();
    }
    if (menus.value.length === 0) {
      await loadMenus();
    }
  }

  function logout(): void {
    accessToken.value = "";
    userInfo.value = null;
    menus.value = [];
    roles.value = [];
    permissions.value = {};
    removeStorage(STORAGE_KEYS.ACCESS_TOKEN);
    removeStorage(STORAGE_KEYS.USER_INFO);
    removeStorage(STORAGE_KEYS.MENUS);
  }

  return {
    accessToken,
    access_token: accessToken,
    userInfo,
    menus,
    roles,
    permissions,
    hasToken,
    isAuthenticated,
    displayName,
    login,
    logout,
    loadUserInfo,
    loadMenus,
    ensureSession,
  };
});
