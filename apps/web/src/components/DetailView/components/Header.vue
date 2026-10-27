<template>
  <div class="detail-header">
    <component :is="resolvedIcon" v-if="icon || title" :size="18" class="detail-header__icon" />
    <span class="detail-header__title">{{ title || '详情' }}</span>
    <span v-if="subtitle" class="detail-header__subtitle">{{ subtitle }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FileText } from 'lucide-vue-next'
import type { Component } from 'vue'

const props = defineProps<{
  icon?: string | Component
  title?: string
  subtitle?: string
}>()

const resolvedIcon = computed(() => {
  if (!props.icon && !props.title) return FileText
  if (typeof props.icon === 'string') {
    return props.icon
  }
  return props.icon || FileText
})
</script>

<style lang="less">
.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;

  &__icon {
    color: var(--detail-primary-color, #1d45dd);
    flex-shrink: 0;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--detail-title-color, #1a1a2e);
  }

  &__subtitle {
    font-size: 12px;
    color: var(--detail-label-color, #8c8c8c);
    margin-left: 4px;
  }
}
</style>
