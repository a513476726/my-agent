<template>
  <a-date-picker
    :value="modelValue"
    :style="{ width: '100%' }"
    :locale="locale"
    format="YYYY-MM-DD"
    value-format="YYYY-MM-DD"
    v-bind="props"
    @update:value="handleChange"
  />
</template>

<script setup lang="ts">
import zhCN from 'ant-design-vue/es/locale/zh_CN'

interface Props {
  modelValue: any
  placeholder?: string
  props?: Record<string, any>
}

interface Emits {
  'update:modelValue': [value: any]
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择日期',
})

const emit = defineEmits<Emits>()

const locale = zhCN

const handleChange = (val: any) => {
  emit('update:modelValue', val)
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
