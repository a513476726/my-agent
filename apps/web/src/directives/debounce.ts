/**
 * 防抖指令
 * 使用: v-debounce:click="handleClick" 或 v-debounce:click.300="handleClick"
 */
import type { Directive, DirectiveBinding } from 'vue'

interface DebounceElement extends HTMLElement {
  _debounceHandler?: {
    [key: string]: {
      handler: (...args: any[]) => void
      timer: ReturnType<typeof setTimeout>
    }
  }
}

export const vDebounce: Directive = {
  mounted(el: DebounceElement, binding: DirectiveBinding) {
    const { arg = 'click', modifiers } = binding
    const delay = modifiers[300] ? 300 : modifiers[500] ? 500 : modifiers[1000] ? 1000 : 300

    if (!el._debounceHandler) {
      el._debounceHandler = {}
    }

    const handler = (...args: any[]) => {
      if (el._debounceHandler?.[arg]) {
        clearTimeout(el._debounceHandler[arg].timer)
      }

      if (!el._debounceHandler) {
        el._debounceHandler = {}
      }

      el._debounceHandler[arg] = {
        handler: binding.value,
        timer: setTimeout(() => {
          binding.value(...args)
        }, delay),
      }
    }

    el.addEventListener(arg, handler)
  },
  unmounted(el: DebounceElement, binding: DirectiveBinding) {
    const { arg = 'click' } = binding
    if (el._debounceHandler?.[arg]) {
      clearTimeout(el._debounceHandler[arg].timer)
      delete el._debounceHandler[arg]
    }
  },
}
