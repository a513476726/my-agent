import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface TagItem {
  label: string
  value: string
  query?: Record<string, any>
  meta?: Record<string, any>
  close?: boolean
  num?: string
  /** 路由 name（用于 KeepAlive 缓存清理） */
  name?: string
}

const tagObj: TagItem = {
  label: '',
  value: '',
  query: {},
  num: '',
  close: true,
}

function setFirstTag(list: TagItem[]): TagItem[] {
  if (list.length === 1) {
    list[0].close = false
  } else {
    list.forEach(a => {
      a.close = true
    })
  }
  return list
}

function getStorageItem<T>(key: string, defaultValue: T): T {
  try {
    const item = sessionStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch {
    return defaultValue
  }
}

function setStorageItem(key: string, value: any): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    console.error('Failed to save to sessionStorage:', e)
  }
}

function removeStorageItem(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch (e) {
    console.error('Failed to remove from sessionStorage:', e)
  }
}

export const useTagsStore = defineStore('tags', () => {
  const tagList = ref<TagItem[]>(getStorageItem('tagList', []))
  const tag = ref<TagItem>(getStorageItem('tag', { ...tagObj }))
  const tagWel = ref<TagItem>({
    label: '首页',
    value: '/',
  })

  const isCollapse = ref(false)

  /** 用于强制刷新当前路由视图（RouterView key） */
  const routerViewKey = ref(0)
  const REFRESH_VIEW = () => {
    routerViewKey.value += 1
  }

  /**
   * KeepAlive include 列表：派生自 tagList
   * 只缓存当前在标签栏中（未关闭）的 keepAlive 页面
   * - 关闭标签 → tagList 移除 → cachedViews 自动同步
   * - F5 刷新 → tagList 从 sessionStorage 恢复 → cachedViews 自动派生
   * - 不会出现在 tagList 中已不存在的"幽灵缓存"
   */
  const cachedViews = computed<string[]>(() => {
    return tagList.value.filter(t => t.meta?.keepAlive && t.name).map(t => t.name as string)
  })

  /**
   * @deprecated 保留兼容，新逻辑通过 tagList 自动派生。请勿直接调用。
   * 不会产生任何效果（cachedViews 是只读 computed）
   */
  const ADD_CACHED_VIEW = (_name: string): void => {
    /* no-op: cachedViews 由 tagList 自动派生 */
  }

  /**
   * @deprecated 保留兼容，新逻辑通过 tagList 自动派生。请勿直接调用。
   */
  const DEL_CACHED_VIEW = (_name: string): void => {
    /* no-op: cachedViews 由 tagList 自动派生 */
  }

  /**
   * @deprecated 保留兼容。退出登录时只需清空 tagList，cachedViews 会自动同步。
   */
  const CLEAR_CACHED_VIEWS = (): void => {
    /* no-op: cachedViews 由 tagList 自动派生 */
  }

  const ADD_TAG = (tagItem: TagItem) => {
    tag.value = tagItem
    setStorageItem('tag', tag.value)

    const existingIndex = tagList.value.findIndex(a => a.value === tagItem.value)
    if (existingIndex !== -1) {
      tagList.value[existingIndex] = {
        ...tagList.value[existingIndex],
        label: tagItem.label ?? tagList.value[existingIndex].label,
        query: tagItem.query ?? tagList.value[existingIndex].query,
        meta: tagItem.meta ?? tagList.value[existingIndex].meta,
        name: tagItem.name ?? tagList.value[existingIndex].name,
      }
      setStorageItem('tagList', tagList.value)
      return
    }

    tagList.value.push({
      label: tagItem.label,
      value: tagItem.value,
      query: tagItem.query,
      meta: tagItem.meta,
      name: tagItem.name,
    })

    tagList.value = setFirstTag(tagList.value)
    setStorageItem('tagList', tagList.value)
  }

  const SET_TAG = (value: string) => {
    tagList.value.forEach((ele, num) => {
      if (ele.value === value) {
        tag.value = tagList.value[num]
        setStorageItem('tag', tag.value)
      }
    })
  }

  const DEL_TAG = (tagItem: TagItem) => {
    const index = tagList.value.findIndex(ele => ele.value === tagItem.value)
    if (index !== -1) {
      tagList.value.splice(index, 1)
      tagList.value = setFirstTag(tagList.value)
      setStorageItem('tag', tag.value)
      setStorageItem('tagList', tagList.value)
      // cachedViews 是 computed，自动从 tagList 派生，无需手动清理
    }
  }

  const DEL_TAG_OTHER = () => {
    const currentValue = tag.value.value
    const index = tagList.value.findIndex(ele => ele.value === currentValue)
    if (index !== -1) {
      tagList.value = [tagList.value[index]]
      tag.value = tagList.value[0]
      tagList.value[0].close = false
      setStorageItem('tag', tag.value)
      setStorageItem('tagList', tagList.value)
    }
  }

  const DEL_ALL_TAG = () => {
    tag.value = { ...tagObj }
    tagList.value = []
    tagList.value.push({ ...tagWel.value, close: false })
    removeStorageItem('tag')
    removeStorageItem('tagList')
  }

  return {
    tagList,
    tag,
    tagWel,
    isCollapse,
    routerViewKey,
    REFRESH_VIEW,
    ADD_TAG,
    SET_TAG,
    DEL_TAG,
    DEL_TAG_OTHER,
    DEL_ALL_TAG,
    cachedViews,
    ADD_CACHED_VIEW,
    DEL_CACHED_VIEW,
    CLEAR_CACHED_VIEWS,
  }
})
