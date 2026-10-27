/**
 * 自定义指令统一导出
 */
import type { App } from 'vue'
import { vLoading } from './loading'
import { vPermission } from './permission'
import { vClickOutside } from './clickOutside'
import { vDebounce } from './debounce'
import { vThrottle } from './throttle'

/**
 * 注册所有自定义指令
 */
export function setupDirectives(app: App) {
  app.directive('loading', vLoading)
  app.directive('permission', vPermission)
  app.directive('click-outside', vClickOutside)
  app.directive('debounce', vDebounce)
  app.directive('throttle', vThrottle)
}

export * from './loading'
export * from './permission'
export * from './clickOutside'
export * from './debounce'
export * from './throttle'
