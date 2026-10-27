<script setup lang="ts">
import type { ProTableConfig } from "@/components/ProTable/types";
import ProTable from "@/components/ProTable";
import { listProjects } from "@/api/projects";
import type { Project } from "@/api/types";
import { formatDateTime } from "@/utils/date-format";

const config: ProTableConfig<Project> = {
  rowKey: "id",
  size: "middle",
  scroll: { x: 1000 },
  search: {
    fields: [
      {
        field: "enabled",
        label: "状态",
        name: "select",
        placeholder: "全部状态",
        important: true,
        options: [
          { label: "启用", value: true },
          { label: "停用", value: false },
        ],
      },
    ],
    showReset: true,
    showSearch: true,
  },
  fetchApi: async (params) => {
    const page = Number(params.page || 1);
    const limit = Number(params.limit || 20);
    const enabled =
      params.enabled === true || params.enabled === "true"
        ? true
        : params.enabled === false || params.enabled === "false"
          ? false
          : undefined;

    try {
      return await listProjects({ limit, offset: (page - 1) * limit, enabled });
    } catch {
      return { records: [], total: 0 };
    }
  },
  columns: [
    { title: "项目名称", dataIndex: "name", width: 180, ellipsis: true },
    { title: "仓库路径", dataIndex: "path", width: 300, ellipsis: true },
    {
      title: "版本控制",
      dataIndex: "vcs_type",
      width: 110,
      valueType: "tag",
      valueEnum: {
        git: { text: "Git", status: "processing" },
        svn: { text: "SVN", status: "warning" },
        none: { text: "无", status: "default" },
      },
    },
    {
      title: "状态",
      dataIndex: "enabled",
      width: 100,
      valueType: "tag",
      valueEnum: {
        true: { text: "启用", status: "success" },
        false: { text: "停用", status: "default" },
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
</script>

<template>
  <div class="table-page">
    <div class="page-header">
      <div>
        <h1 class="page-header__title">项目管理</h1>
        <p class="page-header__hint">项目路径与启用状态决定定时任务和上下文范围。</p>
      </div>
      <a-tag color="blue">按启用状态筛选</a-tag>
    </div>
    <ProTable :config="config" />
  </div>
</template>
