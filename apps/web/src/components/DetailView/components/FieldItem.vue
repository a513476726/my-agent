<template>
  <div v-if="visible" class="detail-field" :class="{ 'is-wrap': wrap }">
    <div class="detail-field__label" :style="labelStyle">
      <span>{{ field.label }}</span>
      <span v-if="!wrap" class="detail-field__colon">:</span>
    </div>
    <div class="detail-field__value" :class="variantClass" :style="valueStyle">
      <a-tooltip
        v-if="showTooltip && displayValue !== '--'"
        :title="tooltipTitle"
        placement="topLeft"
      >
        <span class="detail-field__content" :class="{ 'is-ellipsis': ellipsis }">
          <template v-if="field.isAttachment && !isEmptyValue(rawValue)">
            <ProUpload
              v-model:json-value="rawValue as string"
              :disabled="true"
              :hide-button="true"
              :hide-tip="true"
              :display-mode="field.displayMode || 'default'"
            />
          </template>
          <template v-else-if="field.render">
            <component :is="field.render(h, rawValue, data)" />
          </template>
          <template v-else>{{ displayValue }}</template>
        </span>
      </a-tooltip>
      <span v-else class="detail-field__content" :class="{ 'is-ellipsis': ellipsis }">
        <template v-if="field.isAttachment && !isEmptyValue(rawValue)">
          <ProUpload
            v-model:json-value="rawValue as string"
            :disabled="true"
            :hide-button="true"
            :hide-tip="true"
            :display-mode="field.displayMode || 'default'"
          />
        </template>
        <template v-else-if="field.render">
          <component :is="field.render(h, rawValue, data)" />
        </template>
        <template v-else>{{ displayValue }}</template>
      </span>
    </div>
    <span v-if="field.tag" class="detail-field__tag">{{ field.tag }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import ProUpload from '@/components/ProUpload/index.vue'
import type { DetailField } from '../types'
import { resolveFieldValue, resolveFieldVariant, isFieldVisible } from '../utils'

interface Props {
  field: DetailField
  data: Record<string, unknown>
}

const props = defineProps<Props>()

const rawValue = computed(() => resolveFieldValue(props.field, props.data))
// 判断值是否为空（null, undefined, 空字符串, 空数组, 空对象）
const isEmptyValue = (val: unknown): boolean => {
  if (val === null || val === undefined || val === '') return true
  if (Array.isArray(val) && val.length === 0) return true
  if (typeof val === 'object' && Object.keys(val).length === 0) return true
  return false
}
const displayValue = computed(() => {
  if (isEmptyValue(rawValue.value)) return '--'
  if (typeof rawValue.value === 'object') return JSON.stringify(rawValue.value)
  return String(rawValue.value)
})
const tooltipTitle = computed(() => String(rawValue.value ?? ''))
const variant = computed(() => resolveFieldVariant(props.field, props.data))
const visible = computed(() => isFieldVisible(props.field, props.data))
const ellipsis = computed(() => props.field.ellipsis !== false && !props.field.wordBreak)
const tooltip = computed(() => {
  if (props.field.isAttachment) return false
  if (props.field.tooltip !== undefined) return props.field.tooltip && ellipsis.value
  return ellipsis.value
})
const wrap = computed(() => props.field.wrap)
const showTooltip = computed(() => tooltip.value && ellipsis.value)

// wordBreak 时强制换行展示全量文本，不使用 ellipsis
const wordBreakValue = computed(() => props.field.wordBreak || 'normal')

// 空值时不应用样式变体
const variantClass = computed(() => {
  if (displayValue.value === '--') return ''
  return `is-${variant.value}`
})

const labelStyle = computed(() => ({
  width: props.field.labelWidth ?? (props.field.wrap ? '100%' : 'auto'),
  textAlign: props.field.labelAlign ?? 'left',
}))

const valueStyle = computed(() => ({
  flex: props.field.wrap ? 1 : 'auto',
  wordBreak: wordBreakValue.value,
}))
</script>

<style lang="less">
.detail-field {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--detail-field-bg, #fafafa);
  border-radius: 4px;
  min-height: 36px;

  &.is-wrap {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  &__label {
    flex-shrink: 0;
    font-size: 12px;
    color: var(--detail-label-color, #8c8c8c);
    display: flex;
    align-items: center;

    .is-wrap & {
      width: 100%;
    }
  }

  &__colon {
    margin-left: 2px;
  }

  &__tag {
    flex-shrink: 0;
    margin-left: auto; /* 推到一行最右侧 */
    font-size: 10px;
    line-height: 16px;
    color: var(--detail-primary-color, #1d45dd);
    background: rgba(29, 69, 221, 0.1);
    border: 1px solid currentColor;
    border-radius: 3px;
    padding: 0 4px;
  }

  &__value {
    flex: 1;
    min-width: 0;
    overflow: hidden; /* 长内容收缩省略，不覆盖右侧 tag */
    color: var(--detail-value-color, #333);

    &.is-success {
      color: #52c41a;
    }

    &.is-danger {
      color: #ff4d4f;
    }

    &.is-warning {
      color: #faad14;
    }

    &.is-error {
      color: #ff4d4f;
    }

    &.is-processing {
      color: #1890ff;
    }
  }

  &__content {
    display: block;

    &.is-ellipsis {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}
</style>
