<template>
  <div class="pro-table-actions">
    <!-- 直接显示的按钮（前 2 个） -->
    <template v-for="action in directActions" :key="action.key">
      <a-button
        type="link"
        size="small"
        :danger="action.danger"
        :disabled="isActionDisabled(action)"
        :title="getActionTitle(action)"
        @click="handleActionClick(action)"
      >
        {{ action.text }}
      </a-button>
    </template>

    <!-- 更多下拉菜单（第 3 个位置） -->
    <a-dropdown
      v-if="dropdownActions.length > 0"
      v-model:open="dropdownVisible"
      :trigger="['hover']"
    >
      <a-button type="link" size="small" class="more-button">
        更多
        <DownOutlined :class="['dropdown-icon', { 'dropdown-icon-open': dropdownVisible }]" />
      </a-button>
      <template #overlay>
        <a-menu>
          <a-menu-item
            v-for="action in dropdownActions"
            :key="action.key"
            :disabled="isActionDisabled(action)"
            :danger="action.danger"
            :title="getActionTitle(action)"
            @click="handleActionClick(action)"
          >
            <span>{{ action.text }}</span>
            <!-- 禁用原因：a-menu-item 的 title 不可靠，直接在菜单项内展示 -->
            <span
              v-if="isActionDisabled(action) && getActionTitle(action)"
              class="action-disabled-tip"
            >
              （{{ getActionTitle(action) }}）
            </span>
          </a-menu-item>
        </a-menu>
      </template>
    </a-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { ActionConfig, ProTableMethods, ShowButtonsMethod } from '../types'

interface Props {
  /** 操作按钮配置 */
  actions: ActionConfig[]
  /** 当前行数据 */
  record: any
  /** 方法集合 */
  methods?: ProTableMethods
  /** 按钮显示控制方法 */
  showButtons?: ShowButtonsMethod
}

const props = withDefaults(defineProps<Props>(), {
  methods: undefined,
  showButtons: undefined,
})

const authStore = useAuthStore()

// ========== 常量配置 ==========

/**
 * 超过此数量时显示"更多"下拉菜单
 * 例如：3 个及以下按钮全部直接显示，4 个及以上显示前 2 个 + "更多"菜单
 */
const ACTION_THRESHOLD = 3

/**
 * 直接显示的按钮数量（超过阈值时）
 */
const MAX_DIRECT_ACTIONS = 2

// ========== 状态管理 ==========

/**
 * 下拉菜单显示状态
 */
const dropdownVisible = ref(false)

// ========== 按钮状态控制 ==========

/**
 * 获取按钮状态（显示/禁用）
 */
const getButtonStatus = (action: ActionConfig) => {
  // 内置权限检查：通过 action.id 检查权限
  if (action.id && authStore.permissions[action.id] !== true) {
    return { show: false, disabled: true }
  }

  // 如果提供了 showButtons 方法，使用自定义逻辑
  if (props.showButtons) {
    return props.showButtons(action, props.record)
  }

  // 默认全部显示且启用
  return {
    show: true,
    disabled: false,
  }
}

/**
 * 可见的操作按钮（通过 showButtons 控制）
 */
const visibleActions = computed(() => {
  return props.actions.filter(action => {
    const status = getButtonStatus(action)
    return status.show
  })
})

/**
 * 判断操作是否禁用（通过 showButtons 控制）
 */
const isActionDisabled = (action: ActionConfig): boolean => {
  const status = getButtonStatus(action)
  return status.disabled
}

/**
 * 悬停提示：showButtons 返回的 title 优先，其次取 action.title
 */
const getActionTitle = (action: ActionConfig): string | undefined => {
  if (props.showButtons) {
    const status = props.showButtons(action, props.record)
    if (status.title) return status.title
  }
  return action.title
}

// ========== 按钮分组逻辑 ==========

/**
 * 直接显示的按钮
 * - 可见按钮 ≤ 3 个：全部直接显示
 * - 可见按钮 > 3 个：只显示前 2 个
 */
const directActions = computed(() => {
  if (visibleActions.value.length <= ACTION_THRESHOLD) {
    return visibleActions.value
  }
  return visibleActions.value.slice(0, MAX_DIRECT_ACTIONS)
})

/**
 * 下拉菜单中的按钮
 * - 可见按钮 ≤ 3 个：不显示下拉菜单
 * - 可见按钮 > 3 个：显示第 3 个及以后的按钮
 */
const dropdownActions = computed(() => {
  if (visibleActions.value.length <= ACTION_THRESHOLD) {
    return []
  }
  return visibleActions.value.slice(MAX_DIRECT_ACTIONS)
})

// ========== 事件处理 ==========

/**
 * 处理操作点击
 */
const handleActionClick = (action: ActionConfig) => {
  // 菜单项点击后收起下拉：自定义 overlay 不受 antd 自动关闭控制，否则会遮挡上层弹窗
  dropdownVisible.value = false
  // 如果有 action 且提供了 methods，调用对应方法
  if (action.action && props.methods && props.methods[action.action]) {
    props.methods[action.action](props.record)
  }
}
</script>

<style scoped lang="less">
.pro-table-actions {
  display: flex;
  gap: 0; // 减小按钮间距为 0，通过按钮内部 padding 控制
  justify-content: center;
  align-items: center;
  flex-wrap: nowrap;

  // 按钮样式优化
  :deep(.ant-btn-link) {
    padding: 0 4px; // 减小按钮内边距，控制按钮间距
  }
}

// "更多"按钮样式
.more-button {
  display: inline-flex;
  align-items: center;
  gap: 1px; // 文字和图标之间的间距减小到 1px

  // 下拉图标样式
  .dropdown-icon {
    font-size: 11px; // 图标大小调整为 11px（比 10px 稍大）
    transition: transform 0.3s cubic-bezier(0.645, 0.045, 0.355, 1); // 添加平滑旋转动画
    transform-origin: center center;
    margin-left: 2px;

    // 展开状态：旋转 180 度
    &.dropdown-icon-open {
      transform: rotate(180deg);
    }
  }
}

// 下拉菜单危险项样式
:deep(.ant-dropdown-menu-item-danger) {
  color: #ff4d4f;

  &:hover {
    color: #ff4d4f;
    background-color: #fff1f0;
  }
}

// 禁用的菜单项样式
:deep(.ant-dropdown-menu-item-disabled) {
  color: rgba(0, 0, 0, 0.25);
  cursor: not-allowed;
}

// 下拉菜单内联的禁用原因提示
:deep(.action-disabled-tip) {
  font-size: 12px;
  opacity: 0.85;
}
</style>
