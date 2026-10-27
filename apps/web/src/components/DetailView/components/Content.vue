<template>
  <div class="detail-content">
    <template v-for="section in visibleSections" :key="section.key">
      <!-- slot 插槽模式 -->
      <DetailSection
        v-if="section.type === 'slot'"
        :title="section.title"
        :icon="section.icon"
        :visible="isSectionVisible(section)"
        :custom-class="section.class"
        :style="section.style"
      >
        <slot :name="`section-${section.key}`" :data="data" :section="section" />
      </DetailSection>

      <!-- custom 自定义渲染 -->
      <DetailSection
        v-else-if="section.type === 'custom'"
        :title="section.title"
        :icon="section.icon"
        :visible="isSectionVisible(section)"
        :custom-class="section.class"
        :style="section.style"
      >
        <component
          :is="section.render!(h, data!)"
          v-if="section.render && isSectionVisible(section)"
        />
      </DetailSection>

      <!-- table 表格模式 -->
      <DetailSection
        v-else-if="section.type === 'table'"
        :title="section.title"
        :icon="section.icon"
        :visible="isSectionVisible(section)"
        :custom-class="section.class"
        :style="section.style"
      >
        <slot :name="`section-${section.key}`" :data="data" :section="section" :extra="extra">
          <DetailTableView
            v-if="section.table && isSectionVisible(section)"
            :config="section.table"
            :data="data!"
          />
        </slot>
      </DetailSection>

      <!-- fields 字段列表模式 -->
      <DetailSection
        v-else-if="section.type === 'fields' && section.fields"
        :title="section.title"
        :icon="section.icon"
        :visible="isSectionVisible(section)"
        :custom-class="section.class"
        :style="section.style"
      >
        <template #default>
          <slot :name="`section-${section.key}-content`" :data="data" :fields="section.fields">
            <a-row :gutter="section.gutter || config.fieldGutter || [12, 8]">
              <a-col
                v-for="field in visibleFields(section.fields!)"
                :key="field.key"
                v-bind="resolveFieldSpans(field, config.defaultSpans)"
              >
                <FieldItem :field="field" :data="data!" />
              </a-col>
            </a-row>
          </slot>
        </template>
      </DetailSection>
    </template>

    <!-- extra 插槽：拼接在 sections 最下方，供审批表单等场景使用 -->
    <slot name="extra" />
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import DetailSection from './Section.vue'
import FieldItem from './FieldItem.vue'
import DetailTableView from './TableView.vue'
import { isFieldVisible, resolveFieldSpans } from '../utils'
import type { DetailConfig, DetailSection as SectionType } from '../types'

interface Props {
  config: DetailConfig
  data: Record<string, unknown> | null
  extra?: Record<string, unknown>
}

const props = defineProps<Props>()

// 合并 data 和 extra 作为上下文，用于 visible 函数判断
const context = computed(() => ({ ...props.data, ...props.extra }))

const visibleSections = computed(() => {
  if (!props.data) return []
  return props.config.sections.filter(section => {
    if (typeof section.visible === 'function') {
      return section.visible(context.value)
    }
    return section.visible !== false
  })
})

function isSectionVisible(section: SectionType): boolean {
  if (typeof section.visible === 'function') {
    return section.visible(context.value)
  }
  return section.visible !== false
}

function visibleFields(fields: SectionType['fields']) {
  if (!fields || !props.data) return []
  return fields.filter(field => isFieldVisible(field, props.data!))
}
</script>

<style lang="less">
.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--detail-section-gap, 16px);
}
</style>
