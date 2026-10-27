/**
 * ProTable 组件类型定义
 */
import type { Component, VNode } from 'vue'
import type { TableColumnType } from 'ant-design-vue'

// ========== 搜索配置类型 ==========

/**
 * 参数格式化函数类型
 */
export type ParamFormatFn = (value: any) => any

/**
 * 内置参数格式化器
 */
export const ParamFormatters = {
  /** 数组转换为逗号分隔字符串，如：['a','b'] => 'a,b' */
  arrayJoin: (value: any) => {
    if (Array.isArray(value)) {
      return value.join(',')
    }
    return value
  },
  /** 日期范围格式化，输出 { fieldStart, fieldEnd } 格式 */
  dateRange: (value: any, field: string) => {
    if (Array.isArray(value) && value.length === 2) {
      return {
        [`${field}Start`]: value[0],
        [`${field}End`]: value[1],
      }
    }
    return value
  },
}

/**
 * 日期范围参数映射配置
 */
export interface DateRangeParams {
  /** 开始日期参数名 */
  start: string
  /** 结束日期参数名 */
  end: string
}

/**
 * 搜索字段配置
 */
export interface SearchFieldConfig {
  /** 字段名，对应查询参数 */
  field: string
  /** 标签名（可选，用于表单布局） */
  label?: string
  /** 组件名称 */
  name:
    | 'input'
    | 'select'
    | 'date'
    | 'dateRange'
    | 'inputNumber'
    | 'asyncSelect'
  /** 占位文本 */
  placeholder?: string | string[]
  /** select 选项 - 支持任意数据结构，通过 fieldNames 指定字段映射 */
  options?: Record<string, any>[]
  /** 自定义选项字段名（用于 select 等组件） */
  fieldNames?: { label: string; value: string }
  /** 参数格式化器 - 内置值或自定义函数 */
  paramFormat?: 'arrayJoin' | ParamFormatFn
  /** 日期范围字段的转换参数名（当 dateRange 需要映射到不同参数名时使用） */
  dateRangeParams?: DateRangeParams
  /**
   * 仅当 name === 'dateRange' 时生效。
   * true 时 useProTable.formatSearchParams 在拆分 dateRange 时
   * 会把 start 补 00:00:00、end 补 23:59:59（基于 YYYY-MM-DD）。
   * 用于「UI / URL 都用 YYYY-MM-DD，实际后端请求需要时分秒边界」的场景。
   */
  dateRangePadTime?: boolean
  /** 默认值 */
  defaultValue?: any
  /** 宽度，默认 200px */
  width?: number | string
  /** 占位数，默认 1 */
  span?: number
  /** 透传给组件的其他属性 */
  props?: Record<string, any>
  /** 远程获取选项的接口函数（用于 asyncSelect） */
  remoteFunc?: () => Promise<any[]>
  /** 远程数据格式化函数 */
  remoteFormat?: (data: any[]) => { label: string; value: any }[]
  /** 是否为关键筛选项（常驻显示，不进入弹窗），默认 false */
  important?: boolean
}

/**
 * 搜索区域配置
 */
export interface SearchConfig {
  /** 搜索字段配置 */
  fields: SearchFieldConfig[]
  /** 是否显示清空按钮，默认 true */
  showReset?: boolean
  /** 是否显示查询按钮，默认 true */
  showSearch?: boolean
  /** 默认是否折叠，默认 true */
  defaultCollapsed?: boolean
  /** 折叠阈值，超过此数量显示"展开"按钮，默认 2 */
  collapseThreshold?: number
  /** 关键筛选项数量上限，默认 2（仅 important=true 的前 N 个生效） */
  importantCount?: number
}

// ========== 工具栏配置类型 ==========

/**
 * 工具栏按钮配置
 */
export interface ToolbarButtonConfig {
  /** 按钮唯一标识 */
  key: string
  /** 按钮 ID（权限标识） */
  id?: string
  /** 按钮文字 */
  text: string
  /** 按钮类型 */
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text'
  /** 是否幽灵按钮 */
  ghost?: boolean
  /** 是否危险按钮 */
  danger?: boolean
  /** 图标 */
  icon?: Component
  /** 方法名称（调用 methods 中的方法） */
  action?: string
  /** 权限标识（已废弃，使用 id） */
  permission?: string
  /** 是否显示 */
  visible?: boolean | (() => boolean)
  /** 是否禁用 */
  disabled?: boolean | ((selectedRows: any[]) => boolean)
  /** 是否需要选中行才能操作，默认 false */
  needSelection?: boolean
  /** 是否为报表模式默认按钮（内部使用） */
  isDefaultReport?: boolean
}

/**
 * 工具栏配置
 */
export interface ToolbarConfig {
  /** 左侧按钮 */
  leftButtons?: ToolbarButtonConfig[]
  /** 右侧按钮（支持 VNode 用于自定义内容如文案） */
  rightButtons?: (ToolbarButtonConfig | VNode)[]
  /** 报表模式配置 */
  reportConfig?: ReportToolbarConfig
}

/**
 * 报表模式工具栏配置
 */
export interface ReportToolbarConfig {
  /** 是否显示筛选按钮，默认 true */
  showFilterButton?: boolean
  /** 是否显示查询按钮，默认 true */
  showSearchButton?: boolean
  /** 筛选按钮文本，默认 '筛选' */
  filterButtonText?: string
  /** 查询按钮文本，默认 '查询' */
  searchButtonText?: string
}

// ========== 表格配置类型 ==========

/**
 * 表格选择配置
 */
export interface TableSelectionConfig {
  /** 选择类型 */
  type: 'checkbox' | 'radio'
  /** 是否固定在左侧，默认 true */
  fixed?: boolean
}

/**
 * 表格配置
 */
export interface TableConfig {
  /** 行唯一标识字段 */
  rowKey: string
  /** 选择配置 */
  selection?: TableSelectionConfig
  /** 滚动配置 */
  scroll?: {
    x?: number | string
    y?: number | string
  }
  /** 是否显示边框 */
  bordered?: boolean
  /** 表格尺寸 */
  size?: 'small' | 'middle' | 'large'
}

// ========== 列配置类型 ==========

/**
 * 操作按钮配置
 */
export interface ActionConfig {
  /** 按钮唯一标识 */
  key: string
  /** 按钮 ID（权限标识） */
  id?: string
  /** 按钮文字 */
  text: string
  /** 按钮类型 */
  type?: 'link' | 'primary' | 'default'
  /** 是否危险按钮 */
  danger?: boolean
  /** 方法名称（调用 methods 中的方法） */
  action?: string
  /** 权限标识（已废弃，使用 id） */
  permission?: string
  /** 悬停提示（可选）；禁用态下作为「不可用原因」提示 */
  title?: string
}

/**
 * 值枚举配置
 */
export interface ValueEnumConfig {
  /** 显示文本 */
  text: string
  /** 状态，用于 Tag 颜色 */
  status?: 'success' | 'error' | 'warning' | 'processing' | 'default'
}

/**
 * 内置加密类型
 */
export type ProEncryptType = 'name' | 'phone' | 'idCard' | 'email'

/**
 * 加密配置
 */
export interface ProEncryptConfig {
  /**
   * 显示模式
   * - auto: 点击后显示，定时自动隐藏
   * - manual: 点击后显示，再次点击切换隐藏（默认）
   * @default 'manual'
   */
  mode?: 'auto' | 'manual'

  /**
   * 自动隐藏时长（毫秒），仅在 mode='auto' 时有效
   * @default 3000
   */
  duration?: number

  /**
   * 内置加密类型（与 encryptFn 二选一，优先使用 encryptFn）
   * @default 'name'
   */
  encryptType?: ProEncryptType

  /**
   * 自定义加密函数（优先级高于 encryptType）
   * @param value 原始值
   * @returns 加密后的值
   */
  encryptFn?: (value: any) => string

  /**
   * 图标类型
   * @default 'eye'
   */
  icon?: 'eye' | 'lock'
}

/**
 * ProTable 列配置
 */
export interface ProColumnConfig extends Omit<TableColumnType, 'customRender'> {
  /** 特殊列类型 */
  type?: 'index' | 'selection' | 'action'
  /** 值类型，用于自动渲染 */
  valueType?: 'text' | 'tag' | 'date' | 'link' | 'custom' | 'money'
  /** 金额小数位数：'origin'=原值展示, 2=保留两位, 4=保留四位，默认 2（仅在 valueType='money' 时生效） */
  moneyDecimal?: 'origin' | 2 | 4
  /** 枚举映射 */
  valueEnum?: Record<string, ValueEnumConfig>
  /** 自定义渲染函数 */
  render?: (record: any, index: number) => VNode | string
  /**
   * 自定义插槽名（页面级插槽复用）
   * 设置后，ProTable 会将同名插槽的渲染结果作为该列的 bodyCell 内容
   * 插槽会接收 record / index / column 三个参数
   */
  slotName?: string
  /**
   * 合计行自定义插槽名
   * 设置后，ProTable 会将同名插槽的渲染结果作为该列的 summaryCell 内容
   * 插槽会接收 summary（合计行数据对象）/ column 两个参数
   */
  summarySlotName?: string
  /** 操作按钮配置（type='action' 时使用） */
  actions?: ActionConfig[]
  /**
   * 加密配置
   * - true: 启用默认配置（manual 模式，常显切换，使用 name 加密）
   * - ProEncryptConfig: 详细配置
   */
  proEncrypt?: boolean | ProEncryptConfig
  /** 标签默认颜色 */
  defaultColor?: string
  /** 字典值到颜色的映射 */
  colorMap?: Record<string, string>
  /** 多级表头子列 */
  children?: ProColumnConfig[]
}

// ========== ProTable Props ==========

/**
 * 分页响应数据格式
 */
export interface PageResponse<T = any> {
  records: T[]
  total: number
}

/**
 * 按钮状态（用于权限控制）
 */
export interface ButtonStatus {
  /** 是否显示 */
  show: boolean
  /** 是否禁用 */
  disabled: boolean
  /** 悬停提示（可选）；提供时覆盖 operation.title */
  title?: string
}

/**
 * 单元格合并方法类型
 * @param record 当前行数据
 * @param rowIndex 当前行索引
 * @param records 当前表格所有行数据（用于计算连续相同值）
 * @returns { [key: string]: number } 返回需要合并的列及合并的行数，0 表示不渲染该单元格
 */
export type SpanMethod = (record: any, rowIndex: number, records: any[]) => Record<string, number>

/**
 * 单个 summary 行提取配置
 */
export interface SummaryRowConfig<T = any> {
  /** 从 responseDataPath 同级提取的字段名，如 'summary'、'summaryAll' */
  field?: string
  /** 提取函数，参数为完整 response，返回行数据或 null */
  extractor?: (response: any) => T | null
}

/**
 * ProTable 统一配置
 */
export interface ProTableConfig<T = any> {
  /** 行唯一标识字段 */
  rowKey?: string
  /** 树形表格默认展开所有行（透传给 a-table default-expand-all-rows） */
  defaultExpandAll?: boolean
  /** 数据获取 API */
  fetchApi: (params: any) => Promise<PageResponse<T>>
  /** 额外的固定参数（已废弃，请使用 fixedParams） */
  fetchParams?: Record<string, any>
  /** 固定参数，始终携带到查询接口（支持静态对象或函数，函数在每次查询时调用） */
  fixedParams?: Record<string, any> | (() => Record<string, any>)
  /** 默认搜索参数，用于初始化搜索条件（可被用户修改） */
  defaultSearchParams?: Record<string, any>
  /** 默认每页条数，默认 20 */
  defaultPageSize?: number
  /** 是否立即请求，默认 true */
  immediate?: boolean
  /** 滚动配置，默认 { x: 'max-content', y: 'flex' } */
  scroll?: {
    x?: number | string
    y?: number | string
  }
  /** 是否显示边框，默认 true */
  bordered?: boolean
  /** 表格尺寸，默认 middle */
  size?: 'small' | 'middle' | 'large'
  /** 选择配置 */
  selection?: TableSelectionConfig
  /** 搜索配置 */
  search?: SearchConfig
  /** 工具栏配置 */
  toolbar?: ToolbarConfig
  /** 列配置 */
  columns: ProColumnConfig[]
  /** 单元格合并方法 */
  spanMethod?: SpanMethod
  /**
   * 合计行配置
   * - true: 自动从响应中提取 summary（responseDataPath 末段替换为 .summary）
   * - 函数: 自定义提取函数，参数为完整响应对象，返回合计行数据或 null
   * - SummaryRowConfig[]: 多行提取数组，按元素顺序渲染
   */
  summary?: boolean | SummaryRowConfig<T>[] | ((response: any) => T | null)
  /**
   * 合计行位置
   * - 'top': 固定在表头下方（默认）
   * - 'bottom': 固定在表格底部
   */
  summaryPosition?: 'top' | 'bottom'
  /**
   * 响应数据路径，支持点号路径如 'data.rows'
   * 用于从 { data: { rows: [], total: n, summary: {} } } 这类结构中提取数据
   * 默认为 'records'，即从 response.records 取数据
   */
  responseDataPath?: string
  /**
   * 是否显示表格竖线，默认 false（全局样式默认不显示竖线）
   * 设置为 true 时显示竖线
   */
  showBorder?: boolean
  /**
   * 表格标题，显示在表格上方
   * 支持字符串或 VNode（使用 h() 创建）
   */
  title?: string | VNode
  /**
   * 表头背景色，默认 #f1f2f8
   */
  tableHeaderBg?: string
  /**
   * 报表模式开关
   * 启用后：
   * - showBorder 默认为 true
   * - searchMode 默认为 'dialog'（筛选项通过弹窗展示）
   * - toolbar 会自动注入筛选/查询按钮
   */
  reportMode?: boolean
  /**
   * 筛选项展示模式
   * - inline: 内联展示（默认）
   * - dialog: 弹窗展示（报表模式默认使用）
   */
  searchMode?: 'inline' | 'dialog'
  /**
   * 分页配置
   * - true: 启用分页（默认）
   * - false: 禁用分页（全量数据）
   * - { enabled?: boolean, pageSize?: number }: 自定义配置
   */
  pagination?: boolean | { enabled?: boolean; pageSize?: number }
}

/**
 * ProTable 方法集合（页面实现的业务方法）
 */
export type ProTableMethods<T = any> = Record<string, (record?: T, selectedRows?: T[]) => void>

/**
 * ProTable 按钮显示控制方法
 */
export type ShowButtonsMethod = (
  button: ToolbarButtonConfig | ActionConfig,
  record?: any
) => ButtonStatus

/**
 * ProTable 组件 Props
 */
export interface ProTableProps<T = any> {
  /** 统一配置对象 */
  config: ProTableConfig<T>
  /** 方法集合 */
  methods?: ProTableMethods<T>
  /** 按钮显示控制方法 */
  showButtons?: ShowButtonsMethod
  /** 搜索参数（支持 v-model:searchParams 双向绑定） */
  searchParams?: Record<string, any>
}

// ========== Hook 类型 ==========

/**
 * useProTable 配置选项
 */
export interface UseProTableOptions<T = any> {
  /** 数据获取 API */
  fetchApi: (params: any) => Promise<PageResponse<T>>
  /** 默认查询参数（已废弃，请使用 defaultSearchParams） */
  defaultParams?: Record<string, any>
  /** 默认搜索参数，用于初始化搜索条件（可被用户修改） */
  defaultSearchParams?: Record<string, any>
  /** 固定参数，始终携带到查询接口（不可被用户修改） */
  fixedParams?: Record<string, any> | (() => Record<string, any>)
  /** 默认每页条数 */
  defaultPageSize?: number
  /** 是否立即请求 */
  immediate?: boolean
  /** 合计行配置 */
  summary?: boolean | SummaryRowConfig<T>[] | ((response: any) => T | null)
  /**
   * 合计行位置
   * - 'top': 固定在表头下方（默认）
   * - 'bottom': 固定在表格底部
   */
  summaryPosition?: 'top' | 'bottom'
  /** 响应数据路径，支持点号路径如 'data.rows' */
  responseDataPath?: string
  /** 分页配置：true=启用(默认), false=禁用 */
  pagination?: boolean
  /** 缓存 key（用于 sessionStorage 持久化筛选条件） */
  cacheKey?: string
}

/**
 * 分页配置
 */
export interface PaginationConfig {
  current: number
  pageSize: number
  total: number
  showSizeChanger: boolean
  showTotal: (total: number) => string
}

/**
 * useProTable 返回值
 */
export interface UseProTableReturn<T = any> {
  /** 加载状态 */
  loading: import('vue').Ref<boolean>
  /** 表格数据 */
  dataSource: import('vue').Ref<T[]>
  /** 合计行数据 */
  summary: import('vue').Ref<T[]>
  /** 分页配置 */
  pagination: PaginationConfig
  /** 搜索参数 */
  searchParams: Record<string, any>
  /** 查询方法 */
  search: (resetPage?: boolean) => Promise<void>
  /** 重置方法 */
  reset: () => Promise<void>
  /** 刷新方法 */
  refresh: () => Promise<void>
  /** 处理表格变化 */
  handleTableChange: (pag: any) => void
}

/**
 * useSelection 返回值
 */
export interface UseSelectionReturn<T = any> {
  /** 选中的行 keys */
  selectedRowKeys: import('vue').Ref<any[]>
  /** 选中的行数据 */
  selectedRows: import('vue').Ref<T[]>
  /** 行选择配置 */
  rowSelection: import('vue').ComputedRef<any>
  /** 清空选择 */
  clearSelection: () => void
  /** 设置选择 */
  setSelection: (keys: any[], rows: T[]) => void
}
