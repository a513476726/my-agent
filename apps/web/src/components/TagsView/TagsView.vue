<template>
  <div class="tags-container">
    <div class="tag-left" v-if="isShow">
      <a-button title="前一个" size="small" @click="moveForward">
        <template #icon>
          <LeftOutlined />
        </template>
      </a-button>
    </div>
    <div class="tag-center" :class="{ isWhole: !isShow }">
      <div
        class="tags-box"
        ref="tagBox"
        @mousewheel="handleMousewheel"
        @mouseup="handleMouseUp"
        @mousemove="handleMouse"
        @mousedown="handleMouseStart"
      >
        <div class="tags-list" ref="tagsList" :style="{ left: tagBodyLeft + 'px' }">
          <div
            ref="tagsPageOpened"
            class="tag-item"
            :class="{ 'is-active': nowTagValue === item.value, 'is-only': !item.close }"
            :name="item.value"
            v-for="(item, index) in tagsStore.tagList"
            :key="index"
            @contextmenu.prevent="openMenu(item, $event)"
            @click="openUrl(item)"
          >
            <span class="tag-text">{{ item.label || (item.meta && item.meta.title) }}</span>
            <CloseOutlined class="tag-close" @click.stop="closeTag(item)" v-if="item.close" />
            <CloseOutlined class="tag-hide" v-else />
          </div>
        </div>
        <ul v-show="visible" :style="{ left: left + 'px', top: top + 'px' }" class="contextmenu">
          <li @click="closeTag(selectedTag)">关闭</li>
          <li @click="closeOthersTags">关闭其他</li>
          <li @click="closeAllTags">关闭全部</li>
          <li @click="refreshTag" v-if="nowTagValue === selectedTag.value">刷新</li>
        </ul>
      </div>
    </div>
    <div class="tag-right" v-if="isShow">
      <a-button title="后一个" size="small" @click="backwardShift">
        <template #icon>
          <RightOutlined />
        </template>
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTagsStore } from '@/stores/tags'
import { resolveUrlPath, setUrlPath } from '@/utils/route'
import { CloseOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import type { TagItem } from '@/stores/tags'

const route = useRoute()
const router = useRouter()
const tagsStore = useTagsStore()

const instance = getCurrentInstance()
const reLoad = () => {
  instance?.appContext.config.globalProperties.$forceUpdate()
}

const visible = ref(false)
const tagBodyLeft = ref(0)
const lock = ref(false)
const startX = ref(0)
const startY = ref(0)
const endX = ref(0)
const endY = ref(0)
const top = ref(0)
const left = ref(0)
const selectedTag = ref<TagItem>({} as TagItem)
const isShow = ref(false)

const tagBox = ref<HTMLElement | null>(null)
const tagsList = ref<HTMLElement | null>(null)
const tagsPageOpened = ref<HTMLElement[]>([])

const nowTagValue = computed(() => {
  return setUrlPath(route)
})

const init = () => {
  setTimeout(() => {
    if (tagsPageOpened.value) {
      tagsPageOpened.value.forEach((item: HTMLElement, index: number) => {
        if (tagsStore.tag.value === item.attributes.getNamedItem('name')?.value) {
          const tagEl = tagsPageOpened.value[index]
          if (tagEl) {
            moveToView(tagEl)
          }
        }
      })
    }
  }, 1)
}

const handleMouseUp = () => {
  lock.value = false
}

const handleMouseStart = (e: MouseEvent | TouchEvent) => {
  lock.value = true
  if ('clientX' in e && e.clientX && e.clientY) {
    startX.value = e.clientX
    startY.value = e.clientY
  } else if ('touches' in e) {
    startX.value = e.touches[0].pageX
    startY.value = e.touches[0].pageY
  }
}

const handleMouse = (e: MouseEvent | TouchEvent) => {
  const boundarystart = 0
  const boundaryend =
    tagsList.value && tagBox.value ? tagsList.value.offsetWidth - tagBox.value.offsetWidth + 100 : 0

  if (!lock.value) {
    return
  }

  if ('clientX' in e && e.clientX && e.clientY) {
    endX.value = e.clientX
    endY.value = e.clientY
  } else if ('touches' in e) {
    endX.value = e.touches[0].pageX
    endY.value = e.touches[0].pageY
  }

  let distanceX = endX.value - startX.value
  distanceX = parseInt(String(distanceX * 0.8))

  if (distanceX > 0 && tagBodyLeft.value < boundarystart) {
    tagBodyLeft.value = tagBodyLeft.value + distanceX
  } else if (distanceX < 0 && tagBodyLeft.value >= -boundaryend) {
    tagBodyLeft.value = tagBodyLeft.value + distanceX
  }
}

const handleMousewheel = (e: WheelEvent) => {
  const step = 100
  const boundarystart = 0
  const boundaryend =
    tagsList.value && tagBox.value ? tagsList.value.offsetWidth - tagBox.value.offsetWidth : 0

  if (e.deltaY > 0 && tagBodyLeft.value > -boundaryend) {
    if (tagBodyLeft.value + boundaryend < 100) {
      tagBodyLeft.value = -boundaryend
    } else {
      tagBodyLeft.value = tagBodyLeft.value - step
    }
  } else if (e.deltaY < 0 && tagBodyLeft.value < boundarystart) {
    if (tagBodyLeft.value < 0 && tagBodyLeft.value + step > 0) {
      tagBodyLeft.value = 0
    } else {
      tagBodyLeft.value = tagBodyLeft.value + step
    }
  }
}

const openMenu = (tag: TagItem, e: MouseEvent) => {
  e.preventDefault()
  if (tagsStore.tagList.length === 1) {
    return
  }

  visible.value = true
  selectedTag.value = tag
  left.value = e.clientX
  top.value = e.clientY
}

const closeOthersTags = () => {
  openUrl(selectedTag.value)
  tagsStore.DEL_TAG_OTHER()
}

const closeMenu = () => {
  visible.value = false
}

const closeAllTags = () => {
  tagsStore.DEL_ALL_TAG()
  router.push({
    path: resolveUrlPath(tagsStore.tagWel.value),
    query: tagsStore.tagWel.query || {},
  })
}

const moveToView = (tag: HTMLElement) => {
  if (tagsList.value && tagBox.value) {
    isShow.value = tagsList.value.offsetWidth - tagBox.value.offsetWidth > 0
  }

  if (!tag || !tagsList.value || !tagBox.value) return

  if (tag.offsetLeft < -tagBodyLeft.value) {
    tagBodyLeft.value = -tag.offsetLeft
  } else if (
    tag.offsetLeft + 10 > -tagBodyLeft.value &&
    tag.offsetLeft + tag.offsetWidth < -tagBodyLeft.value + tagBox.value.offsetWidth
  ) {
    // 标签在可视区域内，不做处理
  } else {
    tagBodyLeft.value = -(tag.offsetLeft - (tagBox.value.offsetWidth - 0 - tag.offsetWidth))
  }
}

const openUrl = (item: TagItem) => {
  router.push({
    path: resolveUrlPath(item.value),
    query: item.query || {},
  })
}

const eachTag = (tag: TagItem) => {
  for (const key in tagsStore.tagList) {
    if (tagsStore.tagList[Number(key)].value === tag.value) {
      return Number(key)
    }
  }
  return -1
}

const closeTag = (item: TagItem) => {
  const key = eachTag(item)
  let tag: TagItem | undefined
  tagsStore.DEL_TAG(item)
  if (item.value === tagsStore.tag.value) {
    tag = tagsStore.tagList[key === 0 ? key : key - 1]
    if (tag) {
      openUrl(tag)
    }
  }

  if (tagBodyLeft.value < -100) {
    tagBodyLeft.value = tagBodyLeft.value + 100
  } else {
    tagBodyLeft.value = 0
  }

  if (tagsList.value && tagBox.value) {
    isShow.value = tagsList.value.offsetWidth - tagBox.value.offsetWidth > 0
  }
}

const refreshTag = () => {
  tagsStore.REFRESH_VIEW()
  closeMenu()
}

const moveForward = () => {
  const boundarystart = 0
  if (tagBodyLeft.value < boundarystart) {
    if (tagBodyLeft.value < 0 && tagBodyLeft.value + 100 > 0) {
      tagBodyLeft.value = 0
    } else {
      tagBodyLeft.value = tagBodyLeft.value + 100
    }
  }
}

const backwardShift = () => {
  if (!tagsList.value || !tagBox.value) return
  const boundaryend = tagsList.value.offsetWidth - tagBox.value.offsetWidth
  if (tagBodyLeft.value > -boundaryend) {
    if (tagBodyLeft.value + boundaryend < 100) {
      tagBodyLeft.value = -boundaryend
    } else {
      tagBodyLeft.value = tagBodyLeft.value - 100
    }
  }
}

const updateTagsList = () => {
  const refs = instance?.refs.tagsPageOpened
  if (refs) {
    if (Array.isArray(refs)) {
      tagsPageOpened.value = refs as HTMLElement[]
    } else {
      tagsPageOpened.value = [refs as HTMLElement]
    }
  }
}

onMounted(() => {
  updateTagsList()
  init()

  tagsStore.$subscribe(() => {
    updateTagsList()
  })
})

const handleBodyClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (!target.closest('.contextmenu')) {
    closeMenu()
  }
}

onMounted(() => {
  document.body.addEventListener('click', handleBodyClick)
})

onUnmounted(() => {
  document.body.removeEventListener('click', handleBodyClick)
})

defineExpose({
  reLoad,
})
</script>

<style scoped>
.contextmenu {
  margin: 0;
  background: #fff;
  z-index: 999999;
  position: fixed;
  list-style-type: none;
  padding: 5px 0;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 400;
  color: #333;
  box-shadow: 2px 2px 3px 0 rgba(0, 0, 0, 0.3);
}

.contextmenu li {
  margin: 0 16px;
  padding: 0;
  height: 25px;
  line-height: 25px;
  cursor: pointer;
}

.contextmenu li:hover {
  background: #eee;
  color: #1d45dd;
}

.contextmenu li:not(:last-child) {
  border-bottom: 1px solid #ebebed;
}

.tags-container {
  height: 34px;
  display: flex;
  justify-content: space-between;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.tag-left {
  width: 28px;
  height: 100%;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tag-center {
  height: 100%;
  flex: 1;
  z-index: 999;
  overflow: hidden;
}

.tag-right {
  width: 28px;
  height: 100%;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.isWhole {
  width: 100%;
}

.tags-box {
  height: 100%;
  overflow: hidden;
  position: relative;
}

.tags-list {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  align-items: center;
  height: 100%;
  transition: left 0.2s;
  white-space: nowrap;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  height: 26px;
  line-height: 26px;
  padding: 0 10px;
  margin-left: 4px;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
  border: 1px solid #e4e7ed;
}

.tag-item:hover {
  background: #ecf5ff;
}

.tag-item.is-active {
  /* background: #1d45dd; */
  color: #1d45dd;
  border-color: #1d45dd;
}

.tag-item.is-active .tag-close {
  color: #1d45dd;
}

.tag-item.is-active .tag-close:hover {
  color: #f56c6c;
}

.tag-item.is-active .tag-hide {
  display: none;
}

.tag-item.is-only {
  padding-right: 10px;
}

.tag-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-close {
  margin-left: 6px;
  font-size: 10px;
  color: #999;
  cursor: pointer;
}

.tag-close:hover {
  color: #f56c6c;
}

.tag-hide {
  display: none;
}
</style>
