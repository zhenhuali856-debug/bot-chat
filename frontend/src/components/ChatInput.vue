<script setup>
import { ref, computed } from 'vue'
import {
  Position,
  VideoPause,
  Document,
  CloseBold,
  ElTooltip,
  ElMessage
} from '../plugins/element'
import { readMarkdownFile, isMarkdownLikeFile, formatCharCount } from '../utils/fileReader'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  hasApiKey: {
    type: Boolean,
    default: true
  },
  selectedModel: {
    type: String,
    default: 'deepseek-chat'
  },
  promptFiles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'update:modelValue',
  'send',
  'stop',
  'upload-prompt-files',
  'preview-prompt-file',
  'toggle-prompt-file',
  'delete-prompt-file',
  'run-with-prompts'
])

const mdFileInput = ref(null)
const isDragging = ref(false)
const isReadingFiles = ref(false)

const activePromptFiles = computed(() =>
  props.promptFiles.filter(f => f.enabled)
)

const totalActiveChars = computed(() =>
  activePromptFiles.value.reduce((sum, f) => sum + (f.char_count || f.content?.length || 0), 0)
)

const scopeLabel = (scope) => {
  if (scope === 'global') return '全局'
  if (scope === 'work') return '作品'
  return '本会话'
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}

const triggerFileSelect = () => {
  if (props.isLoading) return
  if (mdFileInput.value) {
    mdFileInput.value.value = ''
    mdFileInput.value.click()
  }
}

const processSelectedFiles = async (fileList) => {
  const files = Array.from(fileList || [])
  if (files.length === 0) return

  const validFiles = files.filter(f => isMarkdownLikeFile(f.name))
  const invalidCount = files.length - validFiles.length
  if (invalidCount > 0) {
    ElMessage.warning('仅支持读取 .md / .markdown / .txt 格式的提示词文件')
  }
  if (validFiles.length === 0) return

  isReadingFiles.value = true
  try {
    const parsedItems = []
    for (const file of validFiles) {
      const content = await readMarkdownFile(file)
      if (!content.trim()) {
        ElMessage.warning(`文件《${file.name}》内容为空，已跳过`)
        continue
      }
      parsedItems.push({
        filename: file.name,
        content
      })
    }

    if (parsedItems.length > 0) {
      emit('upload-prompt-files', parsedItems)
    }
  } catch (err) {
    ElMessage.error(err.message || '读取 Markdown 文件失败')
  } finally {
    isReadingFiles.value = false
  }
}

const onFileChange = async (event) => {
  await processSelectedFiles(event.target.files)
  if (mdFileInput.value) {
    mdFileInput.value.value = ''
  }
}

const onDragOver = (e) => {
  e.preventDefault()
  isDragging.value = true
}

const onDragLeave = (e) => {
  if (e.currentTarget.contains(e.relatedTarget)) return
  isDragging.value = false
}

const onDrop = async (e) => {
  e.preventDefault()
  isDragging.value = false
  if (props.isLoading) return
  await processSelectedFiles(e.dataTransfer?.files)
}
</script>

<template>
  <el-footer class="input-panel" height="auto">
    <div
      class="input-container"
      :class="{ 'is-dragging': isDragging }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <!-- 已上传的 MD 提示词文件标签栏 -->
      <div v-if="promptFiles.length > 0" class="prompt-chips-bar">
        <div
          v-for="pf in promptFiles"
          :key="pf.id"
          class="prompt-chip"
          :class="{ 'is-disabled': !pf.enabled }"
        >
          <el-tooltip
            :content="pf.enabled ? '点击暂停注入此提示词' : '点击启用并喂给模型'"
            placement="top"
          >
            <button
              type="button"
              class="chip-status-dot"
              :class="{ active: pf.enabled }"
              @click.stop="emit('toggle-prompt-file', pf)"
            />
          </el-tooltip>

          <button
            type="button"
            class="chip-main"
            title="点击阅读 / 编辑 Markdown 提示词内容"
            @click="emit('preview-prompt-file', pf)"
          >
            <el-icon class="chip-icon"><Document /></el-icon>
            <span class="chip-name">{{ pf.filename }}</span>
            <span class="chip-scope">{{ scopeLabel(pf.scope) }}</span>
            <span class="chip-size">{{ formatCharCount(pf.char_count || pf.content?.length || 0) }}</span>
          </button>

          <button
            type="button"
            class="chip-remove"
            title="移除此提示词文件"
            @click.stop="emit('delete-prompt-file', pf)"
          >
            <el-icon><CloseBold /></el-icon>
          </button>
        </div>

        <button
          v-if="activePromptFiles.length > 0 && !modelValue.trim() && !isLoading && hasApiKey"
          type="button"
          class="quick-run-pill"
          title="不输入额外文字，直接让模型读取以上提示词并回复"
          @click="emit('run-with-prompts')"
        >
          ▶ 让模型按提示词开始
        </button>
      </div>

      <!-- 多行输入文本框 -->
      <el-input
        :model-value="modelValue"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        placeholder="输入你的创作需求"
        class="custom-chat-input"
        :disabled="isLoading || !hasApiKey"
        @update:model-value="emit('update:modelValue', $event)"
        @keydown="handleKeydown"
      />

      <!-- 底部操作栏：左侧 MD 文件工具 + 右侧发送/停止按钮 -->
      <div class="input-toolbar">
        <div class="toolbar-left">
          <el-tooltip content="上传并读取 .md 提示词文件喂给模型（支持多选与拖拽）" placement="top">
            <button
              type="button"
              class="tool-icon-btn"
              :disabled="isLoading || isReadingFiles"
              @click="triggerFileSelect"
            >
              <el-icon><Document /></el-icon>
              <span class="tool-btn-label">添加 MD 提示词</span>
            </button>
          </el-tooltip>
        </div>

        <div class="action-buttons">
          <el-button
            v-if="isLoading"
            type="danger"
            class="stop-btn"
            :icon="VideoPause"
            @click="emit('stop')"
          >
            停止生成
          </el-button>

          <el-button
            v-else
            type="primary"
            class="send-btn"
            :icon="Position"
            :disabled="!modelValue.trim() || !hasApiKey"
            @click="emit('send')"
          >
            发送
          </el-button>
        </div>
      </div>

      <!-- 隐藏的多文件选择器 -->
      <input
        ref="mdFileInput"
        type="file"
        accept=".md,.markdown,.txt"
        multiple
        style="display: none"
        @change="onFileChange"
      />
    </div>

    <div class="input-tip">
      Rabbit AI 支持服务端多轮记忆持久化 · 当前模型: {{ selectedModel }}
    </div>
  </el-footer>
</template>

<style scoped>
.input-panel {
  padding: 12px 20px 18px 20px;
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.input-container {
  width: 100%;
  max-width: 840px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
}

.input-container:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.15);
}

.input-container.is-dragging {
  border-color: var(--accent-color, #3b82f6);
  border-style: dashed;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.prompt-chips-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--border-color);
}

.prompt-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-primary);
  transition: all 0.2s;
}

.prompt-chip.is-disabled {
  opacity: 0.55;
}

.prompt-chip.is-disabled .chip-name {
  text-decoration: line-through;
}

.chip-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  padding: 0;
  cursor: pointer;
  background: var(--text-muted);
  transition: transform 0.15s, background-color 0.15s;
}

.chip-status-dot.active {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}

.chip-status-dot:hover {
  transform: scale(1.25);
}

.chip-main {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
}

.chip-main:hover .chip-name {
  color: var(--accent-color, #60a5fa);
  text-decoration: underline;
}

.chip-icon {
  font-size: 13px;
  color: var(--accent-color, #60a5fa);
}

.chip-name {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.chip-scope {
  font-size: 10px;
  padding: 0 5px;
  border-radius: 4px;
  background: var(--reasoning-bg);
  color: var(--text-secondary);
}

.chip-size {
  font-size: 11px;
  color: var(--text-muted);
}

.chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 10px;
  padding: 0;
}

.chip-remove:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}

.quick-run-pill {
  border: 1px solid var(--reasoning-border);
  background: var(--reasoning-bg);
  color: var(--text-primary);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-run-pill:hover {
  border-color: var(--accent-color, #3b82f6);
  transform: translateY(-1px);
}

.custom-chat-input {
  width: 100%;
}

.custom-chat-input :deep(.el-textarea__inner) {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
  color: var(--text-primary) !important;
  font-size: 0.95rem;
  padding: 2px 0;
  resize: none;
}

.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 2px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.tool-icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.tool-icon-btn:hover:not(:disabled) {
  border-color: var(--accent-color, #3b82f6);
  color: var(--accent-color, #60a5fa);
}

.tool-icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.prompt-status-hint {
  font-size: 12px;
  color: #10b981;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.prompt-muted-hint {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-buttons {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.send-btn,
.stop-btn {
  border-radius: 10px;
  padding: 8px 16px;
  font-weight: 500;
  height: 34px;
}

.send-btn {
  background: var(--accent-gradient);
  border: none;
}

.send-btn:hover {
  opacity: 0.9;
}

.input-tip {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 8px;
}
</style>
