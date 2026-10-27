<template>
  <a-card
    class="pro-table-container"
    :class="{ 'report-mode': config.reportMode, 'no-shadow': props.noShadow }"
  >
    <div class="pro-table">
      <!-- 表格标题 -->
      <div v-if="config.title" class="pro-table__title">
        <h3 v-if="typeof config.title === 'string'" class="pro-table__title-text">
          {{ config.title }}
        </h3>
        <component :is="config.title" v-else />
      </div>

      <!-- 搜索区域 -->
      <div v-if="showSearchBar" ref="searchBarRef">
        <SearchBar
          class="pro-table__search"
          ref="searchBarComponentRef"
          :model-value="searchParams"
          :config="config.search!"
          :search-mode="searchMode"
          @update:model-value="onSearchParamsModelValue"
          @change="handleSearchBarChange"
          @search="handleSearch"
          @reset="handleReset"
        />
      </div>

      <!-- 工具栏区域 -->
      <div v-if="hasToolbar" ref="toolbarRef" class="pro-table__toolbar">
        <Toolbar
          :config="config.toolbar"
          :selected-rows="selectedRows"
          :methods="methods"
          :show-buttons="showButtons"
          :report-mode="config.reportMode"
          :important-fields="searchBarComponentRef?.importantFields ?? []"
          :has-dialog-fields="(searchBarComponentRef?.dialogFields ?? []).length > 0"
          :search-params="searchParams"
          :on-field-change="handleSearchBarFieldChange"
          :on-search="handleSearch"
          :on-change="handleSearchBarChange"
          @search="handleSearch"
          @open-filter-dialog="handleOpenFilterDialog"
        />
      </div>

      <!-- 表格区域 -->
      <div
        ref="tableBodyRef"
        class="pro-table__body"
        :class="{ 'pro-table__body--empty': isTableEmpty }"
        :style="{
          '--table-border': isShowBorder ? '1px solid #ededed' : '1px solid transparent',
          '--table-header-bg': config.tableHeaderBg || '#f1f2f8',
        }"
      >
        <a-table
          :columns="processedColumns"
          :data-source="dataSource"
          :loading="loading"
          :pagination="tablePagination"
          :row-selection="rowSelection"
          :row-key="config.rowKey"
          :expanded-row-keys="expandedRowKeys"
          :scroll="tableScroll"
          :bordered="config.bordered ?? true"
          :size="config.size ?? 'small'"
          @expand="handleExpand"
          @change="handleTableChange"
        >
          <!-- 自定义单元格渲染 -->
          <template #bodyCell="{ column, record, index }">
            <!-- 加密列 -->
            <template v-if="column.proEncrypt">
              <EncryptedCell
                :value="record[column.dataIndex]"
                :config="normalizeEncryptConfig(column.proEncrypt)"
                :data-index="column.dataIndex"
              />
            </template>

            <!-- 序号列 -->
            <template v-else-if="column.type === 'index'">
              {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
            </template>

            <!-- 标签列 -->
            <template v-else-if="column.valueType === 'tag' && column.valueEnum">
              <a-tag
                v-if="getValueEnumItem(column.valueEnum, record[column.dataIndex])"
                :color="
                  getTagColor(getValueEnumItem(column.valueEnum, record[column.dataIndex])?.status)
                "
              >
                {{ getValueEnumItem(column.valueEnum, record[column.dataIndex])?.text }}
              </a-tag>
              <span v-else>{{ record[column.dataIndex] ?? '--' }}</span>
            </template>

            <!-- 金额列 -->
            <template v-else-if="column.valueType === 'money'">
              <span>{{ formatMoney(record[column.dataIndex], column.moneyDecimal) }}</span>
            </template>

            <!-- 操作列 -->
            <template v-else-if="column.type === 'action' && column.actions">
              <ActionColumn
                :actions="column.actions"
                :record="record"
                :methods="methods"
                :show-buttons="showButtons"
              />
            </template>

            <!-- 自定义渲染 -->
            <template v-else-if="column.render">
              <component :is="() => column.render!(record, index)" />
            </template>

            <!-- 自定义插槽名（页面级插槽复用：多列共用一个插槽） -->
            <template v-else-if="column.slotName && $slots[column.slotName]">
              <slot
                :name="column.slotName"
                :record="record"
                :index="index"
                :data-index="column.dataIndex"
              />
            </template>

            <!-- 默认渲染 - 使用插槽或默认值 -->
            <template v-else-if="$slots[column.dataIndex || column.key]">
              <slot :name="column.dataIndex || column.key" :record="record" :index="index" />
            </template>

            <!-- 默认数据渲染 - 空数据显示 -- -->
            <template v-else>
              <span>{{ record[column.dataIndex] ?? '--' }}</span>
            </template>
          </template>

          <!-- 合计行 -->
          <template #summary>
            <a-table-summary v-if="summary.length > 0" :fixed="config.summaryPosition ?? 'top'">
              <a-table-summary-row v-for="(summaryRow, rowIndex) in summary" :key="rowIndex">
                <a-table-summary-cell
                  v-for="(col, colIndex) in flatColumns"
                  :key="colIndex"
                  :align="col.align ?? 'center'"
                  :style="getSummaryCellStyle(col, summaryStickyOffsets[colIndex])"
                >
                  <template v-if="col.summarySlotName && $slots[col.summarySlotName]">
                    <slot
                      :name="col.summarySlotName"
                      :summary="summaryRow"
                      :column="col"
                      :record="summaryRow"
                      :index="rowIndex"
                      :data-index="col.dataIndex"
                    />
                  </template>
                  <template v-else>
                    {{ getSummaryValue(col, summaryRow) }}
                  </template>
                </a-table-summary-cell>
              </a-table-summary-row>
            </a-table-summary>
          </template>
        </a-table>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

import SearchBar from './components/SearchBar/index.vue'
import Toolbar from './components/Toolbar.vue'
import ActionColumn from './components/ActionColumn.vue'
import EncryptedCell from './components/EncryptedCell.vue'
import { useProTable, formatSearchParams } from './hooks/useProTable'
import { useSelection } from './hooks/useSelection'
import type { ProTableConfig, ProTableMethods, ShowButtonsMethod, ProEncryptConfig } from './types'

interface Props<T = any> {
  /** 统一配置对象 */
  config: ProTableConfig<T>
  /** 方法集合 */
  methods?: ProTableMethods
  /** 按钮显示控制方法 */
  showButtons?: ShowButtonsMethod
  /** 搜索参数（支持 v-model:searchParams 双向绑定） */
  searchParams?: Record<string, any>
  /** 是否为报表模式 */
  reportMode?: boolean
  /** 是否在弹窗内（去阴影） */
  noShadow?: boolean
  /** 缓存 key（用于 sessionStorage 持久化筛选条件，必须显式传入，不传则不缓存） */
  cacheKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  methods: undefined,
  showButtons: undefined,
  searchParams: undefined,
  reportMode: false,
  noShadow: false,
  cacheKey: undefined,
})

const emit = defineEmits<{
  'update:searchParams': [value: Record<string, any>]
  'data-loaded': [data: any[]]
  'selection-change': [rows: any[]]
  change: [payload: { field: string; value: any; searchParams: Record<string, any> }]
}>()

// DOM 引用
const searchBarRef = ref<HTMLElement>()
const searchBarComponentRef = ref<InstanceType<typeof SearchBar>>()
const toolbarRef = ref<HTMLElement>()
const tableBodyRef = ref<HTMLElement>()

// 树形展开 key 集合（受控模式）。用 expandedRowKeys 而非 defaultExpandAllRows：
// 数据是异步加载（首帧为空），defaultExpandAllRows 只在初始渲染生效，展开不生效。
const expandedRowKeys = ref<Array<string | number>>([])

/**
 * 收集树数据里所有含 children 的父级 rowKey（递归），用于默认展开全部父级。
 * @param rows 树行数组
 * @param acc 累积输出数组
 */
function collectParentKeys(rows: any[], acc: Array<string | number>): void {
  for (const row of rows) {
    if (row && Array.isArray(row.children) && row.children.length > 0) {
      acc.push(row[props.config.rowKey as string] ?? row.key)
      collectParentKeys(row.children, acc)
    }
  }
}

/**
 * 树形行展开/收起：受控 expandedRowKeys 需手动增删，保证用户交互与默认展开状态共存。
 * @param expanded 是否展开
 * @param record 当前行
 */
function handleExpand(expanded: boolean, record: any): void {
  if (!props.config.defaultExpandAll) return
  const key = record?.[props.config.rowKey as string] ?? record?.key
  if (key == null) return
  const set = new Set(expandedRowKeys.value)
  if (expanded) {
    set.add(key)
  } else {
    set.delete(key)
  }
  expandedRowKeys.value = [...set]
}

// 动态表格滚动高度
const tableScrollY = ref<number>(0)

// cacheKey 必须显式传入，不传则不缓存
// （移除 inject 自动获取逻辑，避免内嵌 ProTable 与父列表共享 cacheKey 导致参数污染）
const effectiveCacheKey = computed(() => props.cacheKey || undefined)

// 使用 useProTable hook
const {
  loading,
  dataSource,
  summary,
  pagination,
  searchParams,
  search,
  reset,
  refresh,
  handleTableChange: onTableChange,
} = useProTable(
  {
    fetchApi: props.config.fetchApi,
    defaultSearchParams: props.searchParams || props.config.defaultSearchParams,
    fixedParams: props.config.fixedParams || props.config.fetchParams, // 兼容旧的 fetchParams
    defaultPageSize: props.config.defaultPageSize ?? 20,
    immediate: props.config.immediate ?? true,
    summary: props.config.summary,
    responseDataPath: props.config.responseDataPath,
    pagination: props.config.pagination !== false, // 默认启用分页
    cacheKey: effectiveCacheKey.value || undefined,
  },
  props.config.search // 传递 searchConfig 用于参数格式化
)

// 列表无数据（请求结束且无行）时给表格容器加高度，让空态撑满；有数据时保持原布局
const isTableEmpty = computed(() => {
  return !loading.value && (dataSource.value?.length ?? 0) === 0
})

// dataSource 变化（异步加载/搜索/分页/重置）时，defaultExpandAll 的树默认展开全部父级。
// 用受控 expandedRowKeys：异步数据首帧为空，defaultExpandAllRows 只在初始渲染生效故失效。
watch(
  dataSource,
  rows => {
    if (!props.config.defaultExpandAll) {
      // 非默认展开的树：不干预展开状态（可能无树数据）
      return
    }
    const keys: Array<string | number> = []
    collectParentKeys((rows || []) as any[], keys)
    expandedRowKeys.value = keys
  },
  { immediate: true }
)

// 初始化搜索参数的默认值（从 search.fields 中的 defaultValue）
if (props.config.search?.fields) {
  props.config.search.fields.forEach(field => {
    // 如果 field 设置了 defaultValue 且 searchParams 中还没有该值，则设置
    if (field.defaultValue !== undefined && searchParams[field.field] === undefined) {
      searchParams[field.field] = field.defaultValue
    }
  })
}

// 监听 searchParams 变化，触发 update:searchParams 事件
watch(
  () => ({ ...searchParams }),
  newParams => {
    emit('update:searchParams', newParams)
  },
  { deep: true }
)

// 使用 useSelection hook
const {
  selectedRowKeys,
  selectedRows,
  rowSelection: baseRowSelection,
  clearSelection,
} = useSelection(props.config.selection)

// 监听选择变化，通知父组件
watch(
  () => selectedRows.value,
  newRows => {
    if (props.config.selection) {
      emit('selection-change', newRows)
    }
  },
  { immediate: true }
)

// 行选择配置
const rowSelection = computed(() => {
  if (!props.config.selection) return undefined
  return baseRowSelection.value
})

// 是否启用分页
const isPaginationEnabled = computed(() => {
  return props.config.pagination !== false
})

// 表格分页配置
const tablePagination = computed(() => {
  if (!isPaginationEnabled.value) return false
  return {
    ...pagination,
    total: pagination.total,
    onChange: undefined,
    onShowSizeChange: undefined,
    hideOnSinglePage: false, // 始终显示分页器，即使没有数据
    showSizeChanger: true, // 显示可切换每页条数
    showQuickJumper: false, // 不显示快速跳转
    showTotal: (total: number) => `共 ${dataSource.value.length === 0 ? 0 : total} 条`, // 中文显示总数
    pageSizeOptions: ['20', '50', '100', '200'], // 每页条数选项
    buildOptionText: ({ value }: { value: number }) => `${value}条 / 页`, // 每页条数文本
    // 确保分页器始终渲染
    simple: false,
    size: props.config.reportMode ? 'small' : 'default',
  }
})

// 表格滚动配置
const tableScroll = computed(() => {
  return {
    x: props.config.scroll?.x || 'max-content',
    y: tableScrollY.value > 0 ? tableScrollY.value : undefined,
  }
})

// 报表模式：筛选项展示模式
const searchMode = computed(() => {
  return props.config.searchMode ?? (props.config.reportMode ? 'dialog' : 'inline')
})

// 报表模式：是否显示竖线
const isShowBorder = computed(() => {
  return props.config.reportMode || props.config.showBorder
})

// 是否有工具栏内容
const hasToolbar = computed(() => {
  if (!props.config.toolbar) return false
  const { leftButtons = [], rightButtons = [] } = props.config.toolbar
  return leftButtons.length > 0 || rightButtons.length > 0 || props.config.reportMode
})

// 是否显示搜索区域（dialog 模式下也渲染 SearchBar，以便 Toolbar 通过 ref 获取 importantFields）
const showSearchBar = computed(() => {
  return props.config.search && props.config.search.fields.length > 0
})

/** 单元格合并：列 → spanMethod 返回对象的 key */
const resolveSpanColumnKey = (col: any): string | null => {
  if (col.dataIndex != null && col.dataIndex !== '') {
    return Array.isArray(col.dataIndex) ? col.dataIndex.join('.') : String(col.dataIndex)
  }
  if (col.type === 'action') return '__action__'
  return null
}

// 处理列配置，添加必要的属性
const processedColumns = computed(() => {
  const records = dataSource.value ?? []
  const spanMethodFn = props.config.spanMethod

  const processColumn = (col: any): any => {
    const processed: any = { ...col }

    // 序号列特殊处理
    if (col.type === 'index') {
      processed.key = 'index'
    }

    // 操作列居中
    if (col.type === 'action') {
      processed.align = processed.align || 'center'
      processed.key = processed.key || 'action'
    }

    // 默认 ellipsis: true（除非显式设为 false）
    if (processed.ellipsis === undefined) {
      processed.ellipsis = true
    }

    const spanColumnKey = resolveSpanColumnKey(col)
    if (spanMethodFn && spanColumnKey) {
      const prevCustomCell = col.customCell
      processed.customCell = (record: any, rowIndex: number, column: any) => {
        const spanMap = spanMethodFn(record, rowIndex, records)
        const rowSpan = spanMap[spanColumnKey] ?? 1
        const prev = prevCustomCell ? prevCustomCell(record, rowIndex, column) : {}
        return { ...prev, rowSpan }
      }
    }

    // 递归处理多级表头 children
    if (processed.children && Array.isArray(processed.children)) {
      processed.children = processed.children.map((child: any) => processColumn(child))
    }

    return processed
  }
  return props.config.columns.map(col => processColumn(col))
})

// 展平多级表头，获取所有叶子列（用于 summary 行按顺序渲染）
const flatColumns = computed(() => {
  const result: any[] = []
  const flatten = (cols: any[]) => {
    for (const col of cols) {
      if (col.children?.length) {
        flatten(col.children)
      } else {
        result.push(col)
      }
    }
  }
  flatten(props.config.columns)
  return result
})

// 计算 summary 行的 sticky 偏移量（左侧 fixed 列累计 left 偏移）
// ant-design-vue 的 a-table-summary-cell 不支持 fixed prop，需通过 CSS position: sticky 手动实现
const summaryStickyOffsets = computed(() => {
  const result: number[] = []
  let cumulativeLeft = 0
  for (const col of flatColumns.value) {
    if (col.fixed === 'left') {
      result.push(cumulativeLeft)
      cumulativeLeft += typeof col.width === 'number' ? col.width : 0
    } else {
      result.push(0)
    }
  }
  return result
})

// 生成 summary 单元格的 style：处理 width + 左侧 fixed 列的 sticky 行为
const getSummaryCellStyle = (col: any, stickyOffset: number) => {
  const style: Record<string, string | number> = {}
  // 显式设置 minWidth 保证宽度一致
  if (col.width !== undefined) {
    const w = typeof col.width === 'number' ? `${col.width}px` : col.width
    style.minWidth = w
    style.width = w
  }
  // 左侧 fixed 列：使用 position: sticky 模拟水平方向固定
  if (col.fixed === 'left') {
    style.position = 'sticky'
    style.left = `${stickyOffset}px`
    style.zIndex = 2
    // 背景色防止滚动时透明穿透
    style.background = '#fff'
  }
  return style
}

// 获取 summary 单元格的值（支持嵌套 dataIndex 如 ['total', 'unitCnt']）
const getSummaryValue = (column: any, summaryData?: any) => {
  const data = summaryData ?? summary.value
  if (!data || !column.dataIndex) return ''
  const di = column.dataIndex
  if (Array.isArray(di)) {
    return di.reduce((obj: any, key: string) => obj?.[key], data) ?? ''
  }
  return data[di] ?? ''
}

/**
 * 获取标签颜色
 */
const getValueEnumItem = (
  valueEnum: Record<string, { text?: string; status?: string }>,
  value: unknown
) => {
  if (value == null || value === '') return undefined
  return valueEnum[String(value)]
}

const getTagColor = (status?: string): string => {
  const colorMap: Record<string, string> = {
    success: 'success',
    error: 'error',
    warning: 'warning',
    processing: 'processing',
    default: 'default',
  }
  return colorMap[status || 'default'] || 'default'
}

/**
 * 格式化金额：千分符 + 可控小数位数
 * @param value 原始值
 * @param decimal 小数位数：'origin'=原值, 2=两位, 4=四位，默认 2
 */
const formatMoney = (value: any, decimal: 'origin' | 2 | 4 = 2): string => {
  if (value === null || value === undefined || value === '') return '--'
  // 后端有时会把金额预格式化为带千分符的字符串（如 "1,468.55"），先把逗号去掉再 parse，保留小数点
  const num = Number(String(value).replace(/,/g, ''))
  if (isNaN(num)) return '--'
  if (decimal === 'origin') return String(value)
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimal,
    maximumFractionDigits: decimal,
  })
}

/**
 * 规范化加密配置
 */
const normalizeEncryptConfig = (config: boolean | ProEncryptConfig): ProEncryptConfig => {
  if (typeof config === 'boolean') {
    return {
      mode: 'manual',
      duration: 3000,
      encryptType: 'name',
      icon: 'eye',
    }
  }
  return {
    mode: config.mode || 'manual',
    duration: config.duration || 3000,
    icon: config.icon || 'eye',
    encryptType: config.encryptType || 'name',
    ...config,
  }
}

/**
 * 合并到 useProTable 的 reactive searchParams，禁止整体替换引用。
 * 清空搜索会 emit 新对象；若用 v-model 直接替换，子组件绑到新对象，search() 仍读旧 reactive，再输入不会带进请求。
 */
function onSearchParamsModelValue(val: Record<string, any>) {
  if (val === searchParams) {
    return
  }
  Object.keys(searchParams).forEach(k => delete searchParams[k])
  Object.assign(searchParams, val)
}

/**
 * 处理 Toolbar 中关键筛选项字段变化（直接更新 SearchBar 的 modelValue）
 */
function handleSearchBarFieldChange(field: string, value: any) {
  if (searchParams[field] !== value) {
    searchParams[field] = value
  }
}

/**
 * 处理 SearchBar 任意字段变化的 change 事件，
 * 同步更新 searchParams，确保依赖它的其他字段（如分期依赖项目）能及时响应。
 */
function handleSearchBarChange(payload: {
  field: string
  value: any
  searchParams: Record<string, any>
}) {
  if (!payload) return
  const { field, value } = payload
  if (searchParams[field] !== value) {
    searchParams[field] = value
  }
  emit('change', payload)
}

/**
 * 处理搜索
 */
const handleSearch = () => {
  clearSelection()
  search(true)
}

/**
 * 处理重置
 */
const handleReset = () => {
  clearSelection()
  reset()
}

/**
 * 打开筛选弹窗（报表模式）
 */
const handleOpenFilterDialog = () => {
  searchBarComponentRef.value?.openDialog()
}

/**
 * 处理表格变化
 */
const handleTableChange = (pag: any, _filters: any, _sorter: any) => {
  onTableChange(pag)
}

/**
 * 计算表格可用滚动高度（V2 简化版）
 * 从 pro-table__body 层级计算，只需减去表头和分页器高度
 */
const recalculateTableHeight = () => {
  nextTick(() => {
    if (!tableBodyRef.value) return

    // 获取 .pro-table__body 容器的可用高度
    const containerHeight = tableBodyRef.value.clientHeight

    // 固定高度常量
    const headerEl = tableBodyRef.value.querySelector('.ant-table-header')
    const tableHeaderHeight = headerEl ? headerEl.clientHeight : 46 // 表头高度（动态获取，多级表头时自适应）
    // 报表模式分页器更小：small模式分页器高度约32px，无margin
    const paginationHeight = props.config.reportMode ? 32 : 40 // 分页器高度
    const paginationMargin = props.config.reportMode ? 0 : 16 // 分页器上边距
    const summaryRowHeight = 46 // 合计行高度

    // 计算表格 body 可滚动高度（减去表头、分页器、合计行高度）
    // 根据 config.summary / summaryAll 配置判断（有配置就预扣空间，无需等待异步数据）
    const hasSummaryConfig = props.config.summary !== undefined && props.config.summary !== false
    const summaryRowCount = Array.isArray(props.config.summary)
      ? props.config.summary.length
      : hasSummaryConfig
        ? 1
        : 0
    const summaryTotalHeight = summaryRowCount * summaryRowHeight
    // 不分页模式时不扣减分页器高度
    const paginationHeightOffset = isPaginationEnabled.value
      ? paginationHeight + paginationMargin
      : 0
    const calculatedHeight =
      containerHeight - paginationHeightOffset - tableHeaderHeight - summaryTotalHeight

    // 确保高度为正数，最小 100px
    tableScrollY.value = calculatedHeight > 100 ? calculatedHeight : 100

    // // 🐛 调试日志：输出所有高度计算值
    // console.group('📊 ProTable 高度计算详情 (V2 简化版)')
    // console.log('1️⃣ 容器高度 (.pro-table__body):', containerHeight + 'px')
    // console.log('2️⃣ 表头高度 (固定):', tableHeaderHeight + 'px')
    // console.log('3️⃣ 分页器高度 (固定):', paginationHeight + 'px')
    // console.log('4️⃣ 分页器上边距 (固定):', paginationMargin + 'px')
    // console.log('---')
    // console.log('计算公式:', `${containerHeight} - ${paginationHeight}`)
    // console.log('= 计算结果:', calculatedHeight + 'px')
    // console.log('✅ 最终 tableScrollY:', tableScrollY.value + 'px')
    // console.groupEnd()
  })
}

/**
 * 防抖的高度计算函数
 */
let resizeTimer: ReturnType<typeof setTimeout> | null = null
const debouncedRecalculate = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = setTimeout(() => {
    recalculateTableHeight()
  }, 100)
}

// 生命周期钩子
onMounted(() => {
  // 初始计算
  nextTick(() => {
    recalculateTableHeight()
  })

  // 监听搜索栏高度变化
  if (searchBarRef.value) {
    const resizeObserver = new ResizeObserver(debouncedRecalculate)
    resizeObserver.observe(searchBarRef.value)

    // 保存 observer 以便卸载时清理
    onUnmounted(() => {
      resizeObserver.disconnect()
    })
  }

  // 监听窗口 resize
  window.addEventListener('resize', debouncedRecalculate)
})

onUnmounted(() => {
  window.removeEventListener('resize', debouncedRecalculate)
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
})

// 暴露方法供父组件调用
defineExpose({
  /** 刷新表格 */
  refresh,
  /** 重置并查询 */
  reset,
  /** 查询 */
  search,
  /** 获取选中行 */
  getSelectedRows: () => selectedRows.value,
  /** 获取选中行 keys */
  getSelectedRowKeys: () => selectedRowKeys.value,
  /** 清空选择 */
  clearSelection,
  /** 获取搜索参数 */
  getSearchParams: () => formatSearchParams({ ...searchParams }, props.config.search),
  /** 搜索参数响应式对象（用于监听变化） */
  searchParams,
  /** 获取数据源 */
  getDataSource: () => dataSource.value,
})
</script>

<style scoped lang="less">
@report-mode-gap: 8px;

.pro-table-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: 1px 1px 9px 0px #cfcfcf6e;

  &.no-shadow {
    box-shadow: none;
  }

  :deep(.ant-card-body) {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 16px;
  }
}

.pro-table {
  display: flex;
  flex-direction: column;
  height: 100%;

  &__title {
    flex-shrink: 0;
    font-size: 16px;
    font-weight: 500;
    color: #333;

    &-text {
      margin: 0;
      text-align: center;
      font-size: 22px;
      font-weight: 500;
      color: #333;
    }
  }

  &__search {
    flex-shrink: 0;
    margin-bottom: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  &__toolbar {
    flex-shrink: 0;
    margin-bottom: 16px;
  }

  // 报表模式：紧凑间距
  .report-mode & {
    &__search {
      margin-bottom: @report-mode-gap;
    }

    &__toolbar {
      margin-bottom: @report-mode-gap;
    }

    :deep(.ant-card-body) {
      padding: @report-mode-gap;
    }

    :deep(.ant-table-pagination) {
      margin: @report-mode-gap 0 0 0 !important;
    }
  }

  &__body {
    flex: 1;
    min-height: 0;
    overflow: hidden;

    :deep(.ant-table-cell) {
      border-inline-end: var(--table-border, none) !important;
    }

    :deep(.ant-table-wrapper) {
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    :deep(.ant-table-wrapper table) {
      // height: 100%;
    }

    &.pro-table__body--empty :deep(.ant-table-wrapper table) {
      height: 100%;
    }

    :deep(.ant-spin-nested-loading) {
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    :deep(.ant-spin-container) {
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    :deep(.ant-table) {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    :deep(.ant-table-container) {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    :deep(.ant-table-header) {
      flex-shrink: 0;
    }

    :deep(.ant-table-body) {
      flex: 1;
      overflow-y: auto !important;
      overflow-x: auto !important;
    }

    :deep(.ant-table-pagination) {
      flex-shrink: 0;
      margin: 16px 0 0 0 !important;
      visibility: visible !important;
      opacity: 1 !important;
      display: flex !important;
      float: none !important;
      position: relative !important;
    }

    :deep(.ant-pagination) {
      visibility: visible !important;
      opacity: 1 !important;
    }
  }
}

:deep(.ant-table-thead > tr > th) {
  background-color: var(--table-header-bg, #f1f2f8) !important;
  font-weight: normal;
}

:deep(.ant-table-wrapper .ant-table.ant-table-small .ant-table-tbody > tr > td) {
  padding: 4px 8px;
}
</style>
