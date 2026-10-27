/**
 * 节流指令
 * 使用: v-throttle:scroll="handleScroll" 或 v-throttle:scroll.300="handleScroll"
 */
import type { Directive, DirectiveBinding } from 'vue'

interface ThrottleElement extends HTMLElement {
  _throttleHandler?: {
    [key: string]: {
      handler: (...args: any[]) => void
      lastTime: number
    }
  }
}

export const vThrottle: Directive = {
  mounted(el: ThrottleElement, binding: DirectiveBinding) {
    const { arg = 'scroll', modifiers } = binding
    const delay = modifiers[300] ? 300 : modifiers[500] ? 500 : modifiers[1000] ? 1000 : 300

    if (!el._throttleHandler) {
      el._throttleHandler = {}
    }

    let lastTime = 0

    const handler = (...args: any[]) => {
      const now = Date.now()
      if (now - lastTime >= delay) {
        lastTime = now
        binding.value(...args)
      }
    }

    if (!el._throttleHandler[arg]) {
      el._throttleHandler[arg] = {
        handler,
        lastTime: 0,
      }
    }

    el.addEventListener(arg, handler)
  },
  unmounted(el: ThrottleElement, binding: DirectiveBinding) {
    const { arg = 'scroll' } = binding
    if (el._throttleHandler?.[arg]) {
      delete el._throttleHandler[arg]
    }
  },
}
