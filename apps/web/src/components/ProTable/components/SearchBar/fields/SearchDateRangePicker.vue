<template>
  <a-range-picker
    :value="innerValue"
    :style="{ width: '100%' }"
    :locale="locale"
    :format="displayFormat"
    :value-format="displayFormat"
    v-bind="props"
    @update:value="handleChange"
    @change="(val: any) => emit('update:modelValue', val)"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

interface Props {
  modelValue: any
  placeholder?: string[]
  props?: Record<string, any>
  /**
   * true：format / value-format 均为 YYYY-MM-DD，handleChange 不补 00:00:00 / 23:59:59
   * 用于「显示与选择都是 YYYY-MM-DD，请求参数 padding 由 useProTable 拆分阶段统一处理」
   * 默认 false（保持原行为，向后兼容 onboardDate / leaveDate 等日期范围）
   */
  keepDateOnly?: boolean
}

interface Emits {
  'update:modelValue': [value: any]
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: () => ['开始日期', '结束日期'],
  keepDateOnly: false,
})

const emit = defineEmits<Emits>()

const locale = zhCN

/** keepDateOnly=true 时只展示 YYYY-MM-DD，否则维持原 HH:mm:ss */
const displayFormat = computed(() => (props.keepDateOnly ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm:ss'))

// 内部值，用于处理默认值
// 关键：用 immediate + deep watch + 浅克隆，避免 a-range-picker 拿到 reactive proxy 数组导致初次不渲染
const innerValue = ref<any>(undefined)

watch(
  () => props.modelValue,
  newVal => {
    innerValue.value = Array.isArray(newVal) ? [...newVal] : newVal
  },
  { immediate: true, deep: true }
)

// 处理默认值：开始时间 00:00:00，结束时间 23:59:59
// keepDateOnly=true 时不做 padding，原样透传 YYYY-MM-DD（padding 由 useProTable 拆分阶段统一处理）
const handleChange = (val: any) => {
  if (!val || (Array.isArray(val) && val.length === 0)) {
    emit('update:modelValue', val)
    return
  }

  if (Array.isArray(val) && val.length === 2) {
    const [start, end] = val

    // keepDateOnly 模式：原样透传，由 useProTable.formatSearchParams 按字段 dateRangePadTime 决定 padding
    if (props.keepDateOnly) {
      const formatted = [start, end]
      innerValue.value = formatted
      emit('update:modelValue', formatted)
      return
    }

    let formattedStart = start
    let formattedEnd = end

    // 如果启用了 showTime，始终设置默认时间
    if (props.props?.showTime) {
      formattedStart = start.split(' ')[0] + ' 00:00:00'
      formattedEnd = end.split(' ')[0] + ' 23:59:59'
    } else {
      // 如果开始时间没有时分秒，默认 00:00:00
      if (start && !start.includes(':')) {
        formattedStart = start.split(' ')[0] + ' 00:00:00'
      }
      // 如果结束时间没有时分秒，默认 23:59:59
      if (end && !end.includes(':')) {
        formattedEnd = end.split(' ')[0] + ' 23:59:59'
      }
    }

    const formatted = [formattedStart, formattedEnd]
    innerValue.value = formatted
    emit('update:modelValue', formatted)
  } else {
    innerValue.value = val
    emit('update:modelValue', val)
  }
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
