<script setup lang="ts">
import {
  BgColorsOutlined,
  BulbOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";
import { computed, ref, watch } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

import BreadcrumbBar from "@/components/BreadcrumbBar.vue";
import MenuItem from "@/components/Menu/MenuItem.vue";
import TagsView from "@/components/TagsView/TagsView.vue";
import { useAuthStore } from "@/stores/auth";
import { useTagsStore } from "@/stores/tags";
import { useThemeStore } from "@/stores/theme";
import { getMenuTrailWithPaths, menuTitle } from "@/utils/route";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const tagsStore = useTagsStore();
const themeStore = useThemeStore();

const collapsed = ref(false);
const selectedKeys = computed(() => [route.path]);
const openKeys = ref<string[]>([]);

watch(
  () => route.fullPath,
  () => {
    const trail = getMenuTrailWithPaths(authStore.menus, route.path);
    openKeys.value = trail.slice(0, -1).map((item) => item.fullPath);

    const menu = trail.at(-1)?.menu;
    tagsStore.ADD_TAG({
      label: menu ? menuTitle(menu) : String(route.meta.title || route.name || "页面"),
      value: route.path,
      query: route.query,
      meta: route.meta,
      close: true,
      name: route.name as string | undefined,
    });
  },
  { immediate: true },
);

function handleMenuClick({ key }: { key: string }): void {
  if (key && key !== route.path) {
    router.push(key);
  }
}

async function handleLogout(): Promise<void> {
  authStore.logout();
  await router.replace("/login");
}
</script>

<template>
  <a-layout class="app-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      :width="240"
      :collapsed-width="80"
      :trigger="null"
      collapsible
      theme="light"
      class="app-sider"
    >
      <div class="brand">
        <div class="brand__mark">A</div>
        <div v-if="!collapsed" class="brand__text">
          <strong>个人工作助理</strong>
          <span>Agent 平台</span>
        </div>
      </div>

      <a-menu
        v-model:open-keys="openKeys"
        :selected-keys="selectedKeys"
        mode="inline"
        class="app-menu"
        @click="handleMenuClick"
      >
        <MenuItem :menu-list="authStore.menus" :level="0" />
      </a-menu>

      <div class="sider-footer">
        <a-button type="text" block @click="collapsed = !collapsed">
          <MenuUnfoldOutlined v-if="collapsed" />
          <MenuFoldOutlined v-else />
          <span v-if="!collapsed">收起菜单</span>
        </a-button>
      </div>
    </a-layout-sider>

    <a-layout class="main-layout">
      <a-layout-header class="app-header">
        <BreadcrumbBar />
        <div class="header-actions">
          <a-tooltip :title="themeStore.mode === 'dark' ? '切换到浅色' : '切换到深色'">
            <a-button type="text" shape="circle" @click="themeStore.toggleTheme">
              <BulbOutlined v-if="themeStore.mode === 'dark'" />
              <BgColorsOutlined v-else />
            </a-button>
          </a-tooltip>
          <a-dropdown placement="bottomRight">
            <a-button type="text" class="user-button">
              <a-avatar size="small">
                <template #icon><UserOutlined /></template>
              </a-avatar>
              <span class="user-name">{{ authStore.displayName }}</span>
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item key="logout" @click="handleLogout">
                  <LogoutOutlined />
                  退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <div class="tags-slot">
        <TagsView />
      </div>

      <a-layout-content class="app-content">
        <RouterView />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #f5f7fb;
}

.app-sider {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 20;
  border-right: 1px solid #e5e7eb;
  box-shadow: 1px 0 10px rgb(15 23 42 / 4%);
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid #eef0f4;
}

.brand__mark {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  color: #fff;
  font-weight: 700;
  background: linear-gradient(135deg, #1d45dd, #6d5dfc);
  border-radius: 10px;
  place-items: center;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  white-space: nowrap;
}

.brand__text strong {
  font-size: 14px;
  color: #111827;
}

.brand__text span {
  font-size: 11px;
  color: #9ca3af;
}

.app-menu {
  height: calc(100vh - 110px);
  overflow-y: auto;
  border-inline-end: 0 !important;
}

.sider-footer {
  position: absolute;
  bottom: 0;
  width: 100%;
  padding: 8px;
  border-top: 1px solid #eef0f4;
}

.main-layout {
  min-height: 100vh;
  margin-left: 240px;
  transition: margin-left 0.2s ease;
}

.app-sider.ant-layout-sider-collapsed + .main-layout {
  margin-left: 80px;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.user-button {
  display: inline-flex;
  align-items: center;
  height: 36px;
}

.user-name {
  margin-left: 8px;
  color: #374151;
}

.tags-slot {
  background: #fff;
  border-bottom: 1px solid #eef0f4;
}

.app-content {
  min-height: calc(100vh - 100px);
  padding: 18px;
  overflow: auto;
  background: #f5f7fb;
}
</style>
