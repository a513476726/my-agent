<template>
  <a-select
    :value="modelValue"
    allow-clear
    :dropdown-match-select-width="false"
    :dropdown-style="{ minWidth: 'var(--search-item-width, 100%)' }"
    :get-popup-container="(triggerNode: any) => triggerNode.parentElement?.parentElement"
    :style="{ width: '100%' }"
    :loading="loading"
    v-bind="selectProps"
    :disabled="resolvedDisabled"
    @update:value="handleChange"
  >
    <a-select-option v-for="option in normalizedOptions" :key="option.value" :value="option.value">
      {{ option.label }}
    </a-select-option>
  </a-select>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface Option {
  label: string
  value: any
}

interface Props {
  modelValue: any
  placeholder?: string
  options?: Record<string, any>[]
  fieldNames?: { label: string; value: string }
  props?: Record<string, any>
  disabled?: boolean
  /** SearchBar 的完整搜索参数（响应式），用于读取上级字段值 */
  searchParams?: Record<string, any>
  /** 当前组件在 search.fields 中的 field 名 */
  field?: string
  /** 级联上级字段名（来自 field.props.parentField），上级值变化时清空当前值并重新加载 */
  parentField?: string
  /** 上级字段必须匹配的值（来自 field.props.parentField），仅当上级值等于此值时触发加载 */
  parentValueRequired?: any
  /** 远程获取选项的接口函数，接收上级字段值作为参数 */
  remoteFunc?: (parentValue?: any) => Promise<any[]>
  /** 接口返回后的数据格式化函数，接收原始数据数组，返回 Option[] */
  remoteFormat?: (data: any[]) => Option[]
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择',
  options: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: any]
  /** 向 SearchBar 通知字段变化（用于级联清除等场景） */
  change: [payload: { field: string; value: any; searchParams: Record<string, any> }]
}>()

const loading = ref(false)
const remoteOptions = ref<Option[]>([])

/** 上级字段的当前选中值 */
const parentValue = computed(() => {
  if (!props.parentField || !props.searchParams) return undefined
  return props.searchParams[props.parentField]
})

/**
 * 禁用状态：
 * 1. props.disabled 显式传入时使用
 * 2. parentField 指定但上级值不满足条件时自动禁用
 */
const resolvedDisabled = computed(() => {
  if (props.disabled !== undefined) {
    return props.disabled
  }
  if (props.props?.disabled !== undefined) {
    return props.props?.disabled
  }
  // 级联场景：parentField 指定但上级无值时禁用
  if (props.parentField && !parentValue.value) {
    return true
  }
  // parentValueRequired 指定但上级值不匹配时禁用
  if (props.parentValueRequired !== undefined && parentValue.value !== props.parentValueRequired) {
    return true
  }
  return false
})

/**
 * 提取 select 组件需要的 props
 */
const selectProps = computed(() => {
  const {
    options: _options,
    fieldNames: _fieldNames,
    remoteFunc: _remoteFunc,
    remoteFormat: _remoteFormat,
    ...rest
  } = props
  return rest
})

/**
 * 规范化选项数据
 * 优先级：remoteOptions > options
 */
const normalizedOptions = computed<Option[]>(() => {
  if (remoteOptions.value.length > 0) {
    return remoteOptions.value
  }

  if (!props.options || props.options.length === 0) {
    return []
  }

  // 检查是否已经是标准格式
  const firstItem = props.options[0]
  if ('label' in firstItem && 'value' in firstItem) {
    return props.options as Option[]
  }

  // 使用 fieldNames 进行映射
  if (props.fieldNames) {
    const { label: labelKey, value: valueKey } = props.fieldNames
    return props.options.map(item => ({
      label: String(item[labelKey] ?? ''),
      value: item[valueKey],
    }))
  }

  return []
})

/**
 * 远程获取选项数据，传入上级字段值（级联场景）
 * 若 parentValueRequired 指定但上级值不匹配，跳过请求并清空选项
 */
async function fetchRemoteOptions() {
  if (!props.remoteFunc) return

  // parentValueRequired 条件不满足时，跳过请求
  if (props.parentValueRequired !== undefined && parentValue.value !== props.parentValueRequired) {
    remoteOptions.value = []
    return
  }

  loading.value = true
  try {
    const data = await props.remoteFunc(parentValue.value)
    if (props.remoteFormat) {
      remoteOptions.value = props.remoteFormat(data)
    } else {
      // 默认格式化：假设返回的是 { label, value } 数组
      remoteOptions.value = (data as Option[]).map(item => {
        if ('label' in item && 'value' in item) {
          return item
        }
        const labelKey = props.fieldNames?.label || 'label'
        const valueKey = props.fieldNames?.value || 'value'
        return {
          label: String(item[labelKey] ?? ''),
          value: item[valueKey],
        }
      })
    }
  } catch (error) {
    console.error('[SearchAsyncSelect] 获取选项失败:', error)
    remoteOptions.value = []
  } finally {
    loading.value = false
  }
}

/**
 * 监听 remoteFunc 变化，自动获取数据
 */
watch(
  () => props.remoteFunc,
  () => {
    fetchRemoteOptions()
  },
  { immediate: true }
)

/**
 * 级联场景：上级字段值变化时，清空当前值并重新加载选项
 */
watch(parentValue, (newVal, oldVal) => {
  if (!props.parentField) return
  // 只在值真正变化时处理（非初始化）
  if (newVal === oldVal) return
  // 清空当前选中值
  remoteOptions.value = []
  emit('update:modelValue', undefined)
  emit('change', {
    field: props.field || '',
    value: undefined,
    searchParams: props.searchParams || {},
  })
  // 重新加载选项（传入新的上级值）
  fetchRemoteOptions()
})

/**
 * 监听 options 变化，更新 remoteOptions
 */
watch(
  () => props.options,
  () => {
    remoteOptions.value = []
  }
)

const handleChange = (val: any) => {
  emit('update:modelValue', val)
  emit('change', {
    field: props.field || '',
    value: val,
    searchParams: props.searchParams || {},
  })
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
