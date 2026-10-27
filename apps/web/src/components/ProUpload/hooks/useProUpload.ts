/**
 * ProUpload Hook - 上传组件核心逻辑
 * @description 包含所有业务逻辑：上传配置、文件校验、JSON序列化、预览判断等
 */
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import type { UploadChangeParam } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { STORAGE_KEYS } from '@/constants'
import type {
  ProUploadProps,
  ProUploadFileListItem,
  ProUploadDefaultFileItem,
  ProUploadPreviewState,
} from '../types'

// ==================== 类型定义 ====================

/**
 * 上传配置（内部使用）
 */
export interface UploadConfig {
  action: string
  headers: Record<string, string>
  data: Record<string, any> | ((file: File) => Record<string, any>) | undefined
}

// ==================== Hook ====================

/**
 * ProUpload 组件核心逻辑 Hook
 * @param props 组件 Props
 * @param emit 组件 Emit
 */
export function useProUpload(props: ProUploadProps, emit: any) {
  const authStore = useAuthStore()

  // 文件列表状态
  const fileList = ref<ProUploadFileListItem[]>([])
  const isUploading = ref(false)

  // ==================== 计算属性 ====================

  /** 默认上传地址；业务页面可通过 customConfig.uploadUrl 覆盖 */
  const DEFAULT_UPLOAD_URL = '/api/files/upload'

  /** 获取上传地址 */
  const uploadUrl = computed(() => {
    return props.customConfig?.uploadUrl || DEFAULT_UPLOAD_URL
  })

  /** 获取上传请求头 */
  const uploadHeaders = computed(() => {
    const token = authStore.access_token || localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || ''
    return { Authorization: `Bearer ${token}` }
  })

  /** 获取上传数据 */
  const uploadDataComputed = computed(() => {
    if (props.customConfig?.uploadData) {
      return props.customConfig.uploadData
    }
    if (props.businessId) {
      return { sellchanceId: props.businessId }
    }
    return undefined
  })

  /** 是否达到上传上限 */
  const isMaxCountReached = computed(() => {
    return fileList.value.filter(item => item.status === 'done').length >= (props.maxCount ?? 1)
  })

  /** 已完成的文件数量 */
  const doneFileCount = computed(() => {
    return fileList.value.filter(item => item.status === 'done').length
  })

  /** accept 描述文本 */
  const acceptText = computed(() => {
    if (!props.accept) return ''
    const acceptList = props.accept.split(',').map(item => item.replace('.', '').toUpperCase())
    return [...new Set(acceptList)].join('、')
  })

  // ==================== 文件类型判断 ====================

  /**
   * 获取预览类型
   * @param name 文件名
   */
  function getPreviewType(name: string): 'image' | 'pdf' | 'unsupported' {
    if (!name) return 'unsupported'
    const ext = name.split('.').pop()?.toLowerCase() || ''
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    if (imageExts.includes(ext)) return 'image'
    if (ext === 'pdf') return 'pdf'
    return 'unsupported'
  }

  /**
   * 判断文件是否可预览
   */
  function canPreview(file: ProUploadFileListItem): boolean {
    const name = file.response?.name || file.name
    return getPreviewType(name) === 'image' || getPreviewType(name) === 'pdf'
  }

  // ==================== JSON 序列化/反序列化 ====================

  /**
   * 解析 JSON 字符串为文件列表
   */
  function parseJsonValue(jsonValue: string | undefined): ProUploadDefaultFileItem[] {
    if (!jsonValue || jsonValue === '[]') return []
    try {
      const parsed = JSON.parse(jsonValue)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }

  /**
   * 序列化文件列表为 JSON 字符串
   */
  function serializeFileList(list: ProUploadDefaultFileItem[]): string {
    if (list.length === 0) return ''
    return JSON.stringify(list)
  }

  // ==================== 文件列表转换 ====================

  /**
   * 从 value/jsonValue 初始化文件列表
   */
  function initFileListFromValue(): void {
    const parsedList: any[] = []

    // 优先使用 jsonValue
    if (props.jsonValue !== undefined) {
      const fromJson = parseJsonValue(props.jsonValue)
      if (fromJson.length > 0) {
        parsedList.push(...fromJson)
      }
    }

    // 如果 jsonValue 为空但有 value，使用 value
    if (parsedList.length === 0 && props.value && props.value.length > 0) {
      const rawValue: any = props.value
      // 检测是否为 JSON 字符串，如果是则解析
      if (typeof rawValue === 'string' && rawValue.trim().startsWith('[')) {
        try {
          const parsed = JSON.parse(rawValue)
          if (Array.isArray(parsed)) {
            parsedList.push(...parsed)
          } else {
            parsedList.push(rawValue)
          }
        } catch {
          // 解析失败，使用原始值
          parsedList.push(rawValue)
        }
      } else if (Array.isArray(rawValue)) {
        parsedList.push(...rawValue)
      } else {
        parsedList.push(rawValue)
      }
    }

    // 转换为内部格式
    fileList.value = parsedList.map((item, index) => ({
      uid: `init_${index}_${Date.now()}_${Math.random().toString(36).slice(2)}`,
      name: item.name || (item as any).fileName,
      status: 'done' as const,
      response: item,
    }))
  }

  /**
   * 从文件列表提取已完成文件
   */
  function extractDoneFiles(): ProUploadDefaultFileItem[] {
    return fileList.value
      .filter(item => item.status === 'done' && item.response)
      .map(item => item.response!)
  }

  // ==================== 响应格式化 ====================

  /**
   * 格式化默认响应数据
   */
  function formatDefaultResponse(response: any): ProUploadDefaultFileItem | null {
    if (response?.error === 0 && response.url) {
      return {
        id: response.id,
        name: response.fileName || '未知文件名',
        fileName: response.fileName,
        size: 0,
        url: response.url,
      }
    }
    if (response.code === 0 && response.data && response.data.length > 0) {
      const fileData = response.data[0]
      return {
        name: fileData.attViewName || fileData.attFileName || '未知文件名',
        size: fileData.attFileSize || 0,
        url: fileData.attUrl || fileData.attPath || '',
      }
    }
    return null
  }

  /**
   * 统一处理上传结果
   */
  function handleUploadResult(response: any, originFile: File): ProUploadDefaultFileItem | null {
    // 如果有自定义格式化函数
    if (props.customConfig?.responseFormatter) {
      return props.customConfig.responseFormatter(response, originFile)
    }
    // 使用默认格式
    return formatDefaultResponse(response)
  }

  // ==================== 文件校验 ====================

  /**
   * 文件上传前校验
   */
  function beforeUpload(file: File): boolean | Promise<void> {
    // 检查是否达到上传上限
    if (isMaxCountReached.value) {
      message.warning(`最多只能上传 ${props.maxCount} 个文件`)
      return false
    }

    // 文件大小校验
    const fileSizeMB = file.size / 1024 / 1024
    if (fileSizeMB > (props.fileSize ?? 50)) {
      message.error(`文件大小不能超过 ${props.fileSize}MB`)
      return false
    }

    // 文件类型校验
    if (props.accept && props.accept !== '.doc,.docx,.pdf,.xls,.xlsx,.jpg,.jpeg,.png') {
      const acceptTypes = props.accept.split(',').map(t => t.replace('.', '').toLowerCase())
      const fileExt = file.name.split('.').pop()?.toLowerCase() || ''
      if (!acceptTypes.includes(fileExt)) {
        message.error(`文件格式不支持，请上传 ${acceptText.value} 格式的文件`)
        return false
      }
    }

    return true
  }

  // ==================== 上传 Change 处理 ====================

  /**
   * 处理上传结果变化
   */
  function handleChange(info: UploadChangeParam): void {
    const { file } = info

    if (file.status === 'uploading') {
      isUploading.value = true
      return
    }

    if (file.status === 'done') {
      isUploading.value = false
      // 上传成功
      const response = file.response as any
      const uploadItem = handleUploadResult(response, file.originFileObj as File)

      if (uploadItem) {
        // 替换正在上传的文件为已完成
        const previousDone = fileList.value
          .filter(item => item.status === 'done' && item.uid !== file.uid)
          .map(item => item.response)
          .filter(Boolean) as ProUploadDefaultFileItem[]

        const mergedItems = [...previousDone, uploadItem].slice(0, props.maxCount ?? 1)

        fileList.value = mergedItems.map((item, index) => ({
          uid: `done_${index}_${item.url || item.name || ''}_${Date.now()}`,
          name: item.name,
          status: 'done' as const,
          response: item,
        }))

        // 触发 emit
        const jsonStr = serializeFileList(mergedItems)
        emit('update:jsonValue', jsonStr)
        emit('update:value', mergedItems)
        emit('change', mergedItems)
        emit('success', uploadItem)
      } else {
        // 上传失败
        message.error(response.msg || response.message || '上传失败')
        fileList.value = fileList.value.filter(item => item.uid !== file.uid)
        emit('error', new Error(response.msg || response.message || '上传失败'))
      }
    } else if (file.status === 'error') {
      isUploading.value = false
      message.error('上传失败')
      emit('error', new Error('上传失败'))
    }
  }

  // ==================== 文件操作 ====================

  /**
   * 移除文件
   */
  function handleRemove(file: ProUploadFileListItem): void {
    fileList.value = fileList.value.filter(item => item.uid !== file.uid)
    const mergedItems = extractDoneFiles()
    const jsonStr = serializeFileList(mergedItems)
    emit('update:jsonValue', jsonStr)
    emit('update:value', mergedItems)
    emit('change', mergedItems)
    emit('remove', file)
  }

  /**
   * 预览文件
   */
  function handlePreview(file: ProUploadFileListItem): ProUploadPreviewState | null {
    if (!file.response?.url) return null
    const type = getPreviewType(file.response.name || file.name)
    return {
      visible: true,
      url: file.response.url,
      type,
      title: file.response?.name || file.name || '文件预览',
    }
  }

  // ==================== 监听初始化 ====================

  // 监听 jsonValue 变化，初始化文件列表
  watch(
    () => props.jsonValue,
    () => {
      initFileListFromValue()
    },
    { immediate: true }
  )

  // 监听 value 变化，初始化文件列表（兼容旧方式）
  watch(
    () => props.value,
    () => {
      // 如果没有使用 jsonValue，则使用 value 初始化
      if (props.jsonValue === undefined) {
        initFileListFromValue()
      }
    },
    { immediate: true }
  )

  // ==================== 返回 ====================

  return {
    // 状态
    fileList,
    isUploading,
    isMaxCountReached,
    doneFileCount,
    // 配置
    uploadUrl,
    uploadHeaders,
    uploadDataComputed,
    acceptText,
    // 文件类型
    getPreviewType,
    canPreview,
    // JSON 序列化
    parseJsonValue,
    serializeFileList,
    // 文件列表
    initFileListFromValue,
    extractDoneFiles,
    // 响应格式化
    formatDefaultResponse,
    // 文件操作
    beforeUpload,
    handleChange,
    handleRemove,
    handlePreview,
  }
}
