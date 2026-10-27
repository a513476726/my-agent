/**
 * JWT Token 工具函数
 */

export interface JwtPayload {
  sub?: string // subject (user ID)
  username?: string
  email?: string
  exp?: number // expiration time
  iat?: number // issued at
  [key: string]: any
}

/**
 * 解析 JWT Token
 * @param token JWT Token 字符串
 * @returns 解析后的 payload，如果解析失败返回 null
 */
export function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) {
      return null
    }

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
        })
        .join('')
    )

    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Failed to parse JWT:', error)
    return null
  }
}

/**
 * 检查 Token 是否过期
 * @param token JWT Token 字符串
 * @returns 是否过期
 */
export function isTokenExpired(token: string): boolean {
  const payload = parseJwt(token)
  if (!payload || !payload.exp) {
    return true
  }

  // exp 是秒级时间戳，需要转换为毫秒
  const expirationTime = payload.exp * 1000
  return Date.now() >= expirationTime
}

/**
 * 获取 Token 过期时间
 * @param token JWT Token 字符串
 * @returns 过期时间（毫秒时间戳），如果无法获取返回 null
 */
export function getTokenExpiration(token: string): number | null {
  const payload = parseJwt(token)
  if (!payload || !payload.exp) {
    return null
  }

  return payload.exp * 1000
}

/**
 * 从 Token 中提取用户信息
 * @param token JWT Token 字符串
 * @returns 用户信息，如果无法提取返回 null
 */
export function extractUserFromToken(token: string): {
  id?: string
  username?: string
  email?: string
} | null {
  const payload = parseJwt(token)
  if (!payload) {
    return null
  }

  return {
    id: payload.sub || payload.id,
    username: payload.username,
    email: payload.email,
  }
}
