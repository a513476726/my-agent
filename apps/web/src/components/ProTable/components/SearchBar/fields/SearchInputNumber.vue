<template>
  <a-input-number
    :value="modelValue"
    :style="{ width: '100%' }"
    v-bind="props"
    @update:value="handleChange"
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
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请输入',
})

const emit = defineEmits<Emits>()

const handleChange = (val: any) => {
  emit('update:modelValue', val)
}
</script>

<style scoped lang="less">
// 样式由 SearchItem 处理
</style>
