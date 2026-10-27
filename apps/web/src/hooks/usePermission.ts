/**
 * 权限校验 Hook
 *
 * 参考老系统实现，支持两种校验方式：
 * 1. 函数式：hasPermission('sys_user_add')
 * 2. hooks式：const { hasPermission } = usePermission()
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * 权限校验 Hook
 * @returns 权限校验函数集合
 */
export function usePermission() {
  const authStore = useAuthStore()

  /**
   * 检查是否拥有指定权限
   * @param permission 权限标识（如 'sys_user_add'）
   * @returns 是否拥有该权限
   *
   * @example
   * // 函数式使用
   * hasPermission('sys_user_add')
   *
   * // hooks式使用
   * const { hasPermission } = usePermission()
   * hasPermission('sys_user_add')
   */
  const hasPermission = (permission: string): boolean => {
    if (!permission) {
      return false
    }

    // permissions 是对象形式 { 'sys_user_add': true, 'sys_user_edit': true }
    return authStore.permissions[permission] === true
  }

  /**
   * 检查是否拥有任意一个权限（OR 逻辑）
   * @param permissionList 权限标识列表
   * @returns 是否拥有任意一个权限
   *
   * @example
   * hasAnyPermission(['sys_user_add', 'sys_user_edit'])
   */
  const hasAnyPermission = (permissionList: string[]): boolean => {
    if (!Array.isArray(permissionList) || permissionList.length === 0) {
      return false
    }

    return permissionList.some(permission => authStore.permissions[permission] === true)
  }

  /**
   * 检查是否拥有所有权限（AND 逻辑）
   * @param permissionList 权限标识列表
   * @returns 是否拥有所有权限
   *
   * @example
   * hasAllPermissions(['sys_user_add', 'sys_user_edit'])
   */
  const hasAllPermissions = (permissionList: string[]): boolean => {
    if (!Array.isArray(permissionList) || permissionList.length === 0) {
      return false
    }

    return permissionList.every(permission => authStore.permissions[permission] === true)
  }

  /**
   * 获取所有权限列表
   * @returns 权限对象
   */
  const permissions = computed(() => authStore.permissions)

  /**
   * 获取权限字符串数组（用于调试或显示）
   * @returns 权限字符串数组
   */
  const permissionList = computed(() => {
    return Object.keys(authStore.permissions).filter(key => authStore.permissions[key])
  })

  return {
    // 函数
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    // 计算属性
    permissions,
    permissionList,
  }
}

/**
 * 便捷函数：检查是否拥有指定权限
 * 无需调用 usePermission()，直接导入使用
 *
 * @example
 * import { hasPermission } from '@/hooks/usePermission'
 *
 * // 在 setup 中使用
 * const canEdit = hasPermission('sys_user_edit')
 *
 * // 在模板中使用
 * <a-button v-if="hasPermission('sys_user_add')">新增</a-button>
 */
export function hasPermission(permission: string): boolean {
  const authStore = useAuthStore()
  return authStore.permissions[permission] === true
}

/**
 * 便捷函数：检查是否拥有任意一个权限
 *
 * @example
 * import { hasAnyPermission } from '@/hooks/usePermission'
 *
 * const canOperate = hasAnyPermission(['sys_user_add', 'sys_user_edit', 'sys_user_del'])
 */
export function hasAnyPermission(permissionList: string[]): boolean {
  const authStore = useAuthStore()

  if (!Array.isArray(permissionList) || permissionList.length === 0) {
    return false
  }

  return permissionList.some(permission => authStore.permissions[permission] === true)
}

/**
 * 便捷函数：检查是否拥有所有权限
 *
 * @example
 * import { hasAllPermissions } from '@/hooks/usePermission'
 *
 * const canManage = hasAllPermissions(['sys_user_add', 'sys_user_edit', 'sys_user_del'])
 */
export function hasAllPermissions(permissionList: string[]): boolean {
  const authStore = useAuthStore()

  if (!Array.isArray(permissionList) || permissionList.length === 0) {
    return false
  }

  return permissionList.every(permission => authStore.permissions[permission] === true)
}
