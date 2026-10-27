<template>
  <a-input
    :value="modelValue"
    allow-clear
    v-bind="props"
    @update:value="handleChange"
    @press-enter="handleSearch"
  />
</template>

<script setup lang="ts">
interface Props {
  modelValue: any
  placeholder?: string
  props?: Record<string, any>
}

interface Emits {
  'update:modelValue': [value: any]
  search: []
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请输入',
})

const emit = defineEmits<Emits>()

const handleChange = (val: any) => {
  emit('update:modelValue', val)
}

const handleSearch = () => {
  emit('search')
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
