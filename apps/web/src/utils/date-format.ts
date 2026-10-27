import dayjs from 'dayjs'

/**
 * 表格列渲染：统一截断为 YYYY-MM-DD
 * null / undefined / 空字符串 -> '--'
 * 非法值原样回退，避免覆盖后端真实数据
 */
export function formatDateOnly(value: unknown): string {
  if (value === null || value === undefined || value === '') return '--'
  const d = dayjs(String(value))
  return d.isValid() ? d.format('YYYY-MM-DD') : String(value)
}

/**
 * 把 YYYY-MM-DD HH:mm:ss 截断为 YYYY-MM-DD（用于 URL 渗透）
 * 空值返回空串（调用方决定是否写入 URL）
 */
export function toDateOnlyString(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  return String(value).split(' ')[0]
}

/**
 * 统一展示日期时间（本地化到秒）
 */
export function formatDateTime(value: unknown): string {
  if (value === null || value === undefined || value === '') return '--'
  const date = dayjs(String(value))
  return date.isValid() ? date.format('YYYY-MM-DD HH:mm:ss') : String(value)
}
