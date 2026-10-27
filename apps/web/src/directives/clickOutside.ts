/**
 * 点击外部指令
 * 使用: v-click-outside="handleClickOutside"
 */
import type { Directive, DirectiveBinding } from 'vue'

interface ClickOutsideElement extends HTMLElement {
  _clickOutsideHandler?: (event: MouseEvent) => void
}

export const vClickOutside: Directive = {
  mounted(el: ClickOutsideElement, binding: DirectiveBinding) {
    const handler = (event: MouseEvent) => {
      if (!el.contains(event.target as Node)) {
        binding.value(event)
      }
    }

    el._clickOutsideHandler = handler
    document.addEventListener('click', handler)
  },
  unmounted(el: ClickOutsideElement) {
    if (el._clickOutsideHandler) {
      document.removeEventListener('click', el._clickOutsideHandler)
      delete el._clickOutsideHandler
    }
  },
}
