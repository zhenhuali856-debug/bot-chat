<script setup>
import { ref, computed, watch } from 'vue'
import {
  ElDialog,
  ElInput,
  ElButton,
  ElTag,
  ElMessage,
  ElMessageBox,
  Document,
  View,
  Edit,
  CopyDocument,
  Download,
  Delete
} from '../plugins/element'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  chapter: {
    type: Object,
    default: null
  },
  workTitle: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'save', 'delete'])

const viewMode = ref('preview') // 'preview' | 'edit'
const editTitle = ref('')
const editContent = ref('')
const isSaving = ref(false)

watch(
  () => [props.modelValue, props.chapter],
  ([visible, chap]) => {
    if (visible && chap) {
      editTitle.value = chap.title || ''
      editContent.value = chap.content || ''
      viewMode.value = 'preview'
    }
  },
  { immediate: true }
)

const renderedHtml = computed(() => renderMarkdown(editContent.value))

const wordCount = computed(() => (editContent.value || '').replace(/\s+/g, '').length)

const hasChanges = computed(() => {
  if (!props.chapter) return false
  return (
    editTitle.value.trim() !== (props.chapter.title || '') ||
    editContent.value !== (props.chapter.content || '')
  )
})

const handleCopy = async () => {
  if (!editContent.value) return
  try {
    await navigator.clipboard.writeText(editContent.value)
    ElMessage.success('已复制本章全文！')
  } catch {
    ElMessage.error('复制失败，请切换编辑模式手动复制')
  }
}

const handleExportMd = () => {
  if (!props.chapter) return
  const mdText = `# ${editTitle.value.trim() || props.chapter.title}\n\n${editContent.value}`
  const blob = new Blob([mdText], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${editTitle.value.trim() || 'chapter'}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('已导出本章为 Markdown 文件！')
}

const handleSave = async () => {
  const title = editTitle.value.trim()
  if (!title) {
    ElMessage.warning('章节名称不能为空')
    return
  }
  isSaving.value = true
  try {
    emit('save', props.chapter.id, {
      title,
      content: editContent.value
    })
    emit('update:modelValue', false)
  } finally {
    isSaving.value = false
  }
}

const handleDelete = async () => {
  if (!props.chapter) return
  try {
    await ElMessageBox.confirm(
      `确定要删除章节《${props.chapter.title}》吗？此操作不可恢复。`,
      '删除章节提示',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }
  emit('delete', props.chapter.id)
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="720px"
    class="chapter-editor-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="flex items-center gap-2">
        <el-icon class="text-blue-400"><Document /></el-icon>
        <span class="dialog-title-text">
          {{ workTitle ? `《${workTitle}》· ` : '' }}{{ editTitle || '章节正文' }}
        </span>
        <el-tag size="small" type="info" effect="plain">
          约 {{ wordCount.toLocaleString() }} 字
        </el-tag>
      </div>
    </template>

    <div v-if="chapter" class="chapter-editor-body">
      <div class="editor-toolbar">
        <div class="mode-tabs">
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: viewMode === 'preview' }"
            @click="viewMode = 'preview'"
          >
            <el-icon><View /></el-icon>
            <span>阅读排版</span>
          </button>
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: viewMode === 'edit' }"
            @click="viewMode = 'edit'"
          >
            <el-icon><Edit /></el-icon>
            <span>编辑正文</span>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <el-button size="small" plain :icon="CopyDocument" @click="handleCopy">
            复制全文
          </el-button>
          <el-button size="small" plain :icon="Download" @click="handleExportMd">
            导出 .md
          </el-button>
        </div>
      </div>

      <template v-if="viewMode === 'preview'">
        <div class="chapter-preview-box markdown-body" v-html="renderedHtml" />
      </template>

      <template v-else>
        <el-input
          v-model="editTitle"
          placeholder="章节名称"
          maxlength="60"
          show-word-limit
        />
        <el-input
          v-model="editContent"
          type="textarea"
          :rows="15"
          placeholder="在这里编辑章节正文..."
          class="chapter-edit-textarea"
        />
      </template>
    </div>

    <template #footer>
      <div class="dialog-footer-row">
        <el-button type="danger" plain :icon="Delete" @click="handleDelete">
          删除章节
        </el-button>

        <div class="flex items-center gap-2">
          <el-button @click="emit('update:modelValue', false)">关闭</el-button>
          <el-button
            v-if="hasChanges || viewMode === 'edit'"
            type="primary"
            :loading="isSaving"
            :disabled="!hasChanges"
            @click="handleSave"
          >
            保存修改
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-title-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.chapter-editor-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color);
}

.mode-tabs {
  display: flex;
  gap: 6px;
}

.mode-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.mode-tab-btn.active {
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border-color: var(--border-color);
  font-weight: 500;
}

.chapter-preview-box {
  min-height: 280px;
  max-height: 460px;
  overflow-y: auto;
  padding: 16px 18px;
  border-radius: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.75;
}

.chapter-edit-textarea :deep(.el-textarea__inner) {
  font-size: 14px;
  line-height: 1.75;
}

.dialog-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>

