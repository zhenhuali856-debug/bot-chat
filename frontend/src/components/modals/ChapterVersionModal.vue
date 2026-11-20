<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from '../../plugins/element'
import * as api from '../../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  chapter: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const versions = ref([])
const currentChapterData = ref(null)
const selectedVerA = ref('current')
const selectedVerB = ref('current')
const isSaving = ref(false)

const allVersionOptions = computed(() => {
  const list = versions.value.map(v => ({
    key: String(v.version_no),
    label: `v${v.version_no} · ${v.note || '历史快照'}`,
    content: v.content || ''
  }))
  list.push({
    key: 'current',
    label: `当前正文（最新）`,
    content: currentChapterData.value?.content ?? props.chapter?.content ?? ''
  })
  return list
})

const getVersionContent = (key) => {
  const found = allVersionOptions.value.find(o => o.key === key)
  return found ? found.content : ''
}

const getVersionLabel = (key) => {
  if (key === 'current') return '当前正文'
  return `v${key}`
}

const diffRows = computed(() => {
  const textA = getVersionContent(selectedVerA.value)
  const textB = getVersionContent(selectedVerB.value)
  const linesA = textA ? textA.split('\n') : []
  const linesB = textB ? textB.split('\n') : []
  const maxLen = Math.max(linesA.length, linesB.length, 1)

  const rowsA = []
  const rowsB = []

  for (let i = 0; i < maxLen; i++) {
    const x = linesA[i]
    const y = linesB[i]
    if (x === y) {
      rowsA.push({ type: 'same', text: x || '' })
      rowsB.push({ type: 'same', text: y || '' })
    } else {
      rowsA.push({
        type: 'del',
        text: x !== undefined ? x : '（无此行）'
      })
      rowsB.push({
        type: 'add',
        text: y !== undefined ? y : '（无此行）'
      })
    }
  }
  return { rowsA, rowsB }
})

const loadVersions = async () => {
  if (!props.chapter?.id) return
  try {
    const data = await api.listChapterVersions(props.chapter.id)
    versions.value = data.versions || []
    currentChapterData.value = data.chapter || props.chapter
    if (versions.value.length >= 2) {
      selectedVerA.value = String(versions.value[versions.value.length - 2].version_no)
      selectedVerB.value = String(versions.value[versions.value.length - 1].version_no)
    } else if (versions.value.length === 1) {
      selectedVerA.value = String(versions.value[0].version_no)
      selectedVerB.value = 'current'
    } else {
      selectedVerA.value = 'current'
      selectedVerB.value = 'current'
    }
  } catch (err) {
    ElMessage.error('加载章节版本失败: ' + (err.message || '网络错误'))
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.chapter) {
      loadVersions()
    }
  }
)

const handleSaveVersion = async () => {
  if (!props.chapter?.id) return
  isSaving.value = true
  try {
    const nextNo = versions.value.length + 1
    const res = await api.createChapterVersion(props.chapter.id, {
      note: `v${nextNo} · 手动存版`
    })
    const newVer = res.version
    if (newVer) {
      await loadVersions()
      selectedVerB.value = String(newVer.version_no)
      ElMessage.success(`已将当前正文存为新版本 v${newVer.version_no}`)
    }
  } catch (err) {
    ElMessage.error('保存章节版本失败: ' + (err.message || '网络错误'))
  } finally {
    isSaving.value = false
  }
}

const closeDialog = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue && chapter" class="m3-overlay" @click.self="closeDialog">
      <div class="dialog dialog-wide">
        <div class="dlg-head">
          <h3>
            🕘 版本历史与对比 · <span>{{ chapter.title }}</span>
          </h3>
          <button type="button" class="dlg-close" title="关闭" @click="closeDialog">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div class="dlg-body">
          <div class="ver-toolbar">
            <div class="vt-field">
              <label>版本 A（旧）</label>
              <select v-model="selectedVerA">
                <option v-for="opt in allVersionOptions" :key="'a-' + opt.key" :value="opt.key">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <span class="vt-vs">VS</span>
            <div class="vt-field">
              <label>版本 B（新）</label>
              <select v-model="selectedVerB">
                <option v-for="opt in allVersionOptions" :key="'b-' + opt.key" :value="opt.key">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <button
              type="button"
              class="btn-ghost accent-ghost"
              @click="ElMessage.success('已刷新版本并排对比视图')"
            >
              对比
            </button>
            <button
              type="button"
              class="btn-ghost"
              :disabled="isSaving"
              @click="handleSaveVersion"
            >
              {{ isSaving ? '保存中...' : '存为版本' }}
            </button>
          </div>

          <div class="diff-legend">
            <span><i class="lg-del" /> 删除 / 旧内容</span>
            <span><i class="lg-add" /> 新增 / 新内容</span>
            <span style="margin-left: auto">已存 {{ versions.length }} 个版本（单章最多保留 20 个版本，超出淘汰最旧）</span>
          </div>

          <div class="diff-grid">
            <div class="diff-col">
              <div class="dc-head">
                <span>版本 A · {{ getVersionLabel(selectedVerA) }}</span>
                <span>旧 →</span>
              </div>
              <div class="dc-body">
                <div
                  v-for="(row, idx) in diffRows.rowsA"
                  :key="'ra-' + idx"
                  class="diff-line"
                  :class="{ del: row.type === 'del' }"
                >
                  <span v-if="row.type === 'del'" class="dl-mark">−</span>{{ row.text }}
                </div>
              </div>
            </div>

            <div class="diff-col">
              <div class="dc-head">
                <span>版本 B · {{ getVersionLabel(selectedVerB) }}</span>
                <span>→ 新</span>
              </div>
              <div class="dc-body">
                <div
                  v-for="(row, idx) in diffRows.rowsB"
                  :key="'rb-' + idx"
                  class="diff-line"
                  :class="{ add: row.type === 'add' }"
                >
                  <span v-if="row.type === 'add'" class="dl-mark">+</span>{{ row.text }}
                </div>
              </div>
            </div>
          </div>

          <div class="form-note" style="margin: 12px 0 0">
            💡 点右上角「存为版本」可将章节当前正文保存为历史快照，随时与新稿并排对比差异。
          </div>
        </div>

        <div class="dlg-foot">
          <button type="button" class="btn-primary" @click="closeDialog">完成</button>
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
  width: 720px;
  max-width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  color: var(--text-primary);
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

.ver-toolbar {
  display: flex;
  align-items: end;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  margin-bottom: 12px;
}

.ver-toolbar .vt-field {
  flex: 1;
  min-width: 0;
}

.ver-toolbar .vt-field label {
  display: block;
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.ver-toolbar select {
  width: 100%;
  height: 34px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 12.5px;
  padding: 0 10px;
  outline: none;
  font-family: inherit;
}

.ver-toolbar .vt-vs {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 700;
  padding-bottom: 9px;
}

.diff-legend {
  display: flex;
  gap: 14px;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 9px;
}

.diff-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.diff-legend i {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  display: inline-block;
}

.diff-legend .lg-del {
  background: rgba(239, 68, 68, 0.28);
}

.diff-legend .lg-add {
  background: rgba(16, 185, 129, 0.26);
}

.diff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.diff-col {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  background: var(--bg-primary);
}

.diff-col .dc-head {
  padding: 9px 12px;
  font-size: 11.5px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  justify-content: space-between;
}

.diff-col .dc-body {
  padding: 8px;
  max-height: 260px;
  overflow-y: auto;
}

.diff-line {
  font-size: 12px;
  line-height: 1.7;
  padding: 3px 8px;
  border-radius: 5px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.diff-line.del {
  background: rgba(239, 68, 68, 0.16);
  color: #fca5a5;
}

.diff-line.add {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
}

.diff-line .dl-mark {
  display: inline-block;
  width: 14px;
  opacity: 0.7;
  font-weight: 700;
}

.form-note {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.6;
  background: var(--bg-primary);
  padding: 10px 12px;
  border-radius: 8px;
}

.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--border-color);
}

.btn-ghost {
  height: 34px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: transparent;
  font-size: 12.5px;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.btn-ghost:hover {
  color: var(--text-primary);
}

.btn-ghost.accent-ghost {
  color: var(--accent-color, #3b82f6);
  border-color: rgba(59, 130, 246, 0.42);
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

.btn-primary:hover {
  filter: brightness(1.1);
}
</style>

