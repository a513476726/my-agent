/**
 * Ant Design Vue 主题配置
 * 支持动态主题切换和自定义主题变量
 */

export type ThemeMode = 'light' | 'dark'

export interface ThemeConfig {
  mode: ThemeMode
  primaryColor: string
  borderRadius: number
  // 可以扩展更多主题变量
  [key: string]: any
}

// 默认主题配置
export const defaultTheme: ThemeConfig = {
  mode: 'light',
  primaryColor: '#1d45dd',
  borderRadius: 6,
}

// 暗色主题配置
export const darkTheme: ThemeConfig = {
  mode: 'dark',
  primaryColor: '#1d45dd',
  borderRadius: 6,
}

// 主题变量映射到 ant-design-vue less 变量
export const themeVariableMap: Record<string, string> = {
  primaryColor: '@primary-color',
  borderRadius: '@border-radius-base',
  // 可以添加更多映射
}

/**
 * 将主题配置转换为 CSS 变量字符串
 */
export function generateThemeVariables(config: ThemeConfig): string {
  const variables: string[] = []

  // 基础变量
  if (config.primaryColor) {
    variables.push(`@primary-color: ${config.primaryColor};`)
  }

  if (config.borderRadius !== undefined) {
    variables.push(`@border-radius-base: ${config.borderRadius}px;`)
  }

  // 暗色主题特殊处理
  if (config.mode === 'dark') {
    variables.push(`@body-background: #141414;`)
    variables.push(`@component-background: #1f1f1f;`)
    variables.push(`@text-color: rgba(255, 255, 255, 0.85);`)
    variables.push(`@text-color-secondary: rgba(255, 255, 255, 0.65);`)
    variables.push(`@border-color-base: #434343;`)
    variables.push(`@heading-color: rgba(255, 255, 255, 0.85);`)
  }

  return variables.join('\n')
}

/**
 * 获取主题配置
 */
export function getThemeConfig(mode: ThemeMode): ThemeConfig {
  return mode === 'dark' ? darkTheme : defaultTheme
}
