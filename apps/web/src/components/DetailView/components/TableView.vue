<template>
  <div class="detail-table">
    <a-table
      :columns="resolvedColumns"
      :data-source="tableData"
      :pagination="paginationConfig"
      :scroll="config.scroll || { x: 'max-content' }"
      :show-overflow-tooltip="true"
      :bordered="config.bordered !== false"
      :size="config.size || 'middle'"
      :show-header="config.showHeader !== false"
      :row-class-name="config.rowClassName"
      :row-key="config.rowKey || 'id'"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DetailTableColumn } from '../types'
import { formatMoney } from '../utils'

interface Props {
  config: {
    columns: DetailTableColumn[]
    dataField?: string
    pagination?: boolean | { pageSize?: number }
    bordered?: boolean
    size?: 'small' | 'middle' | 'large'
    scroll?: { x?: number | string; y?: number | string }
    showHeader?: boolean
    rowClassName?: (record: Record<string, unknown>, index: number) => string
    rowKey?: string
  }
  data: Record<string, unknown>
}

const props = defineProps<Props>()

const tableData = computed(() => {
  if (props.config.dataField) {
    return (props.data[props.config.dataField] as Record<string, unknown>[]) || []
  }
  return props.data as unknown as Record<string, unknown>[]
})

const paginationConfig = computed(() => {
  if (props.config.pagination === false) return false
  if (props.config.pagination === true) return {}
  return props.config.pagination || false
})

// 处理列配置：序号列、格式化列、自定义渲染列、其他列
const resolvedColumns = computed(() =>
  props.config.columns.map(col => {
    // 序号列：注入 customRender 显示序号
    if (col.key === 'index') {
      return {
        ...col,
        align: col.align || 'center',
        customRender: ({ index }: { index: number }) => index + 1,
      }
    }
    // 自定义渲染列：优先使用传入的 render 函数
    if (col.render) {
      return {
        ...col,
        ellipsis: col.ellipsis !== undefined ? col.ellipsis : false,
        customRender: ({
          text,
          record,
          index,
        }: {
          text: unknown
          record: Record<string, unknown>
          index: number
        }) => {
          return col.render!(text, record, index)
        },
      }
    }
    // 金额列：注入 customRender 格式化千分符
    if (col.format === 'money') {
      return {
        ...col,
        align: col.align || 'right',
        ellipsis: col.ellipsis !== undefined ? col.ellipsis : false,
        customRender: ({ text }: { text: unknown }) => formatMoney(text),
      }
    }
    // 其他列：默认 ellipsis: true，外部传入则使用外部的值
    return {
      ...col,
      ellipsis: col.ellipsis !== undefined ? col.ellipsis : true,
      customRender: col.customRender || (({ text }: { text: unknown }) => text ?? '--'),
    }
  })
)
</script>

<style lang="less">
.detail-table {
  overflow-x: auto;
  // 确保表格在弹窗内水平滚动
  :deep(.ant-table) {
    max-width: 100%;
  }
  // 富文本单元格样式
  :deep(.rich-text-cell) {
    max-height: 200px;
    overflow-y: auto;
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.6;
    img {
      max-width: 100%;
      height: auto;
    }
    p {
      margin: 0 0 4px 0;
    }
  }
}
</style>
