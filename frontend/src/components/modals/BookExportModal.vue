<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from '../../plugins/element'
import * as api from '../../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  work: {
    type: Object,
    default: null
  },
  chapters: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const exportFormat = ref('md')
const activeCharCount = ref(0)
const isExporting = ref(false)

const workChapterCount = computed(() => {
  if (!props.work) return 0
  return props.chapters.filter(c => c.work_id === props.work.id).length
})

const safeBookFilename = computed(() => {
  const rawTitle = (props.work?.title || '未命名作品').trim()
  const clean = rawTitle.replace(/[\\/:*?"<>|]+/g, '_') || '未命名作品'
  return `《${clean}》-全书.md`
})

const loadCharCount = async () => {
  if (!props.work?.id) {
    activeCharCount.value = 0
    return
  }
  try {
    const data = await api.listCharacters(props.work.id)
    const chars = data.characters || []
    activeCharCount.value = chars.filter(c => c.is_active).length
  } catch {
    activeCharCount.value = 0
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.work) {
      exportFormat.value = 'md'
      loadCharCount()
    }
  }
)

const closeDialog = () => {
  emit('update:modelValue', false)
}

const handleDoExport = async () => {
  if (!props.work?.id) return
  if (exportFormat.value === 'txt') {
    ElMessage.info('TXT 格式即将支持')
    return
  }

  isExporting.value = true
  try {
    const mdText = await api.exportWorkBook(props.work.id, 'md')
    const blob = new Blob([mdText], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = safeBookFilename.value
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success(
      `已生成 ${safeBookFilename.value}（设定 + ${activeCharCount.value} 位角色 + ${workChapterCount.value} 章正文）`
    )
    closeDialog()
  } catch (err) {
    ElMessage.error(err.message || '导出整书失败')
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue && work" class="m3-overlay" @click.self="closeDialog">
      <div class="dialog dialog-export">
        <div class="dlg-head">
          <h3>📖 导出整书 · 《{{ work.title }}》</h3>
          <button type="button" class="dlg-close" title="关闭" @click="closeDialog">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div class="dlg-body">
          <div class="form-row">
            <label>导出格式</label>
            <select v-model="exportFormat" class="form-select">
              <option value="md">Markdown（.md）— 本期支持</option>
              <option value="txt" disabled>TXT（.txt）— 即将支持</option>
            </select>
          </div>

          <div class="form-row">
            <label>导出内容（按此顺序写入单文件）</label>
            <div class="export-struct">
              <div class="es-row">
                <span class="es-num">1</span>
                <span class="es-ico">📄</span>
                <div class="es-text">
                  <b>封面标题</b>
                  <small>作品名 · 体裁 · 目标字数</small>
                </div>
              </div>
              <div class="es-row">
                <span class="es-num">2</span>
                <span class="es-ico">⚙️</span>
                <div class="es-text">
                  <b>作品设定</b>
                  <small>体裁 / 简介 / 大纲 / 目标字数</small>
                </div>
              </div>
              <div class="es-row">
                <span class="es-num">3</span>
                <span class="es-ico">👥</span>
                <div class="es-text">
                  <b>人物表</b>
                  <small>仅启用的角色卡，来自 characters 表</small>
                </div>
                <span class="es-count">{{ activeCharCount }} 位</span>
              </div>
              <div class="es-row">
                <span class="es-num">4</span>
                <span class="es-ico">📚</span>
                <div class="es-text">
                  <b>章节正文</b>
                  <small>按 sort_order 升序；空章节标注「（未写正文）」</small>
                </div>
                <span class="es-count">{{ workChapterCount }} 章</span>
              </div>
            </div>
          </div>

          <div class="form-row">
            <label>文件名预览</label>
            <div class="filename-pill">📦 {{ safeBookFilename }}</div>
          </div>

          <div class="form-note">
            💡 不输出对话气泡与思考过程；空章节会保留标题并标注，不会报错。作品无章节时仍生成「仅设定 + 人物表」的文件。
          </div>
        </div>

        <div class="dlg-foot">
          <button type="button" class="btn-ghost" @click="closeDialog">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="isExporting"
            @click="handleDoExport"
          >
            {{ isExporting ? '导出中...' : '开始导出' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ico {
  width: 18px;
  height: 18px;
  flex: none;
  display: inline-block;
  vertical-align: middle;
}

.m3-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.66);
  z-index: 2050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(3px);
}

.dialog {
  width: 520px;
  max-width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  color: var(--text-primary);
}

.dialog.dialog-export {
  width: 600px;
}

.dlg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-color);
}

.dlg-head h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.dlg-close {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
}

.dlg-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.dlg-body {
  padding: 18px 22px;
}

.form-row {
  margin-bottom: 16px;
}

.form-row label {
  display: block;
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-bottom: 7px;
}

.form-select {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 9px;
  color: var(--text-primary);
  font-size: 13px;
  padding: 10px 12px;
  outline: none;
  font-family: inherit;
}

.form-select:focus {
  border-color: var(--border-focus, #3b82f6);
}

.export-struct {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.export-struct .es-row {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: 9px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}

.export-struct .es-num {
  width: 22px;
  height: 22px;
  flex: none;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.14);
  color: var(--accent-color, #3b82f6);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.export-struct .es-ico {
  font-size: 16px;
  flex: none;
}

.export-struct .es-text {
  flex: 1;
  min-width: 0;
}

.export-struct .es-text b {
  display: block;
  font-size: 12.5px;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.export-struct .es-text small {
  font-size: 11px;
  color: var(--text-muted);
}

.export-struct .es-count {
  font-size: 11px;
  color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.12);
  border-radius: 5px;
  padding: 2px 7px;
  white-space: nowrap;
}

.filename-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  font-family: var(--mono, Consolas, monospace);
  font-size: 12px;
  color: var(--text-secondary);
}

.form-note {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.6;
  background: var(--bg-primary);
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 6px;
}

.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--border-color);
}

.btn-ghost {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: transparent;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-ghost:hover {
  color: var(--text-primary);
}

.btn-primary {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

