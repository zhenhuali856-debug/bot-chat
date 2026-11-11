<script setup>
import { ref, computed, watch } from 'vue'
import {
  ElDialog,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElSwitch,
  ElTag,
  ElMessage,
  Document,
  Edit,
  View,
  Delete,
  Upload
} from '../plugins/element'
import { renderMarkdown } from '../utils/markdown'
import { readMarkdownFile, isMarkdownLikeFile, formatCharCount } from '../utils/fileReader'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  file: {
    type: Object,
    default: null
  },
  currentWork: {
    type: Object,
    default: null
  },
  currentSessionId: {
    type: String,
    default: null
  }
})

const emit = defineEmits([
  'update:modelValue',
  'save',
  'delete'
])

const viewMode = ref('preview') // 'preview' | 'edit'
const editFilename = ref('')
const editContent = ref('')
const editScope = ref('session')
const editEnabled = ref(true)
const isSaving = ref(false)
const replaceInputRef = ref(null)

watch(
  () => [props.modelValue, props.file],
  ([visible, file]) => {
    if (visible && file) {
      editFilename.value = file.filename || ''
      editContent.value = file.content || ''
      editScope.value = file.scope || 'session'
      editEnabled.value = file.enabled !== false
      viewMode.value = 'preview'
    }
  },
  { immediate: true }
)

const renderedHtml = computed(() => renderMarkdown(editContent.value))

const hasChanges = computed(() => {
  if (!props.file) return false
  return (
    editFilename.value.trim() !== (props.file.filename || '') ||
    editContent.value !== (props.file.content || '') ||
    editScope.value !== (props.file.scope || 'session') ||
    editEnabled.value !== (props.file.enabled !== false)
  )
})

const scopeOptions = computed(() => {
  const opts = [
    { value: 'session', label: '当前章节 / 会话' }
  ]
  if (props.currentWork) {
    opts.push({ value: 'work', label: `当前作品《${props.currentWork.title}》全部章节` })
  }
  opts.push({ value: 'global', label: '全局所有对话' })
  return opts
})

const handleClose = () => {
  emit('update:modelValue', false)
}

const handleSave = async () => {
  const name = editFilename.value.trim()
  if (!name) {
    ElMessage.warning('提示词文件名不能为空')
    return
  }
  if (!editContent.value.trim()) {
    ElMessage.warning('提示词内容不能为空')
    return
  }
  isSaving.value = true
  try {
    const payload = {
      filename: name,
      content: editContent.value,
      scope: editScope.value,
      enabled: editEnabled.value
    }
    if (editScope.value === 'work' && props.currentWork) {
      payload.work_id = props.currentWork.id
    } else if (editScope.value === 'session' && props.currentSessionId) {
      payload.session_id = props.currentSessionId
    }
    emit('save', props.file.id, payload)
    emit('update:modelValue', false)
  } finally {
    isSaving.value = false
  }
}

const triggerReplaceFile = () => {
  if (replaceInputRef.value) {
    replaceInputRef.value.value = ''
    replaceInputRef.value.click()
  }
}

const onReplaceFileSelected = async (event) => {
  const f = event.target.files?.[0]
  if (!f) return
  if (!isMarkdownLikeFile(f.name)) {
    ElMessage.warning('请选择 .md / .markdown / .txt 文件')
    return
  }
  try {
    const content = await readMarkdownFile(f)
    if (!content.trim()) {
      ElMessage.warning(`文件 ${f.name} 内容为空`)
      return
    }
    editFilename.value = f.name
    editContent.value = content
    ElMessage.success(`已重新读取 ${f.name}，点击“保存修改”生效`)
  } catch (err) {
    ElMessage.error(err.message || '读取文件失败')
  }
}

const handleDelete = () => {
  if (!props.file) return
  emit('delete', props.file)
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="680px"
    class="prompt-file-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="dialog-header-row">
        <div class="flex items-center gap-2">
          <el-icon class="text-blue-400"><Document /></el-icon>
          <span class="dialog-title-text">Markdown 提示词文件</span>
          <el-tag size="small" type="info" effect="plain">
            {{ formatCharCount(editContent.length) }}
          </el-tag>
          <el-tag size="small" :type="editEnabled ? 'success' : 'info'" effect="plain">
            {{ editEnabled ? '已启用（喂给模型）' : '已暂停' }}
          </el-tag>
        </div>
      </div>
    </template>

    <div v-if="file" class="prompt-modal-body">
      <!-- 顶部元数据配置区 -->
      <div class="meta-bar">
        <div class="meta-item flex-1">
          <label class="meta-label">文件名</label>
          <el-input
            v-model="editFilename"
            size="small"
            placeholder="例如：文风与规则.md"
          />
        </div>

        <div class="meta-item scope-select-box">
          <label class="meta-label">生效范围</label>
          <el-select v-model="editScope" size="small" class="w-full">
            <el-option
              v-for="opt in scopeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </div>

        <div class="meta-item switch-box">
          <label class="meta-label">喂给模型</label>
          <el-switch v-model="editEnabled" size="small" />
        </div>
      </div>

      <!-- 模式切换栏：Markdown 渲染阅读 vs 源码编辑 -->
      <div class="mode-toolbar">
        <div class="mode-tabs">
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: viewMode === 'preview' }"
            @click="viewMode = 'preview'"
          >
            <el-icon><View /></el-icon>
            <span>渲染阅读</span>
          </button>
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: viewMode === 'edit' }"
            @click="viewMode = 'edit'"
          >
            <el-icon><Edit /></el-icon>
            <span>编辑源码</span>
          </button>
        </div>

        <el-button size="small" plain :icon="Upload" @click="triggerReplaceFile">
          重新读取本地 MD
        </el-button>
      </div>

      <!-- 内容阅读/编辑区 -->
      <div v-if="viewMode === 'preview'" class="md-preview-box markdown-body" v-html="renderedHtml" />

      <el-input
        v-else
        v-model="editContent"
        type="textarea"
        :rows="14"
        placeholder="在这里编写或修改喂给模型的 Markdown 提示词..."
        class="md-source-textarea"
      />
    </div>

    <template #footer>
      <div class="dialog-footer-row">
        <el-button type="danger" plain :icon="Delete" @click="handleDelete">
          移除文件
        </el-button>

        <div class="flex items-center gap-2">
          <el-button @click="handleClose">取消</el-button>
          <el-button
            type="primary"
            :loading="isSaving"
            :disabled="!hasChanges && viewMode === 'preview'"
            @click="handleSave"
          >
            保存修改
          </el-button>
        </div>
      </div>
    </template>

    <input
      ref="replaceInputRef"
      type="file"
      accept=".md,.markdown,.txt"
      style="display: none"
      @change="onReplaceFileSelected"
    />
  </el-dialog>
</template>

<style scoped>
.dialog-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.prompt-modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.scope-select-box {
  width: 220px;
}

.switch-box {
  align-items: center;
  padding-bottom: 4px;
}

.meta-label {
  font-size: 12px;
  color: var(--text-muted);
}

.mode-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 4px;
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

.md-preview-box {
  min-height: 260px;
  max-height: 420px;
  overflow-y: auto;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 13.5px;
  line-height: 1.65;
}

.md-source-textarea :deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.dialog-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>

