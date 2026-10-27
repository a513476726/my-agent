<template>
  <div ref="containerRef" class="pro-table-search">
    <!-- inline 模式 -->
    <a-row v-if="searchMode !== 'dialog'" :gutter="12">
      <template v-for="field in config.fields" :key="field.field">
        <a-col
          v-show="!isFieldHidden(field.field)"
          :xs="getColSpan(field, 'xs')"
          :sm="getColSpan(field, 'sm')"
          :md="getColSpan(field, 'md')"
          :lg="getColSpan(field, 'lg')"
          :xl="getColSpan(field, 'xl')"
          :xxl="getColSpan(field, 'xxl')"
          class="pb-2"
        >
          <SearchItem :label="field.label" :label-width="70">
            <component
              :is="getFieldComponent(field.name)"
              :model-value="modelValue[field.field]"
              :placeholder="field.placeholder"
              :options="field.options"
              :field-names="field.fieldNames"
              :remote-func="field.remoteFunc"
              :remote-format="field.remoteFormat"
              v-bind="field.props"
              :search-params="modelValue"
              :field="field.field"
              @update:model-value="(val: any) => handleFieldChange(field.field, val)"
              @change="handleChange"
              @search-submit="handleSearch"
            />
          </SearchItem>
        </a-col>
      </template>

      <a-col v-bind="baseColSpans" class="pb-2" :style="{ order: 999 }">
        <div class="pro-table-search__actions">
          <a-space>
            <a-button v-if="showCollapseButton" type="link" @click="toggleCollapse">
              {{ collapsed ? '更多' : '收起' }}
              <DownOutlined v-if="collapsed" class="icon-spacing" />
              <UpOutlined v-else class="icon-spacing" />
            </a-button>
            <a-button v-if="showSearch" type="primary" @click="handleSearch">
              <template #icon>
                <SearchOutlined />
              </template>
              查询
            </a-button>
            <a-button v-if="showReset" @click="handleReset">清空</a-button>
          </a-space>
        </div>
      </a-col>
    </a-row>

    <!-- dialog 模式：筛选按钮触发弹窗 -->
    <!-- 纯弹窗模式：无关键筛选时显示筛选按钮 -->
    <div v-if="isPureDialogMode" class="pro-table-search__pure-dialog">
      <a-button type="primary" @click="openDialog">
        <template #icon>
          <FilterOutlined />
        </template>
        筛选
      </a-button>
    </div>

    <!-- 弹窗内容：dialogFields（排除关键筛选后的字段） -->
    <a-modal
      v-if="searchMode === 'dialog'"
      v-model:open="dialogVisible"
      title="筛选项"
      :width="dialogWidth"
      :footer="null"
      @cancel="dialogVisible = false"
    >
      <div class="pro-table-search__dialog-content">
        <a-row :gutter="12">
          <template v-for="field in dialogFields" :key="field.field">
            <a-col
              :xs="getColSpan(field, 'xs')"
              :sm="getColSpan(field, 'sm')"
              :md="getColSpan(field, 'md')"
              :lg="getColSpan(field, 'lg')"
              :xl="getColSpan(field, 'xl')"
              :xxl="getColSpan(field, 'xxl')"
              class="pb-2"
            >
              <SearchItem :label="field.label" :label-width="70">
                <component
                  :is="getFieldComponent(field.name)"
                  :model-value="modelValue[field.field]"
                  :placeholder="field.placeholder"
                  :options="field.options"
                  :field-names="field.fieldNames"
                  :remote-func="field.remoteFunc"
                  :remote-format="field.remoteFormat"
                  v-bind="field.props"
                  :search-params="modelValue"
                  :field="field.field"
                  @update:model-value="(val: any) => handleFieldChange(field.field, val)"
                  @change="handleChange"
                  @search-submit="handleSearch"
                />
              </SearchItem>
            </a-col>
          </template>
        </a-row>
      </div>
      <div class="pro-table-search__dialog-footer">
        <a-space>
          <a-button @click="handleReset">重置</a-button>
          <a-button type="primary" @click="handleDialogSearch">查询</a-button>
        </a-space>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw } from 'vue'
import { SearchOutlined, DownOutlined, UpOutlined, FilterOutlined } from '@ant-design/icons-vue'
import { useWindowSize } from '@vueuse/core'
import SearchItem from './SearchItem.vue'
import { fieldComponents } from './fields'
import type { SearchConfig, SearchFieldConfig } from '../../types'

interface Props {
  config: SearchConfig
  modelValue: Record<string, any>
  /** 筛选项展示模式：inline 内联展示，dialog 弹窗展示 */
  searchMode?: 'inline' | 'dialog'
}

const props = withDefaults(defineProps<Props>(), {
  searchMode: 'inline',
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  search: []
  reset: []
  /** 任意字段变化时触发，携带完整 searchParams，业务组件可据此监听联动逻辑 */
  change: [payload: { field: string; value: any; searchParams: Record<string, any> }]
}>()

const containerRef = ref<HTMLElement | null>(null)
const { width: windowWidth } = useWindowSize()

const collapsed = ref(true)
const dialogVisible = ref(false)

const dialogWidth = computed(() => `${(windowWidth.value * 80) / 100}px`)

// 动态列数：窗口越宽，每行可放置的筛选项越多
const _dialogColSpans = computed(() => {
  const w = windowWidth.value
  if (w >= 1600) return { xs: 24, sm: 12, md: 8, lg: 6, xl: 6, xxl: 4 } // 超大屏每行4个
  if (w >= 1200) return { xs: 24, sm: 12, md: 8, lg: 8, xl: 6, xxl: 4 } // 大屏每行3个
  if (w >= 992) return { xs: 24, sm: 12, md: 12, lg: 8, xl: 8, xxl: 6 } // 中屏每行2个
  if (w >= 768) return { xs: 24, sm: 12, md: 12, lg: 12, xl: 12, xxl: 8 } // 小屏每行1-2个
  return { xs: 24, sm: 24, md: 24, lg: 24, xl: 24, xxl: 24 } // 超小屏每行1个
})

const showSearch = computed(() => props.config.showSearch !== false)

const showReset = computed(() => props.config.showReset !== false)

const collapseThreshold = computed(() => props.config.collapseThreshold ?? 3)

/**
 * 关键筛选项（常驻显示，不进入弹窗）
 */
const importantFields = computed(() => {
  const count = props.config.importantCount ?? 2
  return props.config.fields.filter(f => f.important === true).slice(0, count)
})

/**
 * 弹窗内的筛选项（排除关键的）
 */
const dialogFields = computed(() => {
  const importantFieldNames = new Set(importantFields.value.map(f => f.field))
  return props.config.fields.filter(f => !importantFieldNames.has(f.field))
})

/**
 * 纯弹窗模式（无关键筛选）
 */
const isPureDialogMode = computed(() => {
  return props.searchMode === 'dialog' && importantFields.value.length === 0
})

const showCollapseButton = computed(() => {
  if (!props.config.fields || props.config.fields.length === 0) {
    return false
  }

  // 如果字段数量小于等于阈值，直接不显示折叠按钮
  if (props.config.fields.length <= collapseThreshold.value) {
    return false
  }

  // 计算所有字段的总栅格占用
  const breakpoint = getCurrentBreakpoint()
  const buttonSpan = buttonColSpans[breakpoint]
  const availableSpace = 24 - buttonSpan // 需要减去按钮栅格

  let totalSpan = 0
  for (const field of props.config.fields) {
    totalSpan += getFieldGridSpan(field)
  }

  const needCollapse = totalSpan > availableSpace

  // 🐛 调试日志（仅开发环境）
  if (import.meta.env.DEV) {
    // console.log('[SearchBar] 折叠按钮显示判断', {
    //   breakpoint,
    //   fieldCount: props.config.fields.length,
    //   collapseThreshold: collapseThreshold.value,
    //   buttonSpan,
    //   availableSpace,
    //   totalSpan,
    //   needCollapse,
    //   fields: props.config.fields.map(f => ({
    //     field: f.field,
    //     span: f.span ?? 1,
    //     gridSpan: getFieldGridSpan(f),
    //   })),
    // })
  }

  return needCollapse
})

const baseColSpans: Record<string, number> = {
  xs: 12,
  sm: 12,
  md: 8,
  lg: 8,
  xl: 6,
  xxl: 4,
}

const buttonColSpans: Record<string, number> = {
  xs: 12,
  sm: 12,
  md: 8,
  lg: 8,
  xl: 6,
  xxl: 4,
}

/**
 * 获取当前断点
 */
const getCurrentBreakpoint = (): string => {
  if (windowWidth.value < 576) return 'xs'
  if (windowWidth.value < 768) return 'sm'
  if (windowWidth.value < 992) return 'md'
  if (windowWidth.value < 1200) return 'lg'
  if (windowWidth.value < 1600) return 'xl'
  return 'xxl'
}

/**
 * 获取当前断点下，字段可用的栅格空间
 * 折叠状态：24 - 按钮栅格（确保按钮组在第一行）
 * 展开状态：24（按钮组会自动换行到最后）
 */
const getAvailableGridSpace = (): number => {
  const breakpoint = getCurrentBreakpoint()
  const buttonSpan = buttonColSpans[breakpoint]

  // 🔑 折叠时减去按钮栅格，确保按钮组在同一行
  if (collapsed.value) {
    return 24 - buttonSpan
  }

  // 展开时按钮组会自动换行，字段可用整行空间
  return 24
}

/**
 * 计算字段在当前断点下占用的栅格数
 */
const getFieldGridSpan = (field: SearchFieldConfig): number => {
  const breakpoint = getCurrentBreakpoint()
  const span = field.span ?? 1
  const baseSpan = baseColSpans[breakpoint]
  return baseSpan * span
}

/**
 * 判断字段是否应该被隐藏（折叠状态下）
 * 基于栅格累加计算，确保按钮组在第一行
 */
const isFieldHidden = (field: string): boolean => {
  // 如果不显示折叠按钮，所有字段都可见
  if (!showCollapseButton.value) return false

  // 如果未折叠，所有字段都可见
  if (!collapsed.value) return false

  // 获取可用栅格空间（已减去按钮栅格）
  const availableSpace = getAvailableGridSpace()

  // 累加字段占用的栅格数
  let accumulatedSpan = 0

  for (const f of props.config.fields) {
    const fieldSpan = getFieldGridSpan(f)

    // 检查当前字段是否会超出可用空间
    if (accumulatedSpan + fieldSpan > availableSpace) {
      // 🐛 调试日志（仅开发环境）
      if (import.meta.env.DEV && f.field === field) {
        // console.log(`[SearchBar] 字段 "${field}" 被隐藏`, {
        //   breakpoint: getCurrentBreakpoint(),
        //   availableSpace,
        //   accumulatedSpan,
        //   fieldSpan,
        //   totalNeeded: accumulatedSpan + fieldSpan,
        //   reason: '超出可用空间',
        // })
      }

      // 如果是目标字段，返回 true（隐藏）
      if (f.field === field) {
        return true
      }
      // 后续所有字段都隐藏
      continue
    }

    // 累加栅格数
    accumulatedSpan += fieldSpan

    // 如果是目标字段且未超出空间，返回 false（可见）
    if (f.field === field) {
      // 🐛 调试日志（仅开发环境）
      if (import.meta.env.DEV) {
        // console.log(`[SearchBar] 字段 "${field}" 可见`, {
        //   breakpoint: getCurrentBreakpoint(),
        //   availableSpace,
        //   accumulatedSpan,
        //   fieldSpan,
        //   remainingSpace: availableSpace - accumulatedSpan,
        // })
      }
      return false
    }
  }

  // 默认隐藏（理论上不会到达这里）
  return true
}

const getColSpan = (field: SearchFieldConfig, breakpoint: string): number => {
  const span = field.span ?? 1
  return baseColSpans[breakpoint] * span
}

const getFieldComponent = (name: string) => {
  const component = fieldComponents[name] || fieldComponents.input
  return markRaw(component)
}

/**
 * 统一 change 事件处理器，转发变化给所有业务组件
 */
const handleChange = (payload: {
  field: string
  value: any
  searchParams: Record<string, any>
}) => {
  emit('change', payload)
}

const handleFieldChange = (field: string, value: any) => {
  // cascadeSelect 传入 { field, value } 格式，同时更新多个字段
  if (typeof field === 'object' && field !== null && 'field' in field) {
    const { field: f, value: v } = field as { field: string; value: any }
    const trimmed = typeof v === 'string' ? v.trim() : v
    Object.assign(props.modelValue, { [f]: trimmed })
    emit('update:modelValue', props.modelValue)
    emit('change', { field: f, value: trimmed, searchParams: props.modelValue })
    return
  }
  // 普通字段
  const trimmed = typeof value === 'string' ? value.trim() : value
  Object.assign(props.modelValue, { [field]: trimmed })
  emit('update:modelValue', props.modelValue)
  emit('change', { field, value: trimmed, searchParams: props.modelValue })
}

const toggleCollapse = () => {
  collapsed.value = !collapsed.value
}

const handleSearch = () => {
  emit('search')
}

const handleReset = () => {
  const resetValue: Record<string, any> = {}
  props.config.fields.forEach(field => {
    resetValue[field.field] = field.defaultValue ?? undefined
  })
  emit('update:modelValue', resetValue)
  emit('reset')
}

/**
 * 打开筛选弹窗（供外部调用）
 */
const openDialog = () => {
  dialogVisible.value = true
}

/**
 * 弹窗模式查询：触发搜索并关闭弹窗
 */
const handleDialogSearch = () => {
  dialogVisible.value = false
  emit('search')
}

// 暴露方法给父组件（Toolbar）调用
defineExpose({
  openDialog,
  /** 关键筛选项配置（混合模式下由 Toolbar 渲染在筛选项按钮左侧） */
  importantFields,
  /** 弹窗内筛选项配置（用于 Toolbar 决定是否显示"筛选项"按钮） */
  dialogFields,
  /** 当前搜索参数（双向绑定） */
  searchParams: props.modelValue,
  /** 更新字段值 */
  handleFieldChange,
  /** 触发搜索 */
  handleSearch,
  /** 重置 */
  handleReset,
})
</script>

<style scoped lang="less">
.pro-table-search {
  // 确保 Row 使用 flex 布局，order 属性才能生效
  :deep(.ant-row) {
    display: flex;
    flex-wrap: wrap;
  }

  &__actions {
    display: flex;
    align-items: flex-end;
    height: 100%;
  }

  :deep(.ant-select-single .ant-select-selector .ant-select-selection-search) {
    left: 0;
  }
}

.icon-spacing {
  margin-left: 4px;
}

.pro-table-search__dialog-content {
  padding: 16px 0;
}

.pro-table-search__dialog-footer {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
}

.pro-table-search__pure-dialog {
  display: inline-block;
}
</style>
