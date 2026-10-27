<template>
  <div v-if="visible" class="detail-section" :class="customClass">
    <div class="detail-section__header">
      <slot name="header">
        <component :is="resolvedIcon" v-if="icon" :size="16" class="detail-section__icon" />
        <span class="detail-section__title">{{ title }}</span>
        <span v-if="subtitle" class="detail-section__subtitle">{{ subtitle }}</span>
      </slot>
    </div>
    <div class="detail-section__content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FileText } from 'lucide-vue-next'
import type { Component } from 'vue'

const props = defineProps<{
  title?: string
  icon?: string | Component | Record<string, unknown>
  subtitle?: string
  visible?: boolean
  customClass?: string
}>()

const resolvedIcon = computed(() => {
  if (!props.icon) return FileText
  if (typeof props.icon === 'string') {
    return props.icon
  }
  return props.icon
})

const visible = computed(() => props.visible !== false)
</script>

<style lang="less">
.detail-section {
  background: #fff;
  padding: 20px 24px;
  border: 1px solid var(--detail-border-color, #e8ecf0);
  border-radius: 8px;

  &__header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 12px;
    margin-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  &__icon {
    color: var(--detail-primary-color, #1d45dd);
    flex-shrink: 0;
  }

  &__title {
    font-size: 14px;
    font-weight: 600;
    color: var(--detail-title-color, #1a1a2e);
  }

  &__subtitle {
    font-size: 12px;
    color: var(--detail-label-color, #8c8c8c);
    margin-left: 8px;
  }

  &__content {
    // 内容区样式
  }
}
</style>
