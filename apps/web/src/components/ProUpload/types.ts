// ==================== 类型定义 ====================

/**
 * 展示模式
 */
export type ProUploadDisplayMode = 'default' | 'compact'

/**
 * 统一文件列表项格式（内部使用）
 */
export interface ProUploadFileListItem {
  uid: string
  name: string
  status: 'done' | 'uploading' | 'error' | 'removed'
  response?: ProUploadDefaultFileItem | null
  percent?: number
}

/**
 * 预览状态
 */
export interface ProUploadPreviewState {
  visible: boolean
  url: string
  type: 'image' | 'pdf' | 'unsupported'
  title: string
}

/**
 * 上传文件项
 */
export interface ProUploadFileItem {
  /** 文件ID（服务器返回） */
  id: string
  /** 文件名 */
  fileName: string
  /** 文件URL（可选，用于显示） */
  url?: string
}

/**
 * 默认上传响应数据结构
 */
export interface ProUploadDefaultResponse {
  msg: string
  object: any
  code: number
  data: Array<{
    id: any
    attRelationId: string
    attFileName: string
    attFileSize: number
    attViewName: string
    attFileType: any
    attPath: string
    attUploadTime: string
    attUrl: string
    userId: string
    code: number
    msg: string
    invesProjectId: any
    createName: any
  }>
}

/**
 * 原有业务上传响应数据结构（兼容旧接口）
 */
export interface ProUploadResponse {
  fileName: string
  id: number
  error: number
  message: string
  url: string
}

/**
 * 默认上传存储格式（name/size/url）
 */
export interface ProUploadDefaultFileItem {
  /** 文件 ID（新平台 upload 接口返回） */
  id?: string | number
  /** 文件名 */
  name: string
  /** 文件名（与 name 同义，提交后端时使用） */
  fileName?: string
  /** 文件大小（字节） */
  size: number
  /** 文件URL */
  url: string
}

/**
 * 自定义上传配置
 */
export interface ProUploadCustomConfig {
  /** 自定义上传接口地址（默认：/api/files/upload） */
  uploadUrl?: string
  /** 自定义请求参数（函数形式，支持动态参数） */
  uploadData?: (file: File) => Record<string, any> | undefined
  /** 自定义响应格式化函数（将接口响应转换为存储格式） */
  responseFormatter?: (response: any, file: File) => any
}

/**
 * ProUpload 组件 Props
 */
export interface ProUploadProps {
  /** 业务ID（如客户登记ID） */
  businessId?: string
  /** 最大文件数量 */
  maxCount?: number
  /** 接受的文件类型 */
  accept?: string
  /** 文件大小限制(MB) */
  fileSize?: number
  /** 是否禁用 */
  disabled?: boolean
  /** 已上传的文件列表（用于回显，支持 v-model:value） */
  value?: any[]
  /** 附件 JSON 字符串（用于双向绑定，自动序列化和解析） */
  jsonValue?: string
  /** 按钮尺寸 */
  buttonSize?: 'small' | 'middle' | 'large'
  /** 上传按钮文案 */
  uploadButtonLabel?: string
  /** 是否隐藏上传提示文字 */
  hideTip?: boolean
  /** 是否隐藏上传按钮（预览模式使用） */
  hideButton?: boolean
  /** 自定义提示文字 */
  tipText?: string
  /** 自定义上传配置 */
  customConfig?: ProUploadCustomConfig
  /** 是否使用默认存储格式（name/size/url），否则使用 ProUploadFileItem */
  useDefaultFormat?: boolean
  /** 展示模式：default=完整列表，compact=紧凑一行 */
  displayMode?: ProUploadDisplayMode
}

/**
 * ProUpload 组件 Emits
 */
export interface ProUploadEmits {
  (e: 'update:value', value: any[]): void
  (e: 'update:jsonValue', value: string): void
  (e: 'change', value: any[]): void
  (e: 'success', file: any): void
  (e: 'remove', file?: any): void
  (e: 'error', error: Error): void
}
