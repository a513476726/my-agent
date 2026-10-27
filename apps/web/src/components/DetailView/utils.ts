/**
 * DetailView 配置式详情组件 - 工具函数
 */
import dayjs from '@/plugins/dayjs'
import type { DetailField, ValueVariant } from './types'

/**
 * 获取嵌套属性值
 */
export function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  if (!path) return undefined
  return path.split('.').reduce((acc: unknown, key: string) => {
    if (acc && typeof acc === 'object') {
      return (acc as Record<string, unknown>)[key]
    }
    return undefined
  }, obj)
}

/**
 * 格式化金额
 */
export function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === '') return '--'
  const n = Number(v)
  if (Number.isNaN(n)) return '--'
  return n.toFixed(2).replace(/(\d)(?=(\d{3})+\.)/g, '$1,')
}

/**
 * 格式化日期
 */
export function formatDate(v: unknown): string {
  if (!v) return '--'
  const val = typeof v === 'number' ? v : String(v)
  if (/^\d{10}$/.test(String(val))) return dayjs.unix(Number(val)).format('YYYY-MM-DD')
  if (/^\d{13}$/.test(String(val))) return dayjs(Number(val)).format('YYYY-MM-DD')
  return String(v)
}

/**
 * 格式化日期时间
 */
export function formatDateTime(v: unknown): string {
  if (!v) return '--'
  const val = typeof v === 'number' ? v : String(v)
  if (/^\d{10}$/.test(String(val))) return dayjs.unix(Number(val)).format('YYYY-MM-DD HH:mm')
  if (/^\d{13}$/.test(String(val))) return dayjs(Number(val)).format('YYYY-MM-DD HH:mm')
  return String(v)
}

/**
 * 格式化百分比
 */
export function formatPercent(v: unknown): string {
  if (v === null || v === undefined || v === '') return '--'
  return `${Number(v).toFixed(2)}%`
}

/**
 * 格式化时长
 */
export function formatDuration(v: unknown): string {
  if (v === null || v === undefined || v === '') return '--'
  const seconds = Number(v)
  if (Number.isNaN(seconds)) return '--'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

/**
 * 格式化值
 */
export function formatValue(value: unknown, format?: string): string {
  if (value === null || value === undefined || value === '') return '--'

  switch (format) {
    case 'money':
      return formatMoney(value)
    case 'date':
      return formatDate(value)
    case 'datetime':
      return formatDateTime(value)
    case 'percent':
      return formatPercent(value)
    case 'duration':
      return formatDuration(value)
    default:
      return String(value)
  }
}

/**
 * 解析字段值
 */
export function resolveFieldValue(field: DetailField, data: Record<string, unknown>): unknown {
  const rawValue = field.value ?? getNestedValue(data, field.field ?? '')

  // 注意：render 不在此处执行。FieldItem 拿到本函数返回的原始值后，
  // 自行以 (h, rawValue, data) 调用 field.render；此处若调用会传入错误实参，
  // 且会让 rawValue 变成 VNode，破坏空值判断与 tooltip。

  if (field.formatter) {
    return field.formatter(rawValue, data)
  }

  if (field.format) {
    return formatValue(rawValue, field.format)
  }

  if (field.dictType) {
    return rawValue
  }

  if (field.valueEnum && rawValue != null) {
    const entry = field.valueEnum[String(rawValue)]
    return entry?.text ?? '--'
  }

  if (rawValue === null || rawValue === undefined || rawValue === '') return '--'
  return rawValue
}

/**
 * 解析字段样式变体
 */
export function resolveFieldVariant(
  field: DetailField,
  data: Record<string, unknown>
): ValueVariant {
  const rawValue = field.value ?? getNestedValue(data, field.field ?? '')

  if (field.statusMap && rawValue != null && rawValue !== '') {
    const variant = field.statusMap[String(rawValue)]
    if (variant) return variant
  }

  if (field.valueEnum && rawValue != null && rawValue !== '') {
    const entry = field.valueEnum[String(rawValue)]
    if (entry?.variant) return entry.variant
  }

  return field.variant || 'default'
}

/**
 * 判断字段是否可见
 */
export function isFieldVisible(field: DetailField, data: Record<string, unknown>): boolean {
  if (typeof field.visible === 'function') {
    const value = field.value ?? getNestedValue(data, field.field ?? '')
    return field.visible(value, data)
  }
  return field.visible !== false
}

/**
 * 解析字段跨度
 */
export function resolveFieldSpans(
  field: DetailField,
  defaultSpans?: { xs?: number; sm?: number; md?: number; lg?: number; xl?: number }
): Record<string, number> {
  if (field.spans) {
    return { ...defaultSpans, ...field.spans }
  }

  const span = field.span || 6
  return {
    // 响应式栅格：以 span 为该字段在"空间充足时"所占列数（span 是 24 的分母）。
    // 仅当窗口极窄(xs)时折为整行(24)，其余宽度(>=sm)保持 span 占比，
    // 使宽窗口每行放下 span 对应数量的字段(span=12 → 2 个/行)，窄窗口自动换行。
    xs: 24,
    sm: span,
    md: span,
    lg: span,
    xl: span,
    xxl: span,
    ...defaultSpans,
  }
}
