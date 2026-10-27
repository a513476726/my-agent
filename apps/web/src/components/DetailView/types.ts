/**
 * DetailView 配置式详情组件 - 类型定义
 */
import type { VNode, Component } from 'vue'

// ==================== 值样式变体 ====================

export type ValueVariant =
  | 'default'
  | 'primary'
  | 'code'
  | 'success'
  | 'danger'
  | 'warning'
  | 'error'
  | 'processing'
  | 'money'
  | 'time'

// ==================== 字段配置 ====================

export type FieldSpan = 4 | 6 | 8 | 12 | 24

export interface FieldSpanConfig {
  xs?: number
  sm?: number
  md?: number
  lg?: number
  xl?: number
  xxl?: number
}

export interface DetailField {
  /** 字段唯一标识 */
  key: string
  /** 字段标签 */
  label: string
  /** 数据字段名（支持嵌套路径如 user.name） */
  field?: string
  /** 直接传入值（优先级高于 field） */
  value?: unknown
  /** 值样式变体 */
  variant?: ValueVariant
  /** 固定跨度（默认 6） */
  span?: FieldSpan
  /** 响应式跨度配置（优先级高于 span） */
  spans?: FieldSpanConfig
  /** 是否显示省略（默认 true） */
  ellipsis?: boolean
  /** 是否显示 tooltip（默认 true） */
  tooltip?: boolean
  /** 格式化类型 */
  format?: 'money' | 'date' | 'datetime' | 'percent' | 'duration'
  /** 自定义格式化函数 */
  formatter?: (value: unknown, record: Record<string, unknown>) => string | null
  /** 字典类型 */
  dictType?: string
  /** 静态值映射 */
  valueEnum?: Record<string, { text: string; variant?: ValueVariant; color?: string }>
  /** 状态映射 */
  statusMap?: Record<string, ValueVariant>
  /** 是否隐藏 */
  visible?: boolean | ((value: unknown, record: Record<string, unknown>) => boolean)
  /** 自定义渲染 */
  render?: (
    h: typeof import('vue').h,
    value: unknown,
    record: Record<string, unknown>
  ) => VNode | string
  /** 是否为附件字段 */
  isAttachment?: boolean
  /** 附件字段的展示模式（isAttachment=true 时生效） */
  displayMode?: 'default' | 'compact'
  /** 标签对齐方式 */
  labelAlign?: 'left' | 'right'
  /** 标签宽度 */
  labelWidth?: number | string
  /** 是否强制换行 */
  wrap?: boolean
  /** 自动换行策略 */
  wordBreak?: 'normal' | 'break-word' | 'break-all' | 'keep-all'
  /** 对接字段标记文案（如 '对接'）；提供时在标签后渲染一个小徽标 */
  tag?: string
}

// ==================== 表格配置 ====================

export interface DetailTableColumn {
  key: string
  dataIndex?: string
  title?: string
  render?: (value: unknown, record: Record<string, unknown>, index: number) => VNode | string
  customRender?: (opts: {
    text: unknown
    record: Record<string, unknown>
    index: number
  }) => VNode | string
  format?: 'money' | 'date' | 'datetime' | 'percent' | 'duration'
  width?: number | string
  align?: 'left' | 'center' | 'right'
  ellipsis?: boolean
}

export interface DetailTableConfig {
  columns: DetailTableColumn[]
  dataField?: string
  pagination?: boolean | { pageSize?: number }
  paginationPosition?: 'top' | 'bottom' | 'both'
  bordered?: boolean
  size?: 'small' | 'middle' | 'large'
  scroll?: { x?: number | string; y?: number | string }
  showHeader?: boolean
  rowClassName?: (record: Record<string, unknown>, index: number) => string
  rowKey?: string
}

// ==================== Section 配置 ====================

export type SectionType = 'fields' | 'table' | 'slot' | 'custom'

export interface DetailSection {
  key: string
  title: string
  icon?: string | Component | Record<string, unknown>
  visible?: boolean | ((data: Record<string, unknown>) => boolean)
  type: SectionType
  fields?: DetailField[]
  columns?: number
  gutter?: [number, number]
  table?: DetailTableConfig
  slot?: string
  render?: (h: typeof import('vue').h, data: Record<string, unknown>) => VNode
  class?: string
  style?: Record<string, string | number>
}

// ==================== 详情配置 ====================

export interface DetailConfig {
  sections: DetailSection[]
  defaultSpan?: FieldSpan
  defaultSpans?: FieldSpanConfig
  fieldGutter?: [number, number]
  sectionGap?: number
}

// ==================== 主组件 Props ====================

export type DetailViewMode = 'card' | 'embed' | 'modal'

export interface DetailViewProps {
  data: Record<string, unknown> | null
  config: DetailConfig
  mode?: DetailViewMode
  open?: boolean
  title?: string
  width?: string | number
  footer?: DetailViewFooter | false
  loading?: boolean
  showHeader?: boolean
  headerIcon?: string | Record<string, unknown>
  subtitle?: string
  showClose?: boolean
  /** 额外的上下文数据，用于 visible 等函数的判断 */
  extra?: Record<string, unknown>
}

export interface DetailViewFooter {
  showClose?: boolean
  closeText?: string
  closeType?: 'default' | 'primary'
  extraButtons?: Array<{
    text: string
    type?: 'primary' | 'default' | 'danger'
    danger?: boolean
    onClick: () => void
  }>
}
