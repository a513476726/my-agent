/**
 * 从当前路由 query 中按映射提取搜索参数初始化值（setup 同步执行，仅一次）
 *
 * 设计原则：
 * 1. 一次性：不监听 route.query 变化，避免用户手动改 URL 覆盖已选筛选
 * 2. 纯函数：返回 plain object，调用方 spread 到 defaultSearchParams
 * 3. 安全：仅接受非空 string 值（trim 后）
 *
 * 适用场景：跨页穿透查询（如顾问业绩 → 渠道成交表，携带 projectId 自动回显）
 *
 * @param mapping { [searchParamsField]: queryKey } 字段名 → URL query key 的映射
 * @returns 从 route.query 提取的搜索参数对象
 *
 * @example
 * ```ts
 * const initParams = useRouteSearchInit({ projectId: 'projectId' })
 * const tableConfig = ref({
 *   ...baseTableConfig,
 *   defaultSearchParams: { ...baseTableConfig.defaultSearchParams, ...initParams }
 * })
 * ```
 */
import { useRoute } from 'vue-router'

export function useRouteSearchInit(mapping: Record<string, string>): Record<string, any> {
  const route = useRoute()
  const result: Record<string, any> = {}
  for (const [fieldName, queryKey] of Object.entries(mapping)) {
    const raw = route.query[queryKey]
    const value = Array.isArray(raw) ? raw[0] : raw
    if (typeof value === 'string' && value.trim() !== '') {
      result[fieldName] = value.trim()
    }
  }
  return result
}
