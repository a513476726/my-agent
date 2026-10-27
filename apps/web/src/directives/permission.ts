/**
 * 权限指令
 * 使用: v-permission="'user:create'"
 * 或: v-permission="['user:create', 'user:edit']"
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

interface PermissionElement extends HTMLElement {
  _permissionOriginalDisplay?: string
}

// 权限检查函数
function checkPermission(permission: string | string[]): boolean {
  const authStore = useAuthStore()

  // 空权限视为无权限
  if (!permission) {
    return false
  }

  // 数组权限：拥有任意一个即可
  if (Array.isArray(permission)) {
    return permission.some(p => authStore.permissions[p] === true)
  }

  // 字符串权限：直接检查
  return authStore.permissions[permission] === true
}

export const vPermission: Directive = {
  mounted(el: PermissionElement, binding: DirectiveBinding) {
    const permission = binding.value
    if (!permission) {
      return
    }

    if (!checkPermission(permission)) {
      el._permissionOriginalDisplay = el.style.display
      el.style.display = 'none'
    }
  },
  updated(el: PermissionElement, binding: DirectiveBinding) {
    const permission = binding.value
    if (!permission) {
      return
    }

    if (checkPermission(permission)) {
      el.style.display = el._permissionOriginalDisplay || ''
    } else {
      el._permissionOriginalDisplay = el.style.display
      el.style.display = 'none'
    }
  },
  unmounted(el: PermissionElement) {
    if (el._permissionOriginalDisplay !== undefined) {
      el.style.display = el._permissionOriginalDisplay
    }
  },
}
