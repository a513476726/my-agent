<script setup lang="ts">
import { RouterView } from "vue-router";

import { appTheme } from "@/config/theme";
</script>

<template>
  <a-config-provider :theme="appTheme">
    <RouterView />
  </a-config-provider>
</template>
