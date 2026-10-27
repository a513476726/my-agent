<template>
  <div ref="itemRef" class="ant-search-item">
    <span v-if="label" class="ant-search-item-label">{{ label }}</span>
    <div class="ant-search-item-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide } from 'vue'

interface Props {
  label?: string
  labelWidth?: number | string
}

defineProps<Props>()

const itemRef = ref<HTMLElement | null>(null)

/** 容器实际宽度，通过 provide 暴露给下拉组件，用于设置 dropdown min-width */
provide('searchItemWidth', 0)

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (itemRef.value) {
    const setWidth = () => {
      if (itemRef.value) {
        // 通过 CSS 变量暴露给子组件的 dropdownStyle 使用
        itemRef.value.style.setProperty('--search-item-width', `${itemRef.value.offsetWidth}px`)
      }
    }
    setWidth()
    resizeObserver = new ResizeObserver(setWidth)
    resizeObserver.observe(itemRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<style scoped lang="less">
.ant-search-item {
  display: flex;
  align-items: center;
  height: 100%;
  width: 100%;
  max-height: 31px;
  box-sizing: border-box;
  padding: 4px 8px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background-color: #fff;
  transition: all 0.3s;

  &:hover {
    border-color: #1d45dd;
  }

  &.ant-search-item-focused {
    border-color: #1d45dd;
    box-shadow: 0 0 0 2px rgba(29, 69, 221, 0.1);
  }

  &-label {
    flex-shrink: 0;
    color: #4e5969;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1;
    padding-right: 8px;
  }

  &-content {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    line-height: 1;
  }

  :deep(.ant-select),
  :deep(.ant-picker),
  :deep(.ant-input),
  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input-number) {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;

    .ant-select-selector {
      border: none !important;
      outline: none !important;
      box-shadow: none !important;
      background: transparent !important;
    }
  }

  :deep(.ant-select-selector) {
    padding: 0 !important;
  }

  :deep(.ant-select-selection-overflow) {
    margin-left: 0 !important;
    flex-wrap: nowrap !important;
    overflow: hidden !important;
  }

  :deep(.ant-select-selection-overflow-item) {
    flex-shrink: 0 !important;
  }

  :deep(.ant-select-selection-item) {
    flex-shrink: 0 !important;
  }

  :deep(.ant-input),
  :deep(.ant-input-affix-wrapper) {
    min-width: 50px;
    line-height: 1;
    padding: 0;
  }

  :deep(.ant-picker) {
    padding: 0 !important;

    .ant-picker-suffix {
      margin-left: 4px;
    }
  }

  :deep(.ant-input-number) {
    line-height: 1;
    padding: 0;
  }
}
</style>
