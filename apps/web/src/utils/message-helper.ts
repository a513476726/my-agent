/**
 * 错误消息辅助工具
 * 提供截断、统一显示等能力
 */
import { message } from 'ant-design-vue'

/** 错误消息最大字符数（统一规范） */
export const MAX_ERROR_MESSAGE_LENGTH = 80

/**
 * 截断过长的错误消息
 * - 合并连续空白
 * - 超出长度以省略号结尾
 *
 * @example
 * truncateMessage('操作失败：服务器返回了 ' + 'a'.repeat(200))
 * // => '操作失败：服务器返回了 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa…'
 */
export function truncateMessage(msg: unknown, maxLength = MAX_ERROR_MESSAGE_LENGTH): string {
  if (msg === null || msg === undefined) return '操作失败'
  const cleaned = String(msg).replace(/\s+/g, ' ').trim()
  if (!cleaned) return '操作失败'
  return cleaned.length <= maxLength ? cleaned : cleaned.slice(0, maxLength) + '…'
}

/**
 * 显示错误消息（自动截断）
 * 替代直接调用 message.error(rawMsg)，解决超长文本溢出问题
 *
 * 关于去重：401 路径走 notification 单次提示，
 * 其他错误不再做去重（避免掩盖实际问题）。
 */
export function showTruncatedError(msg: unknown): void {
  message.error(truncateMessage(msg), 3)
}
