<template>
  <div class="encrypted-cell">
    <span class="encrypted-cell__value">{{ displayValue }}</span>
    <component
      v-if="props.value"
      :is="iconComponent"
      class="encrypted-cell__icon"
      :class="{ 'encrypted-cell__icon--decrypted': isDecrypted }"
      @click="handleToggle"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import {
  EyeOutlined,
  EyeInvisibleOutlined,
  LockOutlined,
  UnlockOutlined,
} from '@ant-design/icons-vue'
import type { ProEncryptConfig } from '../types'

interface Props {
  /** 原始值 */
  value: any
  /** 加密配置 */
  config: ProEncryptConfig
  /** 字段名 */
  dataIndex: string
}

const props = defineProps<Props>()

// 状态
const isDecrypted = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

/**
 * 内置加密函数
 */
const BUILT_IN_ENCRYPT = {
  name: (v: string) => {
    if (!v) return '--'
    return v[0] + '*'.repeat(Math.max(0, v.length - 1))
  },
  phone: (v: string) => {
    if (!v) return '--'
    return String(v).replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
  },
  idCard: (v: string) => {
    if (!v) return '--'
    return String(v).replace(/^(.{6}).*(.{4})$/, '$1********$2')
  },
  email: (v: string) => {
    if (!v) return '--'
    return String(v).replace(/^(.{2}).*(@.*)$/, '$1***$2')
  },
}

/**
 * 加密后的值
 */
const encryptedValue = computed(() => {
  if (!props.value) return '--'

  // 优先使用自定义加密函数
  if (props.config.encryptFn) {
    return props.config.encryptFn(props.value)
  }

  // 使用内置加密类型
  const type = props.config.encryptType || 'name'
  return BUILT_IN_ENCRYPT[type](props.value)
})

/**
 * 显示值
 */
const displayValue = computed(() => {
  return isDecrypted.value ? props.value : encryptedValue.value
})

/**
 * 图标组件
 */
const iconComponent = computed(() => {
  const iconType = props.config.icon || 'eye'

  if (iconType === 'lock') {
    return isDecrypted.value ? UnlockOutlined : LockOutlined
  }

  return isDecrypted.value ? EyeOutlined : EyeInvisibleOutlined
})

/**
 * 清除定时器
 */
const clearAutoHideTimer = () => {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

/**
 * 切换显示
 */
const handleToggle = () => {
  const mode = props.config.mode || 'manual'

  if (mode === 'manual') {
    // 手动模式：点击切换，不自动隐藏
    isDecrypted.value = !isDecrypted.value
  } else {
    // 自动模式：显示后定时隐藏
    isDecrypted.value = true
    clearAutoHideTimer()
    timer = setTimeout(() => {
      isDecrypted.value = false
    }, props.config.duration || 3000)
  }
}

// 组件卸载时清除定时器
onUnmounted(() => {
  clearAutoHideTimer()
})
</script>

<style scoped lang="less">
.encrypted-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  &__value {
    user-select: none;
  }

  &__icon {
    cursor: pointer;
    font-size: 14px;
    color: #8c8c8c;
    transition: all 0.3s;

    &:hover {
      color: #1890ff;
      transform: scale(1.15);
    }

    &--decrypted {
      color: #52c41a;
    }
  }
}
</style>
