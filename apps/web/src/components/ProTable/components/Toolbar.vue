<template>
  <div v-if="hasButtons || importantFields.length > 0" class="pro-table-toolbar">
    <!-- 左侧区域：关键筛选项 + 按钮 -->
    <div class="pro-table-toolbar__left">
      <!-- 关键筛选项（混合模式下由外部传入） -->
      <div v-if="importantFields.length > 0" class="pro-table-toolbar__important">
        <div
          v-for="field in importantFields"
          :key="field.field"
          class="pro-table-toolbar__important-item"
        >
          <SearchItem :label="field.label" :label-width="70">
            <component
              :is="getFieldComponent(field.name)"
              :model-value="searchParams[field.field]"
              :placeholder="field.placeholder"
              :options="field.options"
              :field-names="field.fieldNames"
              :remote-func="field.remoteFunc"
              :remote-format="field.remoteFormat"
              v-bind="field.props"
              :search-params="searchParams"
              :field="field.field"
              @update:model-value="(val: any) => handleImportantFieldChange(field.field, val)"
              @change="handleChange"
              @search-submit="handleSearch"
            />
          </SearchItem>
        </div>
      </div>

      <!-- 左侧按钮 -->
      <template v-for="button in visibleLeftButtons" :key="button.key">
        <a-button
          v-if="!button.isDefaultReport"
          :type="button.type || 'default'"
          :ghost="button.ghost"
          :danger="button.danger"
          :disabled="isButtonDisabled(button)"
          @click="handleButtonClick(button)"
        >
          <template v-if="button.icon" #icon>
            <component :is="button.icon" />
          </template>
          {{ button.text }}
        </a-button>
        <a-button
          v-else
          :type="button.type || 'default'"
          :ghost="button.ghost"
          :danger="button.danger"
          :disabled="isButtonDisabled(button)"
          @click="handleButtonClick(button)"
        >
          <template v-if="button.icon" #icon>
            <component :is="button.icon" />
          </template>
          {{ button.text }}
        </a-button>
      </template>
    </div>

    <!-- 右侧按钮 -->
    <div class="pro-table-toolbar__right">
      <template
        v-for="(item, index) in visibleRightButtons"
        :key="isVNode(item) ? `vnode-${index}` : item.key"
      >
        <a-button
          v-if="!isVNode(item)"
          :type="item.type || 'default'"
          :ghost="item.ghost"
          :danger="item.danger"
          :disabled="isButtonDisabled(item)"
          @click="handleButtonClick(item)"
        >
          <template v-if="item.icon" #icon>
            <component :is="item.icon" />
          </template>
          {{ item.text }}
        </a-button>
        <component :is="item" v-else />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, isVNode, markRaw } from 'vue'
import { FilterOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import SearchItem from './SearchBar/SearchItem.vue'
import { fieldComponents } from './SearchBar/fields'
import type { SearchFieldConfig } from '../types'
import type {
  ToolbarConfig,
  ToolbarButtonConfig,
  ProTableMethods,
  ShowButtonsMethod,
} from '../types'

interface Props {
  /** 工具栏配置 */
  config?: ToolbarConfig
  /** 选中的行数据 */
  selectedRows?: any[]
  /** 方法集合 */
  methods?: ProTableMethods
  /** 按钮显示控制方法 */
  showButtons?: ShowButtonsMethod
  /** 是否为报表模式 */
  reportMode?: boolean
  /** 关键筛选项（混合模式下由 SearchBar 传入，渲染在筛选项按钮左侧） */
  importantFields?: SearchFieldConfig[]
  /** 是否有弹窗筛选项（false 时隐藏默认"筛选项"按钮） */
  hasDialogFields?: boolean
  /** 搜索参数（用于绑定关键筛选项的值） */
  searchParams?: Record<string, any>
  /** 更新字段值回调（来自 SearchBar） */
  onFieldChange?: (field: string, value: any) => void
  /** 搜索回调 */
  onSearch?: () => void
  /** 字段变化回调 */
  onChange?: (payload: { field: string; value: any; searchParams: Record<string, any> }) => void
}

const props = withDefaults(defineProps<Props>(), {
  config: undefined,
  selectedRows: () => [],
  methods: undefined,
  showButtons: undefined,
  reportMode: false,
  importantFields: () => [],
  hasDialogFields: true, // 默认 true：未显式传入时保持原有行为（兼容现有调用）
  searchParams: () => ({}),
})

const emit = defineEmits<{
  'open-filter-dialog': []
  search: []
}>()

const authStore = useAuthStore()

/**
 * 获取按钮状态（显示/禁用）
 */
const getButtonStatus = (button: ToolbarButtonConfig) => {
  // 内置权限检查：通过 button.id 检查权限
  if (button.id && authStore.permissions[button.id] !== true) {
    return { show: false, disabled: true }
  }

  // 如果提供了 showButtons 方法，使用自定义逻辑
  if (props.showButtons) {
    return props.showButtons(button, props.selectedRows?.[0])
  }

  // 默认全部显示且启用
  return {
    show: true,
    disabled: false,
  }
}

/**
 * 判断按钮是否可见（通过 showButtons 控制）
 */
const isButtonVisible = (button: ToolbarButtonConfig): boolean => {
  // 优先使用 showButtons 方法
  const status = getButtonStatus(button)
  if (!status.show) return false

  // 检查 visible 属性
  if (button.visible === undefined) return true
  if (typeof button.visible === 'function') return button.visible()
  return button.visible
}

/**
 * 判断按钮是否禁用（通过 showButtons 控制）
 */
const isButtonDisabled = (button: ToolbarButtonConfig): boolean => {
  // 优先使用 showButtons 方法
  const status = getButtonStatus(button)
  if (status.disabled) return true

  // 需要选择行但没有选中
  if (button.needSelection && (!props.selectedRows || props.selectedRows.length === 0)) {
    return true
  }

  // 检查 disabled 属性
  if (button.disabled === undefined) return false
  if (typeof button.disabled === 'function') return button.disabled(props.selectedRows || [])
  return button.disabled
}

/**
 * 报表模式默认按钮
 */
const defaultReportButtons = computed((): ToolbarButtonConfig[] => {
  const reportConfig = props.config?.reportConfig
  const buttons: ToolbarButtonConfig[] = []

  // 当弹窗内没有筛选项时，隐藏"筛选项"按钮（避免点击打开空弹窗）
  const showFilterBtn = reportConfig?.showFilterButton !== false && props.hasDialogFields

  if (showFilterBtn) {
    buttons.push({
      key: '__report_filter__',
      text: reportConfig?.filterButtonText || '筛选项',
      type: 'default',
      icon: FilterOutlined,
      action: '__openFilterDialog__',
      isDefaultReport: true,
    })
  }

  if (reportConfig?.showSearchButton !== false) {
    buttons.push({
      key: '__report_search__',
      text: reportConfig?.searchButtonText || '查询',
      type: 'primary',
      icon: SearchOutlined,
      action: '__search__',
      isDefaultReport: true,
    })
  }

  return buttons
})

/**
 * 可见的左侧按钮（报表模式默认按钮在前，用户按钮在后）
 */
const visibleLeftButtons = computed(() => {
  const userButtons = (props.config?.leftButtons || []).filter(isButtonVisible)
  if (props.reportMode) {
    return [...defaultReportButtons.value, ...userButtons]
  }
  return userButtons
})

/**
 * 可见的右侧按钮（支持 VNode）
 */
const visibleRightButtons = computed(() => {
  return (props.config?.rightButtons || []).filter(item => {
    if (isVNode(item)) return true
    const button = item as ToolbarButtonConfig
    return isButtonVisible(button)
  })
})

/**
 * 是否有按钮
 */
const hasButtons = computed(() => {
  return visibleLeftButtons.value.length > 0 || visibleRightButtons.value.length > 0
})

/**
 * 处理按钮点击
 */
const handleButtonClick = (button: ToolbarButtonConfig) => {
  // 报表模式内置动作
  if (button.action === '__openFilterDialog__') {
    emit('open-filter-dialog')
    return
  }
  if (button.action === '__search__') {
    // 触发搜索通过 emit 通知父组件
    emit('search')
    return
  }

  // 如果有 action 且提供了 methods，调用对应方法
  if (button.action && props.methods && props.methods[button.action]) {
    props.methods[button.action](undefined, props.selectedRows)
  }
}

/**
 * 获取字段对应的组件
 */
const getFieldComponent = (name: string) => {
  const component = fieldComponents[name] || fieldComponents.input
  return markRaw(component)
}

/**
 * 关键筛选项值变化
 */
const handleImportantFieldChange = (field: string, value: any) => {
  props.onFieldChange?.(field, value)
}

/**
 * 搜索
 */
const handleSearch = () => {
  props.onSearch?.()
}

/**
 * 变化回调
 */
const handleChange = (payload: {
  field: string
  value: any
  searchParams: Record<string, any>
}) => {
  props.onChange?.(payload)
}
</script>

<style scoped lang="less">
.pro-table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;

  &__left {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__right {
    display: flex;
    gap: 8px;
  }

  // 关键筛选项容器
  &__important {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-right: 8px;

    &-item {
      display: inline-flex;
      align-items: center;
      min-width: 200px;
    }
  }
}
</style>
