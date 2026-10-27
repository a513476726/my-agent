/**
 * 数据脱敏工具函数
 */

/**
 * 手机号脱敏 - 保留前3位和后4位
 * @param phone 手机号
 * @returns 脱敏后的手机号
 */
export function encryptPhone(phone: string | number | null | undefined): string {
  if (!phone) return '--'
  const phoneStr = String(phone)
  return phoneStr.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

/**
 * 固定电话脱敏 - 忽略分隔符，保留前3位和后4位数字，中间打码
 * 兼容区号+横杠、12位等格式（encryptPhone 的 11 位正则匹配不到会漏脱敏）
 * @param phone 固定电话
 * @returns 脱敏后的固定电话
 */
export function encryptOfficePhone(phone: string | number | null | undefined): string {
  if (!phone) return '--'
  const value = String(phone)
  const digits = value.replace(/\D/g, '')
  if (digits.length < 7) return value
  return digits.slice(0, 3) + '****' + digits.slice(-4)
}

/**
 * 姓名脱敏 - 保留第一个字符
 * @param name 姓名
 * @returns 脱敏后的姓名
 */
export function encryptName(name: string | null | undefined): string {
  if (!name) return '--'
  return name[0] + '*'.repeat(name.length - 1)
}

/**
 * 地址脱敏 - 保留前4位
 * @param address 地址
 * @returns 脱敏后的地址
 */
export function encryptAddress(address: string | null | undefined): string {
  if (!address) return '--'
  return address.slice(0, 4) + '*'.repeat(Math.max(0, address.length - 4))
}

/**
 * 身份证脱敏 - 保留前6位和后4位
 * @param idCard 身份证号
 * @returns 脱敏后的身份证号
 */
export function encryptIdCard(idCard: string | number | null | undefined): string {
  if (!idCard) return '--'
  const idCardStr = String(idCard)
  return idCardStr.replace(/(\d{6})\d{8}(\d{4})/, '$1****$2')
}

/**
 * 微信/QQ 等账号脱敏 - 保留后4位
 * @param value 账号
 * @returns 脱敏后的账号
 */
export function encryptExt(value: string | null | undefined): string {
  if (!value) return '--'
  const v = String(value)
  if (v.length <= 4) return v
  return '****' + v.slice(-4)
}

/**
 * 邮箱脱敏 - 首字符 + ****@域名
 * @param email 邮箱
 * @returns 脱敏后的邮箱
 */
export function encryptEmail(email: string | null | undefined): string {
  if (!email) return '--'
  const at = String(email).indexOf('@')
  if (at <= 1) return String(email)
  return String(email).charAt(0) + '****' + String(email).slice(at)
}

/**
 * 处理手机号（用于列表展示）
 * @param phoneNumber 手机号
 * @returns 脱敏后的手机号
 */
export function processPhoneNumber(phoneNumber: string | number | null | undefined): string {
  if (!phoneNumber) return '--'
  const phoneStr = String(phoneNumber)
  return phoneStr.slice(0, 3) + '****' + phoneStr.slice(-4)
}

/**
 * 处理身份证号（用于列表展示）
 * @param idCard 身份证号
 * @returns 脱敏后的身份证号
 */
export function processIDCard(idCard: string | number | null | undefined): string {
  if (!idCard) return '--'
  const idCardStr = String(idCard)
  return idCardStr.slice(0, 6) + '****' + idCardStr.slice(-4)
}

/**
 * 处理地址（用于列表展示）
 * @param address 地址
 * @returns 脱敏后的地址
 */
export function processAddress(address: string | null | undefined): string {
  if (!address) return '--'
  return address.slice(0, 4) + '****'
}
