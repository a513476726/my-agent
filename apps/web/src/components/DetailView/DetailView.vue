<template>
  <!-- Card 模式 -->
  <a-card v-if="mode === 'card'" :bordered="false" class="detail-view">
    <template #title>
      <slot name="title">
        <slot name="header">
          <DetailViewHeader
            v-if="showHeader"
            :icon="headerIcon"
            :title="title"
            :subtitle="subtitle"
          />
        </slot>
      </slot>
    </template>

    <div class="detail-view-body">
      <DetailViewContent :config="config" :data="data" :extra="extra">
        <template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
          <slot :name="name" v-bind="{ ...(slotData || {}), extra }" />
        </template>
      </DetailViewContent>
    </div>

    <template v-if="footer !== false" #footer>
      <slot name="footer">
        <div class="detail-view-footer">
          <a-button
            v-if="footer === undefined || footer?.showClose !== false"
            :type="footer?.closeType || 'default'"
            @click="handleClose"
          >
            {{ footer?.closeText || '关闭' }}
          </a-button>
          <a-button
            v-for="btn in footer?.extraButtons"
            :key="btn.text"
            :type="btn.type"
            :danger="btn.danger"
            @click="btn.onClick"
          >
            {{ btn.text }}
          </a-button>
        </div>
      </slot>
    </template>
  </a-card>

  <!-- Embed 模式 -->
  <div v-else-if="mode === 'embed'" class="detail-view detail-view--embed">
    <DetailViewContent :config="config" :data="data" :extra="extra">
      <template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
        <slot :name="name" v-bind="slotData || {}" />
      </template>
    </DetailViewContent>
  </div>

  <!-- Modal 模式 -->
  <a-modal
    v-else
    v-model:open="dialogVisible"
    :width="width"
    :style="{ height: '80vh' }"
    :body-style="{ height: 'calc(80vh - 110px)' }"
    :mask-closable="false"
    :footer="footer === false ? null : undefined"
    destroy-on-close
    @cancel="handleClose"
  >
    <template #title>
      <slot name="title">
        {{ title }}
      </slot>
    </template>
    <a-spin :spinning="loading">
      <div class="detail-view-body">
        <DetailViewContent :config="config" :data="data">
          <template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
            <slot :name="name" v-bind="slotData || {}" />
          </template>
        </DetailViewContent>
      </div>
    </a-spin>
    <template v-if="footer !== false" #footer>
      <slot name="modal-footer">
        <div class="detail-view-footer">
          <a-button
            v-if="footer === undefined || footer?.showClose !== false"
            :type="footer?.closeType || 'default'"
            @click="handleClose"
          >
            {{ footer?.closeText || '关闭' }}
          </a-button>
          <a-button
            v-for="btn in footer?.extraButtons"
            :key="btn.text"
            :type="btn.type"
            :danger="btn.danger"
            @click="btn.onClick"
          >
            {{ btn.text }}
          </a-button>
        </div>
      </slot>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DetailViewContent from './components/Content.vue'
import DetailViewHeader from './components/Header.vue'
import type { DetailViewProps } from './types'

const props = withDefaults(defineProps<DetailViewProps>(), {
  mode: 'embed',
  title: '详情',
  width: '80%',
  loading: false,
  showHeader: true,
  showClose: true,
  extra: () => ({}),
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  close: []
}>()

const dialogVisible = computed({
  get: () => props.open ?? false,
  set: v => emit('update:open', v),
})

function handleClose() {
  emit('update:open', false)
  emit('close')
}
</script>

<style lang="less">
.detail-view {
  --detail-primary-color: #1d45dd;
  --detail-border-color: #e8ecf0;
  --detail-field-bg: #fafafa;
  --detail-title-color: #1a1a2e;
  --detail-label-color: #8c8c8c;
  --detail-value-color: #333;
  --detail-section-gap: 16px;

  &--embed {
    padding: 0;
    max-height: calc(80vh - 110px);
    overflow-y: auto;
  }

  &-body {
    max-height: calc(80vh - 110px);
    overflow-y: auto;
    padding-right: 4px;
  }

  &-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  // 加载指示器居中，垂直方向 40%
  :deep(.ant-spin-nested-loading) {
    position: relative;
    min-height: 200px;
  }
  :deep(.ant-spin) {
    position: absolute;
    top: 40%;
    left: 50%;
    transform: translateX(-50%);
  }
}
</style>
