/**
 * 加载指令
 * 使用: v-loading="isLoading"
 */
import type { Directive, DirectiveBinding } from 'vue'

interface LoadingElement extends HTMLElement {
  _loadingInstance?: {
    show: () => void
    hide: () => void
  }
}

const createLoadingElement = (): HTMLElement => {
  const loadingEl = document.createElement('div')
  loadingEl.className = 'v-loading-mask'
  loadingEl.innerHTML = `
    <div class="v-loading-spinner">
      <div class="v-loading-spinner-icon"></div>
      <div class="v-loading-text">加载中...</div>
    </div>
  `
  return loadingEl
}

export const vLoading: Directive = {
  mounted(el: LoadingElement, binding: DirectiveBinding) {
    const loadingEl = createLoadingElement()
    el.style.position = 'relative'
    el._loadingInstance = {
      show: () => {
        if (!el.contains(loadingEl)) {
          el.appendChild(loadingEl)
        }
      },
      hide: () => {
        if (el.contains(loadingEl)) {
          el.removeChild(loadingEl)
        }
      },
    }

    if (binding.value) {
      el._loadingInstance.show()
    }
  },
  updated(el: LoadingElement, binding: DirectiveBinding) {
    if (binding.value !== binding.oldValue) {
      if (binding.value) {
        el._loadingInstance?.show()
      } else {
        el._loadingInstance?.hide()
      }
    }
  },
  unmounted(el: LoadingElement) {
    el._loadingInstance?.hide()
    delete el._loadingInstance
  },
}
