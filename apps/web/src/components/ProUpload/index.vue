<template>
  <div class="pro-upload" :class="{ 'pro-upload--compact': displayMode === 'compact' }">
    <!-- ========== Default 模式 ========== -->
    <template v-if="displayMode === 'default'">
      <!-- 上传按钮 -->
      <a-upload
        v-if="!(disabled || hideButton)"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :data="uploadDataComputed"
        :max-count="maxCount"
        :accept="accept"
        :disabled="disabled || isMaxCountReached || isUploading"
        :before-upload="beforeUpload"
        :show-upload-list="false"
        @change="handleChange"
      >
        <a-button
          type="primary"
          ghost
          :size="buttonSize"
          :disabled="disabled || isMaxCountReached || isUploading"
          :loading="isUploading"
        >
          <UploadOutlined />
          {{ uploadButtonLabel }}
        </a-button>
      </a-upload>

      <!-- 文件列表 -->
      <div v-if="fileList.length > 0" class="file-list">
        <div
          v-for="file in fileList"
          :key="file.uid"
          class="file-item"
          :class="{ 'file-item-disabled': disabled }"
        >
          <div class="file-info">
            <component :is="getFileIcon(file.name)" :size="14" class="file-icon" />
            <span class="file-name" :title="file.name">{{ file.name }}</span>
          </div>
          <div class="file-actions">
            <template v-if="canPreview(file)">
              <Eye :size="14" class="action-icon" @click="openPreview(file)" />
            </template>
            <a v-if="file.response?.url" :href="file.response.url" target="_blank" download>
              <Download :size="14" class="action-icon" />
            </a>
            <Popconfirm
              v-if="!disabled"
              title="确定删除该附件吗？"
              ok-text="确定"
              cancel-text="取消"
              @confirm="handleRemove(file)"
            >
              <Trash2 :size="14" class="action-icon delete-icon" />
            </Popconfirm>
          </div>
        </div>
      </div>

      <!-- 提示文字 -->
      <div v-if="!(disabled || hideButton) && !hideTip" class="pro-upload-tip">
        {{
          tipText ||
          `请上传相关证明材料，支持 ${acceptText} 格式，大小不超过 ${fileSize}MB，最多上传 ${maxCount} 个文件`
        }}
      </div>
    </template>

    <!-- ========== Compact 模式 ========== -->
    <template v-else-if="displayMode === 'compact'">
      <div class="compact-wrapper">
        <!-- 左侧：上传按钮 -->
        <a-upload
          v-if="!(disabled || hideButton)"
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadDataComputed"
          :max-count="maxCount"
          :accept="accept"
          :disabled="disabled || isMaxCountReached || isUploading"
          :before-upload="beforeUpload"
          :show-upload-list="false"
          @change="handleChange"
        >
          <a-button
            type="link"
            :disabled="disabled || isMaxCountReached || isUploading"
            :loading="isUploading"
            size="small"
          >
            <Upload :size="14" />
            {{ uploadButtonLabel }}
          </a-button>
        </a-upload>

        <!-- 右侧：附件列表（flex: 1 占满空间） -->
        <div v-if="fileList.length > 0" class="compact-files">
          <!-- 第1个附件（flex: 1 占满中间空间） -->
          <div v-if="fileList.length >= 1" class="compact-file-item">
            <component :is="getFileIcon(fileList[0].name)" :size="14" class="compact-icon" />
            <a-tooltip :title="fileList[0].name">
              <span class="compact-filename">{{ fileList[0].name }}</span>
            </a-tooltip>
            <span class="compact-actions">
              <template v-if="canPreview(fileList[0])">
                <Eye :size="14" class="compact-action" @click="openPreview(fileList[0])" />
              </template>
              <a
                v-if="fileList[0].response?.url"
                :href="fileList[0].response.url"
                target="_blank"
                download
              >
                <Download :size="14" class="compact-action" />
              </a>
              <Popconfirm
                v-if="!disabled"
                title="确定删除该附件吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleRemove(fileList[0])"
              >
                <Trash2 :size="14" class="compact-action delete-icon" />
              </Popconfirm>
            </span>
          </div>

          <!-- +N 按钮（hover 显示其余附件） -->
          <a-popover
            v-if="fileList.length > 1"
            v-model:open="popoverVisible"
            trigger="hover"
            placement="top"
          >
            <template #content>
              <div class="compact-popover-list popover-content">
                <div
                  v-for="file in fileList.slice(1)"
                  :key="file.uid"
                  class="compact-popover-item"
                  :title="file.name"
                >
                  <component :is="getFileIcon(file.name)" :size="14" class="compact-icon" />
                  <span class="compact-popover-filename">{{ file.name }}</span>
                  <span class="compact-popover-actions">
                    <template v-if="canPreview(file)">
                      <Eye :size="14" class="compact-action" @click="openPreview(file)" />
                    </template>
                    <a v-if="file.response?.url" :href="file.response.url" target="_blank" download>
                      <Download :size="14" class="compact-action" />
                    </a>
                    <Popconfirm
                      v-if="!disabled"
                      title="确定删除该附件吗？"
                      ok-text="确定"
                      cancel-text="取消"
                      @confirm="handleRemove(file)"
                    >
                      <Trash2 :size="14" class="compact-action delete-icon" />
                    </Popconfirm>
                  </span>
                </div>
              </div>
            </template>
            <span class="compact-more">+{{ fileList.length - 1 }}</span>
          </a-popover>
        </div>
      </div>
    </template>

    <!-- ========== 预览弹窗 ========== -->
    <a-modal
      v-model:open="previewState.visible"
      :title="previewState.title"
      width="95%"
      :footer="null"
      destroy-on-close
    >
      <div class="preview-content">
        <img
          v-if="previewState.type === 'image'"
          :src="previewState.url"
          class="preview-image"
          alt=""
        />
        <iframe
          v-else-if="previewState.type === 'pdf'"
          :src="previewState.url"
          class="preview-pdf"
          type="application/pdf"
        />
        <div v-else class="preview-unsupported">
          <p>该文件类型不支持预览，请下载后查看</p>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Popconfirm } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import {
  Upload,
  File,
  FileText,
  FileImage,
  FileSpreadsheet,
  Eye,
  Download,
  Trash2,
} from 'lucide-vue-next'
import { useProUpload } from './hooks/useProUpload'
import type { ProUploadProps, ProUploadEmits, ProUploadPreviewState } from './types'

const props = withDefaults(defineProps<ProUploadProps>(), {
  maxCount: 1,
  accept: '.doc,.docx,.pdf,.xls,.xlsx,.jpg,.jpeg,.png',
  fileSize: 50,
  disabled: false,
  buttonSize: 'middle',
  hideTip: false,
  hideButton: false,
  useDefaultFormat: true,
  uploadButtonLabel: '上传附件',
  displayMode: 'default',
})

const emit = defineEmits<ProUploadEmits>()

// 使用 hook
const {
  fileList,
  isUploading,
  isMaxCountReached,
  uploadUrl,
  uploadHeaders,
  uploadDataComputed,
  acceptText,
  canPreview,
  beforeUpload,
  handleChange,
  handleRemove,
  handlePreview,
} = useProUpload(props, emit)

// 根据文件后缀获取图标组件
function getFileIcon(name: string) {
  if (!name) return File
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const iconMap: Record<string, typeof File> = {
    doc: FileText,
    docx: FileText,
    pdf: FileText,
    xls: FileSpreadsheet,
    xlsx: FileSpreadsheet,
    csv: FileSpreadsheet,
    jpg: FileImage,
    jpeg: FileImage,
    png: FileImage,
    gif: FileImage,
    bmp: FileImage,
    webp: FileImage,
  }
  return iconMap[ext] || File
}

// displayMode
const displayMode = computed(() => props.displayMode || 'default')

// 预览状态
const previewState = ref<ProUploadPreviewState>({
  visible: false,
  url: '',
  type: 'unsupported',
  title: '',
})

// Compact 模式 Popover 显隐
const popoverVisible = ref(false)

// 打开预览
function openPreview(file: any) {
  const result = handlePreview(file)
  if (result) {
    previewState.value = result
  }
}
</script>

<style scoped lang="less">
.pro-upload {
  width: 100%;
}

// ========== Default 模式样式 ==========

.pro-upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.file-list {
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;

  & + .file-item {
    margin-top: 4px;
  }

  &-disabled {
    background-color: #fafafa;
  }
}

.file-info {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.file-icon {
  font-size: 16px;
  color: #999;
  margin-right: 8px;
  flex-shrink: 0;
}

.file-name {
  font-size: 14px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  margin-left: 12px;
}

.action-icon {
  font-size: 16px;
  color: #333;
  cursor: pointer;

  &:hover {
    color: #1890ff;
  }
}

.delete-icon {
  color: #333;

  &:hover {
    color: #ff4d4f;
  }
}

// ========== Compact 模式样式 ==========

.pro-upload--compact {
  .compact-wrapper {
    display: flex;
    align-items: center;
    width: 100%;
  }

  .compact-files {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
  }

  .compact-file-item {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    gap: 8px;
    padding: 2px 8px;
    background: #f5f5f5;
    border-radius: 4px;
    max-width: 100%;
  }

  .compact-icon {
    font-size: 12px;
    color: #999;
    flex-shrink: 0;
  }

  .compact-filename {
    flex: 1;
    font-size: 13px;
    color: #333;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .compact-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .compact-action {
    font-size: 12px;
    color: #666;
    cursor: pointer;
    flex-shrink: 0;

    &:hover {
      color: var(--detail-primary-color);
    }

    &.delete-icon:hover {
      color: #ff4d4f;
    }
  }

  .compact-more {
    flex-shrink: 0;
    font-size: 13px;
    color: #1890ff;
    cursor: pointer;
    padding: 2px 8px;
    background: #d9edff;
    border-radius: 4px;
    margin-left: 8px;

    &:hover {
      background: #cfe8ff;
    }
  }

  .compact-popover-list {
    width: 280px;
  }

  :deep(.popover-content) {
    .compact-popover-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 2px 8px;
      background: #f5f5f5;
      border-radius: 4px;

      &:not(:last-child) {
        margin-bottom: 4px;
      }
    }

    .compact-popover-filename {
      flex: 1;
      font-size: 13px;
      color: #333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
    }

    .compact-popover-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    .compact-icon {
      font-size: 12px;
      color: #999;
      flex-shrink: 0;
    }

    .compact-action {
      font-size: 12px;
      color: #666;
      cursor: pointer;
      flex-shrink: 0;

      &:hover {
        color: var(--detail-primary-color);
      }

      &.delete-icon:hover {
        color: #ff4d4f;
      }
    }
  }
}

// ========== 预览弹窗样式 ==========

.preview-content {
  width: 100%;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  max-width: 100%;
  max-height: 85vh;
  object-fit: contain;
}

.preview-pdf {
  width: 100%;
  height: 85vh;
  border: none;
}

.preview-unsupported {
  text-align: center;
  color: #999;
  padding: 40px;
}
</style>

<style lang="less">
// Popover 内容在 body 下渲染，非 scoped 样式才能生效
.compact-popover-list {
  width: 400px;
}

.compact-popover-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 8px;
  background: #f5f5f5;
  border-radius: 4px;

  &:not(:last-child) {
    margin-bottom: 4px;
  }
}

.compact-popover-filename {
  flex: 1;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.compact-popover-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.compact-popover-item .compact-icon,
.compact-popover-item .compact-action {
  font-size: 14px;
  color: #999;
  flex-shrink: 0;
}

.compact-popover-item .compact-action:hover {
  color: var(--detail-primary-color, #1890ff);
}

.compact-popover-item .compact-action.delete-icon:hover {
  color: #ff4d4f;
}
</style>
