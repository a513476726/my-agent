/**
 * ProTable 核心状态管理 Hook
 * 管理表格数据、分页、搜索等状态
 */
import { ref, shallowRef, reactive, computed, watch, onMounted } from 'vue'
import type {
  UseProTableOptions,
  UseProTableReturn,
  PaginationConfig,
  ParamFormatFn,
  SearchConfig,
} from '../types'

/** sessionStorage 缓存前缀 */
const CACHE_STORAGE_PREFIX = 'proTable_cache_'

/** 缓存数据结构：搜索参数 + 分页 */
interface ProTableCacheData {
  searchParams?: Record<string, any>
  pagination?: { current?: number; pageSize?: number }
}

/** 从 sessionStorage 加载缓存 */
function loadCachedData(key: string): ProTableCacheData | null {
  try {
    const data = sessionStorage.getItem(`${CACHE_STORAGE_PREFIX}${key}`)
    return data ? JSON.parse(data) : null
  } catch {
    return null
  }
}

/** 保存完整缓存（搜索参数 + 分页）到 sessionStorage */
function saveCachedData(key: string, data: ProTableCacheData): void {
  try {
    sessionStorage.setItem(`${CACHE_STORAGE_PREFIX}${key}`, JSON.stringify(data))
  } catch (e) {
    console.warn('[ProTable] 保存缓存到 sessionStorage 失败:', e)
  }
}

/**
 * 根据字段配置格式化参数值
 */
const formatParamValue = (value: any, paramFormat?: 'arrayJoin' | ParamFormatFn): any => {
  if (!paramFormat) return value

  // 内置格式化器
  if (paramFormat === 'arrayJoin') {
    if (Array.isArray(value)) {
      return value.join(',')
    }
    return value
  }

  // 自定义格式化函数
  if (typeof paramFormat === 'function') {
    return paramFormat(value)
  }

  return value
}

/**
 * 格式化搜索参数，支持字段级别的 paramFormat
 * 对于 dateRange 类型字段，根据 dateRangeParams 配置转换为分开的参数
 */
export const formatSearchParams = (
  params: Record<string, any>,
  searchConfig?: SearchConfig
): Record<string, any> => {
  const formatted: Record<string, any> = {}

  Object.keys(params).forEach(key => {
    const value = params[key]

    // 查找字段配置
    const fieldConfig = searchConfig?.fields?.find(f => f.field === key)

    // dateRange 类型字段使用配置的参数名进行转换
    if (fieldConfig?.name === 'dateRange') {
      if (fieldConfig.dateRangeParams) {
        // 数组或有值的数组才转换
        if (Array.isArray(value) && value.length === 2) {
          const [rawStart, rawEnd] = value
          // dateRangePadTime: true 时把 YYYY-MM-DD padding 为 YYYY-MM-DD 00:00:00 / YYYY-MM-DD 23:59:59
          // 适用于 UI / URL 都用 YYYY-MM-DD、实际请求需要时分秒边界的场景
          if (fieldConfig.dateRangePadTime) {
            formatted[fieldConfig.dateRangeParams.start] = rawStart
              ? `${String(rawStart).split(' ')[0]} 00:00:00`
              : undefined
            formatted[fieldConfig.dateRangeParams.end] = rawEnd
              ? `${String(rawEnd).split(' ')[0]} 23:59:59`
              : undefined
          } else {
            formatted[fieldConfig.dateRangeParams.start] = rawStart || undefined
            formatted[fieldConfig.dateRangeParams.end] = rawEnd || undefined
          }
        }
        // 空数组也不传参
        return
      }
      // 没有配置 dateRangeParams 时，按原逻辑处理
      if (Array.isArray(value)) {
        formatted[key] = value.join(',')
        return
      }
    }

    // 格式化值
    if (value !== undefined && value !== null && value !== '') {
      formatted[key] = formatParamValue(value, fieldConfig?.paramFormat)
    }
  })

  return formatted
}

/**
 * ProTable 核心状态管理
 * @param options 配置选项
 * @param searchConfig 搜索配置（用于参数格式化）
 * @returns 状态和方法
 */
export function useProTable<T = any>(
  options: UseProTableOptions<T>,
  searchConfig?: SearchConfig
): UseProTableReturn<T> {
  const {
    fetchApi,
    defaultParams = {},
    defaultSearchParams = {},
    fixedParams = {},
    defaultPageSize = 20,
    immediate = true,
    summary: summaryExtractor,
    responseDataPath = 'records',
    pagination: paginationEnabled = true,
    cacheKey,
  } = options

  // 是否启用分页（默认 true，pagination: false 时禁用）
  const isPaginationEnabled = computed(() => paginationEnabled)

  // 按路径从对象中提取属性，支持点号路径如 'data.rows'
  const getByPath = (obj: any, path: string): any => {
    return path.split('.').reduce((cur, key) => cur?.[key], obj)
  }

  // 加载状态
  const loading = ref(false)

  // 表格数据
  const dataSource = ref<T[]>([]) as import('vue').Ref<T[]>

  // 合计行数据（多行数组）
  const summary = shallowRef<T[]>([])

  // 搜索参数（优先使用新的 defaultSearchParams，兼容旧的 defaultParams）
  const initialSearchParams =
    Object.keys(defaultSearchParams).length > 0 ? defaultSearchParams : defaultParams

  // 如果有 cacheKey，从 sessionStorage 恢复缓存（搜索参数 + 分页）
  const cachedData = cacheKey ? loadCachedData(cacheKey) : null

  const searchParams = reactive<Record<string, any>>({
    ...initialSearchParams,
    ...(cachedData?.searchParams || {}),
  })

  // 固定参数解析器（支持静态对象或函数，函数在每次查询时调用）
  const resolveFixedParams = (): Record<string, any> => {
    if (typeof fixedParams === 'function') {
      return fixedParams()
    }
    return { ...fixedParams }
  }

  // 分页配置（从缓存恢复 current 和 pageSize）
  const pagination = reactive<PaginationConfig>({
    current: cachedData?.pagination?.current ?? 1,
    pageSize: cachedData?.pagination?.pageSize ?? defaultPageSize,
    total: 10,
    showSizeChanger: true,
    showTotal: (total: number) => `共 ${total} 条`,
  })

  // 监听 searchParams 变化，自动持久化到 sessionStorage
  // immediate:true 让 mount 时无论是否变更都立刻写一次 cache，
  // 这样 URL 穿透跳转进入后 + F5 刷新的链路也能命中 cachedData（与"直访 + 查询后"刷新行为对齐）
  watch(
    () => ({ ...searchParams }),
    val => {
      if (cacheKey) {
        saveCachedData(cacheKey, {
          searchParams: val,
          pagination: { current: pagination.current, pageSize: pagination.pageSize },
        })
      }
    },
    { deep: true, immediate: true }
  )

  // 监听 pagination 变化，自动持久化到 sessionStorage
  watch(
    () => ({ current: pagination.current, pageSize: pagination.pageSize }),
    val => {
      if (cacheKey) {
        saveCachedData(cacheKey, {
          searchParams: { ...searchParams },
          pagination: val,
        })
      }
    }
  )

  /**
   * 查询数据
   * @param resetPage 是否重置页码
   */
  const search = async (resetPage = false): Promise<void> => {
    if (resetPage && isPaginationEnabled.value) {
      pagination.current = 1
    }

    loading.value = true
    try {
      // 构建查询参数（不分页模式不发送 page/limit）
      const params: Record<string, any> = {}
      if (isPaginationEnabled.value) {
        params.page = pagination.current
        params.limit = pagination.pageSize
      }

      // 合并搜索参数，过滤空值
      Object.keys(searchParams).forEach(key => {
        const value = searchParams[key]
        if (value !== undefined && value !== null && value !== '') {
          params[key] = value
        }
      })

      // 合并固定参数（优先级最高，始终携带）
      const resolvedFixedParams = resolveFixedParams()
      Object.keys(resolvedFixedParams).forEach(key => {
        const value = resolvedFixedParams[key]
        if (value !== undefined && value !== null && value !== '') {
          // 数组类型转换为逗号分隔的字符串
          if (Array.isArray(value)) {
            params[key] = value.join(',')
          } else {
            params[key] = value
          }
        }
      })

      // 格式化搜索参数（支持 paramFormat）
      const formattedParams = formatSearchParams(params, searchConfig)

      const response = await fetchApi(formattedParams)

      // 兼容普通数组响应和 { records, summary, total } 结构
      if (Array.isArray(response)) {
        dataSource.value = response
        pagination.total = dataSource.value.length
        summary.value = []
      } else {
        // 按 responseDataPath 提取数据列表，如 'data.rows'
        const dataList = getByPath(response, responseDataPath) || []
        dataSource.value = Array.isArray(dataList) ? dataList : []

        // 提取 total：优先从 responseDataPath 同级（如 'data.rows' -> 'data.total'），无后缀则用 response.total
        const totalPath = responseDataPath.replace(/\.\w+$/, '.total')
        pagination.total = parseInt(
          String(
            totalPath !== responseDataPath ? getByPath(response, totalPath) : response.total || 0
          ) || '0'
        )

        // 提取合计行（支持 boolean / function / SummaryRowConfig[] 三种模式）
        if (Array.isArray(summaryExtractor)) {
          const rows: T[] = []
          for (const cfg of summaryExtractor) {
            const data = cfg.extractor
              ? cfg.extractor(response)
              : cfg.field
                ? getByPath(response, responseDataPath.replace(/\.\w+$/, `.${cfg.field}`))
                : null
            if (data) rows.push(data)
          }
          summary.value = rows
        } else if (typeof summaryExtractor === 'function') {
          const result = summaryExtractor(response)
          summary.value = result ? [result] : []
        } else if (summaryExtractor === true) {
          const summaryPath = responseDataPath.replace(/\.\w+$/, '.summary')
          const data = getByPath(response, summaryPath)
          summary.value = data ? [data] : []
        }
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置搜索条件并查询
   */
  const reset = async (): Promise<void> => {
    // 重置分页
    pagination.current = 1
    pagination.pageSize = defaultPageSize
    pagination.total = 0

    // 重置搜索参数（恢复到初始默认值）
    Object.keys(searchParams).forEach(key => {
      if (key in initialSearchParams) {
        searchParams[key] = initialSearchParams[key]
      } else {
        // 使用 undefined 替代 delete，避免破坏 reactive 对象的完整性
        searchParams[key] = undefined
      }
    })

    // 重新查询
    await search(true)
  }

  /**
   * 刷新当前页数据
   */
  const refresh = async (): Promise<void> => {
    await search(false)
  }

  /**
   * 处理表格变化（分页、排序等）
   */
  const handleTableChange = (pag: any): void => {
    pagination.current = pag.current
    pagination.pageSize = pag.pageSize
    search()
  }

  // 初始化加载
  onMounted(() => {
    if (immediate) {
      search(true)
    }
  })

  return {
    loading,
    dataSource,
    summary,
    pagination,
    searchParams,
    search,
    reset,
    refresh,
    handleTableChange,
  }
}
