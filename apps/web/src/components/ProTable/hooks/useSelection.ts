/**
 * 表格选择状态管理 Hook
 * 管理表格行选择状态
 */
import { ref, computed } from 'vue'
import type { UseSelectionReturn, TableSelectionConfig } from '../types'

/**
 * 表格选择状态管理
 * @param config 选择配置
 * @returns 选择状态和方法
 */
export function useSelection<T = any>(config?: TableSelectionConfig): UseSelectionReturn<T> {
  // 选中的行 keys
  const selectedRowKeys = ref<any[]>([])

  // 选中的行数据
  const selectedRows = ref<T[]>([]) as import('vue').Ref<T[]>

  /**
   * 处理选择变化
   */
  const handleSelectionChange = (keys: any[], rows: T[]) => {
    selectedRowKeys.value = keys
    selectedRows.value = rows
  }

  /**
   * 行选择配置
   */
  const rowSelection = computed(() => {
    if (!config) return undefined

    return {
      type: config.type || 'checkbox',
      fixed: config.fixed !== false,
      selectedRowKeys: selectedRowKeys.value,
      onChange: handleSelectionChange,
    }
  })

  /**
   * 清空选择
   */
  const clearSelection = () => {
    selectedRowKeys.value = []
    selectedRows.value = []
  }

  /**
   * 设置选择
   */
  const setSelection = (keys: any[], rows: T[]) => {
    selectedRowKeys.value = keys
    selectedRows.value = rows
  }

  return {
    selectedRowKeys,
    selectedRows,
    rowSelection,
    clearSelection,
    setSelection,
  }
}
