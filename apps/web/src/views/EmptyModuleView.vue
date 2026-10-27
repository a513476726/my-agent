<script setup lang="ts">
import { useRoute } from "vue-router";

const route = useRoute();
</script>

<template>
  <a-card :bordered="false" class="empty-module">
    <a-result
      status="info"
      :title="String(route.meta.title || '功能建设中')"
      sub-title="该模块将在后续阶段接入真实数据与操作能力。"
    >
      <template #extra>
        <a-tag color="blue">P3 空壳页</a-tag>
      </template>
    </a-result>
  </a-card>
</template>

<style scoped>
.empty-module {
  min-height: calc(100vh - 190px);
}
</style>
