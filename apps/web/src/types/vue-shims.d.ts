declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}

declare module '@/components/ui/*' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<unknown, unknown, unknown>
  export default component
}
