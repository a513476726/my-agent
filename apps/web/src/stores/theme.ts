import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'
import type { ThemeMode, ThemeConfig } from '@/config/theme'
import { defaultTheme, darkTheme } from '@/config/theme'
import { theme } from 'ant-design-vue'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 读取保存的主题
  const savedTheme = localStorage.getItem('theme') as ThemeMode | null
  const mode = ref<ThemeMode>(savedTheme || 'light')

  // 当前主题配置
  const themeConfig = ref<ThemeConfig>(mode.value === 'dark' ? darkTheme : defaultTheme)

  /**
   * 获取 Ant Design Vue 的主题配置
   */
  const antdTheme = computed(() => {
    const baseToken = {
      colorPrimary: themeConfig.value.primaryColor,
      borderRadius: themeConfig.value.borderRadius,
    }

    // 暗色主题额外配置
    const darkToken =
      mode.value === 'dark'
        ? {
            colorBgBase: '#141414',
            colorBgContainer: '#1f1f1f',
            colorText: 'rgba(255, 255, 255, 0.85)',
            colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
            colorBorder: '#434343',
            colorBorderSecondary: '#303030',
          }
        : {}

    return {
      token: {
        ...baseToken,
        ...darkToken,
      },
      algorithm: mode.value === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
    }
  })

  /**
   * 应用主题样式到 DOM
   */
  const applyTheme = (config: ThemeConfig) => {
    // 更新 body 的 class 以支持暗色主题
    if (config.mode === 'dark') {
      document.documentElement.classList.add('dark')
      document.body.classList.add('dark-theme')
    } else {
      document.documentElement.classList.remove('dark')
      document.body.classList.remove('dark-theme')
    }
  }

  /**
   * 切换主题模式
   */
  const toggleTheme = () => {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
  }

  /**
   * 设置主题模式
   */
  const setTheme = (newMode: ThemeMode) => {
    mode.value = newMode
  }

  /**
   * 更新主题配置
   */
  const updateThemeConfig = (config: Partial<ThemeConfig>) => {
    themeConfig.value = { ...themeConfig.value, ...config }
  }

  // 监听主题变化，自动应用
  watch(
    mode,
    newMode => {
      themeConfig.value = newMode === 'dark' ? darkTheme : defaultTheme
      applyTheme(themeConfig.value)
      localStorage.setItem('theme', newMode)
    },
    { immediate: true }
  )

  // 初始化时应用主题
  if (typeof window !== 'undefined') {
    applyTheme(themeConfig.value)
  }

  return {
    mode,
    themeConfig,
    antdTheme,
    toggleTheme,
    setTheme,
    updateThemeConfig,
    applyTheme,
  }
})
