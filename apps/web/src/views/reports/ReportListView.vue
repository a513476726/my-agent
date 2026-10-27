<script setup lang="ts">
import { onMounted, ref } from "vue";

import { listAllProjects } from "@/api/projects";
import { listReports } from "@/api/reports";
import type { Project, ReportRecord } from "@/api/types";
import ProTable from "@/components/ProTable";
import type { ProTableConfig } from "@/components/ProTable/types";
import { REPORT_KIND_OPTIONS } from "@/constants";
import { formatDateOnly, formatDateTime } from "@/utils/date-format";

const projects = ref<Project[]>([]);
const selectedProjectId = ref("");
const selectedKind = ref<string | undefined>();
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

const config: ProTableConfig<ReportRecord> = {
  rowKey: "id",
  size: "middle",
  scroll: { x: 1100 },
  fixedParams: () => ({
    project_id: selectedProjectId.value,
    kind: selectedKind.value,
  }),
  fetchApi: async (params) => {
    const projectId = String(params.project_id || "");
    if (!projectId) return { records: [], total: 0 };

    const page = Number(params.page || 1);
    const limit = Number(params.limit || 20);
    try {
      return await listReports({
        project_id: projectId,
        kind: params.kind as "daily" | "weekly" | "quarterly" | undefined,
        limit,
        offset: (page - 1) * limit,
      });
    } catch {
      return { records: [], total: 0 };
    }
  },
  columns: [
    { title: "报告标题", dataIndex: "title", width: 260, ellipsis: true },
    {
      title: "类型",
      dataIndex: "kind",
      width: 100,
      valueType: "tag",
      valueEnum: {
        daily: { text: "日报", status: "processing" },
        weekly: { text: "周报", status: "success" },
        quarterly: { text: "季报", status: "warning" },
      },
    },
    {
      title: "统计周期",
      dataIndex: "period",
      width: 240,
      render: (record) =>
        `${formatDateOnly(record.period?.start)} ~ ${formatDateOnly(record.period?.end)}`,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      valueType: "tag",
      valueEnum: {
        draft: { text: "草稿", status: "default" },
        ready: { text: "已生成", status: "success" },
        failed: { text: "失败", status: "error" },
      },
    },
    {
      title: "生成时间",
      dataIndex: "created_at",
      width: 180,
      render: (record) => formatDateTime(record.created_at),
    },
  ],
};

function refreshTable(): void {
  void tableRef.value?.search(true);
}
</script>

<template>
  <div class="table-page">
    <div class="page-header">
      <div>
        <h1 class="page-header__title">报告中心</h1>
        <p class="page-header__hint">按项目与报告类型筛选，统计周期来自数据库记录。</p>
      </div>
    </div>

    <a-card :bordered="false">
      <div class="filter-row">
        <span class="filter-row__label">项目</span>
        <a-select
          v-model:value="selectedProjectId"
          :loading="loadingProjects"
          style="width: 260px"
          placeholder="请选择项目"
          @change="refreshTable"
        >
          <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }}
          </a-select-option>
        </a-select>

        <span class="filter-row__label">类型</span>
        <a-select
          v-model:value="selectedKind"
          allow-clear
          style="width: 150px"
          placeholder="全部类型"
          @change="refreshTable"
        >
          <a-select-option v-for="item in REPORT_KIND_OPTIONS" :key="item.value" :value="item.value">
            {{ item.label }}
          </a-select-option>
        </a-select>
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
