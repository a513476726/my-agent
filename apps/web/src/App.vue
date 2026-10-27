<script setup lang="ts">
import { RouterView } from "vue-router";

import { useThemeStore } from "@/stores/theme";

const themeStore = useThemeStore();
</script>

<template>
  <a-config-provider :theme="themeStore.antdTheme">
    <RouterView />
  </a-config-provider>
</template>
