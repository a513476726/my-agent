<template>
  <a-select
    :value="modelValue"
    allow-clear
    :dropdown-match-select-width="false"
    :dropdown-style="{ minWidth: 'var(--search-item-width, 100%)' }"
    :get-popup-container="(triggerNode: any) => triggerNode.parentElement?.parentElement"
    :style="{ width: '100%' }"
    v-bind="selectProps"
    @update:value="handleChange"
  >
    <a-select-option v-for="option in normalizedOptions" :key="option.value" :value="option.value">
      {{ option.label }}
    </a-select-option>
  </a-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Option {
  label: string
  value: any
}

interface FieldNames {
  label: string
  value: string
}

interface Props {
  modelValue: any
  placeholder?: string
  options?: Record<string, any>[]
  fieldNames?: FieldNames
  props?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择',
  options: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: any]
}>()

/**
 * 提取 select 组件需要的 props（排除 options 和 fieldNames）
 */
const selectProps = computed(() => {
  const { options: _options, fieldNames: _fieldNames, ...rest } = props
  return rest
})

/**
 * 根据 fieldNames 规范化选项数据
 * 支持两种格式：
 * 1. 已经是 { label, value } 格式
 * 2. 原始数据格式，通过 fieldNames 映射
 */
const normalizedOptions = computed<Option[]>(() => {
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

  // 如果没有 fieldNames 且不是标准格式，返回空数组并警告
  console.warn('[SearchSelect] options 数据格式不正确，请检查 fieldNames 配置')
  return []
})

const handleChange = (val: any) => {
  emit('update:modelValue', val)
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
