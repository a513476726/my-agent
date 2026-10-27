<script setup lang="ts">
import { CheckCircleOutlined, DatabaseOutlined, FolderOpenOutlined, FileTextOutlined } from "@ant-design/icons-vue";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { getHealth } from "@/api/health";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const serviceStatus = ref<"checking" | "ok" | "down">("checking");
const databaseStatus = ref("未知");

const shortcuts = [
  { title: "项目管理", description: "登记被分析仓库与启用状态", path: "/project-space/projects", icon: FolderOpenOutlined },
  { title: "文档管理", description: "查看已入库文档与解析状态", path: "/project-space/documents", icon: FileTextOutlined },
  { title: "报告中心", description: "按项目和周期阅读报告", path: "/project-space/reports", icon: DatabaseOutlined },
];

onMounted(async () => {
  try {
    const health = await getHealth();
    serviceStatus.value = health.status === "ok" ? "ok" : "down";
    databaseStatus.value = health.database || "未知";
  } catch {
    serviceStatus.value = "down";
  }
});
</script>

<template>
  <div class="home-page">
    <section class="welcome-panel">
      <div>
        <p class="eyebrow">PERSONAL WORK AGENT</p>
        <h1>{{ authStore.displayName }}，欢迎回来</h1>
        <p>从项目上下文出发，逐步接入文档检索、代码回顾、报告与能力沉淀。</p>
      </div>
      <div class="service-status">
        <a-badge :status="serviceStatus === 'ok' ? 'success' : serviceStatus === 'down' ? 'error' : 'processing'" />
        <span>API {{ serviceStatus === "ok" ? "正常" : serviceStatus === "down" ? "不可用" : "检查中" }}</span>
        <span class="status-separator">/</span>
        <span>数据库 {{ databaseStatus }}</span>
      </div>
    </section>

    <a-row :gutter="[16, 16]">
      <a-col v-for="item in shortcuts" :key="item.path" :xs="24" :md="8">
        <a-card :bordered="false" hoverable class="shortcut-card" @click="router.push(item.path)">
          <component :is="item.icon" class="shortcut-icon" />
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </a-card>
      </a-col>
    </a-row>

    <a-card :bordered="false" class="roadmap-card">
      <template #title>初始化进度</template>
      <a-steps :current="3" size="small">
        <a-step title="基础设施" status="finish" />
        <a-step title="数据层" status="finish" />
        <a-step title="后端骨架" status="finish" />
        <a-step title="前端工作台" status="process" />
        <a-step title="契约生成" />
      </a-steps>
      <div class="roadmap-note">
        <CheckCircleOutlined />
        当前聚焦前端裁剪复用、登录与菜单、项目/文档/报告列表，后续再进入知识库与智能体能力。
      </div>
    </a-card>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.welcome-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: flex-end;
  justify-content: space-between;
  padding: 28px;
  color: #fff;
  background:
    radial-gradient(circle at 90% 10%, rgb(255 255 255 / 20%), transparent 32%),
    linear-gradient(135deg, #1d45dd, #5b4ee8 58%, #7c3aed);
  border-radius: 18px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  letter-spacing: 1.6px;
  opacity: 0.72;
}

.welcome-panel h1 {
  margin: 0 0 8px;
  font-size: 30px;
}

.welcome-panel p:last-child {
  margin: 0;
  color: rgb(255 255 255 / 78%);
}

.service-status {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 12px;
  font-size: 12px;
  background: rgb(255 255 255 / 12%);
  border: 1px solid rgb(255 255 255 / 18%);
  border-radius: 999px;
}

.status-separator {
  opacity: 0.4;
}

.shortcut-card {
  height: 100%;
  border-radius: 14px;
}

.shortcut-icon {
  margin-bottom: 18px;
  font-size: 28px;
  color: #1d45dd;
}

.shortcut-card h3 {
  margin: 0 0 8px;
  font-size: 17px;
}

.shortcut-card p {
  margin: 0;
  color: #6b7280;
  line-height: 1.65;
}

.roadmap-card {
  border-radius: 14px;
}

.roadmap-note {
  display: flex;
  gap: 8px;
  align-items: center;
  padding-top: 18px;
  margin-top: 20px;
  color: #6b7280;
  border-top: 1px solid #f0f1f5;
}
</style>
