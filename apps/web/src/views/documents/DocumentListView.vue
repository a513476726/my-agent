<script setup lang="ts">
import { onMounted, ref } from "vue";

import { listDocuments } from "@/api/documents";
import { listAllProjects } from "@/api/projects";
import type { DocumentRecord, Project } from "@/api/types";
import ProTable from "@/components/ProTable";
import type { ProTableConfig } from "@/components/ProTable/types";
import { formatDateTime } from "@/utils/date-format";

const projects = ref<Project[]>([]);
const selectedProjectId = ref("");
const loadingProjects = ref(true);

const tableRef = ref<{ search: (reset?: boolean) => Promise<void> } | null>(null);

onMounted(async () => {
  try {
    projects.value = await listAllProjects();
    if (projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id;
    }
  } finally {
    loadingProjects.value = false;
  }
});

const config: ProTableConfig<DocumentRecord> = {
  rowKey: "id",
  size: "middle",
  scroll: { x: 1000 },
  fixedParams: () => ({ project_id: selectedProjectId.value }),
  fetchApi: async (params) => {
    const projectId = String(params.project_id || "");
    if (!projectId) return { records: [], total: 0 };

    const page = Number(params.page || 1);
    const limit = Number(params.limit || 20);
    try {
      return await listDocuments({
        project_id: projectId,
        limit,
        offset: (page - 1) * limit,
      });
    } catch {
      return { records: [], total: 0 };
    }
  },
  columns: [
    { title: "文档标题", dataIndex: "title", width: 220, ellipsis: true },
    { title: "来源路径", dataIndex: "source_path", width: 340, ellipsis: true },
    { title: "版本", dataIndex: "version", width: 120, ellipsis: true },
    {
      title: "解析状态",
      dataIndex: "status",
      width: 120,
      valueType: "tag",
      valueEnum: {
        pending: { text: "待处理", status: "default" },
        indexed: { text: "已入库", status: "success" },
        failed: { text: "失败", status: "error" },
      },
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      width: 180,
      render: (record) => formatDateTime(record.updated_at),
    },
  ],
};

function handleProjectChange(): void {
  void tableRef.value?.search(true);
}
</script>

<template>
  <div class="table-page">
    <div class="page-header">
      <div>
        <h1 class="page-header__title">文档管理</h1>
        <p class="page-header__hint">文档按项目隔离，列表先选择项目再查询。</p>
      </div>
    </div>

    <a-card :bordered="false">
      <div class="filter-row">
        <span class="filter-row__label">项目</span>
        <a-select
          v-model:value="selectedProjectId"
          :loading="loadingProjects"
          style="width: 280px"
          placeholder="请选择项目"
          @change="handleProjectChange"
        >
          <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }}
          </a-select-option>
        </a-select>
        <a-tag v-if="!loadingProjects" color="blue">{{ projects.length }} 个项目</a-tag>
      </div>

      <a-empty v-if="!loadingProjects && projects.length === 0" description="暂无项目，请先创建项目" />
      <ProTable
        v-else-if="selectedProjectId"
        :key="selectedProjectId"
        ref="tableRef"
        :config="config"
      />
    </a-card>
  </div>
</template>
