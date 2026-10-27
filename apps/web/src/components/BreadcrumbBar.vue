<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { getMenuTrailWithPaths } from "@/utils/route";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const breadcrumbs = computed(() => {
  if (route.path === "/") {
    return [{ title: "工作台", path: "/" }];
  }

  const trail = getMenuTrailWithPaths(authStore.menus, route.path);
  if (trail.length > 0) {
    return trail.map((item) => ({ title: item.title, path: item.fullPath }));
  }

  const matched = route.matched
    .filter((record) => record.meta?.title)
    .map((record) => ({ title: String(record.meta.title), path: record.path }));
  return matched.length > 0 ? matched : [{ title: String(route.meta.title || "页面"), path: route.path }];
});

function handleClick(path: string): void {
  if (path && path !== route.path) {
    router.push(path);
  }
}
</script>

<template>
  <a-breadcrumb class="breadcrumb-bar">
    <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
      <a class="breadcrumb-link" @click.prevent="handleClick(item.path)">{{ item.title }}</a>
    </a-breadcrumb-item>
  </a-breadcrumb>
</template>

<style scoped>
.breadcrumb-bar {
  font-size: 13px;
}

.breadcrumb-link {
  color: #6b7280;
  cursor: pointer;
}

.breadcrumb-link:hover {
  color: #1d45dd;
}
</style>
