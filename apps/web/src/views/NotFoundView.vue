<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <main class="not-found">
    <a-result status="404" title="404" sub-title="页面不存在或已被移除。">
      <template #extra>
        <a-button type="primary" @click="router.replace('/')">返回工作台</a-button>
      </template>
    </a-result>
  </main>
</template>

<style scoped>
.not-found {
  display: grid;
  min-height: 100vh;
  background: #f5f7fb;
  place-items: center;
}
</style>
