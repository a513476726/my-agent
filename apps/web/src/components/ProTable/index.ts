/**
 * ProTable 组件导出
 */
import ProTable from './index.vue'

export { ProTable }
export default ProTable

// 导出类型
export type {
  SearchConfig,
  SearchFieldConfig,
  ToolbarConfig,
  ToolbarButtonConfig,
  TableConfig,
  TableSelectionConfig,
  ProColumnConfig,
  ActionConfig,
  ValueEnumConfig,
  ProTableProps,
  PageResponse,
  UseProTableOptions,
  UseProTableReturn,
  UseSelectionReturn,
} from './types'

// 导出 hooks
export { useProTable } from './hooks/useProTable'
export { useSelection } from './hooks/useSelection'
