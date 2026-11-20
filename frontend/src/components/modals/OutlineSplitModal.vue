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
  outlineOverride: {
    type: String,
    default: null
  },
  selectedModel: {
    type: String,
    default: 'deepseek-chat'
  }
})

const emit = defineEmits(['update:modelValue', 'created'])

const splitCount = ref(5)
const splitStyle = ref('')
const activeCharacters = ref([])
const selectedCharNames = ref([])
const splitPlans = ref([])
const warnText = ref('')
const isGenerating = ref(false)
const isBatchCreating = ref(false)

const effectiveOutline = computed(() => {
  if (props.outlineOverride !== null && props.outlineOverride !== undefined) {
    return props.outlineOverride.trim()
  }
  return (props.work?.outline || '').trim()
})

const checkedCount = computed(() =>
  splitPlans.value.filter(p => p.checked && (p.title || '').trim()).length
)

const statusText = computed(() => {
  if (isGenerating.value) return '生成中…'
  if (splitPlans.value.length === 0) return '尚未生成规划'
  return `已勾选 ${checkedCount.value} / ${splitPlans.value.length} 章 · 已有章节不会被覆盖`
})

const loadActiveCharacters = async () => {
  if (!props.work?.id) {
    activeCharacters.value = []
    selectedCharNames.value = []
    return
  }
  try {
    const data = await api.listCharacters(props.work.id)
    const active = (data.characters || []).filter(c => c.is_active)
    activeCharacters.value = active
    selectedCharNames.value = active.map(c => c.name)
  } catch {
    activeCharacters.value = []
    selectedCharNames.value = []
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.work) {
      splitPlans.value = []
      splitCount.value = 5
      splitStyle.value = ''
      loadActiveCharacters()
      if (!effectiveOutline.value) {
        warnText.value = '当前作品尚未填写大纲。请先保存作品设定并填写大纲，再使用 AI 拆章。'
      } else if (effectiveOutline.value.length < 80) {
        warnText.value = '大纲信息较少，规划仅供参考，建议补充大纲后重试。'
      } else {
        warnText.value = ''
      }
    }
  }
)

const toggleCharSelection = (name) => {
  const idx = selectedCharNames.value.indexOf(name)
  if (idx >= 0) {
    selectedCharNames.value.splice(idx, 1)
  } else {
    selectedCharNames.value.push(name)
  }
}

const handleRunSplit = async () => {
  if (!props.work?.id) return
  if (!effectiveOutline.value) {
    warnText.value = '当前作品尚未填写大纲。请先保存作品设定并填写大纲，再使用 AI 拆章。'
    ElMessage.warning('请先填写大纲，再使用 AI 拆章')
    return
  }

  const count = parseInt(splitCount.value, 10)
  if (isNaN(count) || count < 1 || count > 50) {
    ElMessage.warning('章节数需在 1–50 之间')
    return
  }

  if (effectiveOutline.value.length < 80) {
    warnText.value = '大纲信息较少，规划仅供参考，建议补充大纲后重试。'
  } else {
    warnText.value = ''
  }

  isGenerating.value = true
  splitPlans.value = []

  try {
    const data = await api.splitOutline(props.work.id, {
      chapter_count: count,
      style_hint: splitStyle.value.trim() || undefined,
      character_names: selectedCharNames.value,
      outline_override: effectiveOutline.value,
      model: props.selectedModel
    })

    if (data.warning) {
      warnText.value = data.warning
    }

    const rawList = data.chapters || []
    splitPlans.value = rawList.map((item, idx) => ({
      index: item.index || idx + 1,
      title: item.title || `第${idx + 1}章 · 待定标题`,
      pointsText: Array.isArray(item.points)
        ? item.points.map(p => (p.startsWith('·') ? p : `· ${p}`)).join('\n')
        : String(item.points || ''),
      checked: true
    }))

    ElMessage.success(`已生成 ${splitPlans.value.length} 章规划，标题与要点均可编辑`)
  } catch (err) {
    ElMessage.error(err.message || '生成章节规划失败')
  } finally {
    isGenerating.value = false
  }
}

const toggleAllPlans = (checked) => {
  splitPlans.value.forEach(p => {
    p.checked = checked
  })
}

const removePlan = (idx) => {
  splitPlans.value.splice(idx, 1)
}

const handleBatchCreate = async () => {
  if (!props.work?.id) return
  if (splitPlans.value.length === 0) {
    ElMessage.warning('请先生成章节规划')
    return
  }

  const selected = splitPlans.value.filter(p => p.checked && (p.title || '').trim())
  if (selected.length === 0) {
    ElMessage.warning('请至少勾选一个章节')
    return
  }

  const payload = selected.map((p, idx) => ({
    index: idx + 1,
    title: p.title.trim(),
    points: (p.pointsText || '')
      .split('\n')
      .map(line => line.replace(/^[·\-•*\s]+/, '').trim())
      .filter(Boolean)
  }))

  isBatchCreating.value = true
  try {
    const res = await api.batchCreateChapters(props.work.id, payload)
    const createdCount = res.created_count || 0
    const skippedCount = res.skipped || 0
    const suffix = skippedCount > 0 ? `（跳过 ${skippedCount} 个同名已有章节）` : '（幂等去重，未覆盖已有章节）'
    ElMessage.success(`已批量创建 ${createdCount} 个章节${suffix}`)
    emit('created', res.created || [])
    closeDialog()
  } catch (err) {
    ElMessage.error(err.message || '批量创建章节失败')
  } finally {
    isBatchCreating.value = false
  }
}

const closeDialog = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue && work" class="m3-overlay" @click.self="closeDialog">
      <div class="dialog dialog-wide">
        <div class="dlg-head">
          <h3>✨ AI 一键拆章 · 《{{ work.title }}》</h3>
          <button type="button" class="dlg-close" title="关闭" @click="closeDialog">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div class="dlg-body">
          <div class="split-wrap">
            <!-- ① 生成参数 -->
            <div class="split-config">
              <div class="sc-title">① 生成参数</div>
              <div class="sc-grid">
                <div>
                  <label>章节数（1–50）</label>
                  <input
                    v-model.number="splitCount"
                    type="number"
                    min="1"
                    max="50"
                  />
                </div>
                <div>
                  <label>风格提示（选填）</label>
                  <input
                    v-model="splitStyle"
                    type="text"
                    placeholder="如：节奏紧凑，悬念前置，冷峻克制"
                  />
                </div>
              </div>

              <div v-if="activeCharacters.length > 0" class="split-chars">
                <span class="sc-label">参考角色卡：</span>
                <label
                  v-for="c in activeCharacters"
                  :key="c.id"
                  class="chk-pill"
                >
                  <input
                    type="checkbox"
                    :checked="selectedCharNames.includes(c.name)"
                    @change="toggleCharSelection(c.name)"
                  />
                  <span>{{ c.name }}</span>
                </label>
              </div>

              <div class="split-actions">
                <span class="sa-hint">仅基于大纲与角色设定生成规划，不写正文、不入库</span>
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="isGenerating"
                  @click="handleRunSplit"
                >
                  {{ isGenerating ? '正在规划...' : '生成章节规划' }}
                </button>
              </div>
            </div>

            <!-- 警告提示条 -->
            <div v-if="warnText" class="split-warn show">
              <span>⚠️</span>
              <span>{{ warnText }}</span>
            </div>

            <!-- ② 审核章节规划 -->
            <div>
              <div class="split-result-head">
                <div class="srh-title">
                  ② 审核章节规划
                  <span class="srh-sub">（可编辑标题与要点）</span>
                </div>
                <div class="srh-tools">
                  <button type="button" class="mini-btn-sm" @click="toggleAllPlans(true)">全选</button>
                  <button type="button" class="mini-btn-sm" @click="toggleAllPlans(false)">取消全选</button>
                </div>
              </div>

              <div class="plan-list">
                <div v-if="isGenerating" class="split-typing">
                  <span class="spinner" />
                  <span>AI 正在依据大纲与角色设定生成章节规划…</span>
                </div>

                <div v-else-if="splitPlans.length === 0" class="plan-empty">
                  点上方「生成章节规划」后，可编辑的章节列表会显示在这里。<br />
                  AI 只产出规划草稿，正文仍由逐章对话产生。
                </div>

                <template v-else>
                  <div
                    v-for="(plan, idx) in splitPlans"
                    :key="idx"
                    class="plan-item"
                    :class="{ selected: plan.checked }"
                  >
                    <div class="pi-check">
                      <input v-model="plan.checked" type="checkbox" />
                    </div>
                    <div class="pi-num">{{ idx + 1 }}</div>
                    <div class="pi-main">
                      <input
                        v-model="plan.title"
                        class="pi-title"
                        placeholder="请输入章节标题"
                      />
                      <textarea
                        v-model="plan.pointsText"
                        class="pi-points"
                        rows="2"
                        placeholder="本章核心情节点..."
                      />
                    </div>
                    <span class="pi-del" title="移除本章" @click="removePlan(idx)">✕</span>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="dlg-foot">
          <span class="foot-stat">{{ statusText }}</span>
          <button type="button" class="btn-ghost" @click="closeDialog">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="isBatchCreating || isGenerating || splitPlans.length === 0"
            @click="handleBatchCreate"
          >
            {{ isBatchCreating ? '创建中...' : '批量创建章节' }}
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

.dialog.dialog-wide {
  width: 720px;
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

.split-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.split-config {
  padding: 14px;
  border-radius: 11px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}

.split-config .sc-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.split-config .sc-grid {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 12px;
  align-items: end;
}

.split-config .sc-grid label {
  display: block;
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.split-config input {
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

.split-config input:focus {
  border-color: var(--border-focus, #3b82f6);
}

.split-chars {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}

.split-chars .sc-label {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-right: 2px;
}

.chk-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--text-secondary);
  padding: 5px 9px;
  border-radius: 7px;
  border: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
}

.chk-pill input {
  width: auto;
  height: auto;
  accent-color: var(--accent-color, #3b82f6);
}

.split-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 13px;
}

.split-actions .sa-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: auto;
}

.split-warn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.28);
  color: #fbbf24;
  font-size: 11.5px;
  line-height: 1.5;
}

.split-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 9px;
}

.split-result-head .srh-title {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 7px;
}

.srh-sub {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 400;
}

.split-result-head .srh-tools {
  display: flex;
  gap: 7px;
}

.mini-btn-sm {
  height: 26px;
  padding: 0 12px;
  border-radius: 7px;
  font-size: 11.5px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  background: var(--bg-primary);
}

.mini-btn-sm:hover {
  color: var(--text-primary);
}

.plan-list {
  max-height: 270px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-item {
  display: flex;
  gap: 10px;
  padding: 11px;
  border-radius: 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}

.plan-item.selected {
  border-color: rgba(59, 130, 246, 0.38);
  background: rgba(59, 130, 246, 0.05);
}

.plan-item .pi-check {
  padding-top: 3px;
}

.plan-item .pi-check input {
  accent-color: var(--accent-color, #3b82f6);
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.plan-item .pi-num {
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

.plan-item .pi-main {
  flex: 1;
  min-width: 0;
}

.plan-item .pi-title {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 7px;
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 600;
  padding: 6px 9px;
  outline: none;
  margin-bottom: 6px;
  font-family: inherit;
}

.plan-item .pi-title:focus {
  border-color: var(--border-focus, #3b82f6);
}

.plan-item .pi-points {
  width: 100%;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 11.5px;
  line-height: 1.6;
  resize: vertical;
  min-height: 42px;
  outline: none;
  font-family: inherit;
}

.plan-item .pi-del {
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
  align-self: flex-start;
}

.plan-item .pi-del:hover {
  color: var(--danger-color, #ef4444);
}

.plan-empty {
  padding: 26px 12px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  border: 1px dashed var(--border-color);
  border-radius: 10px;
}

.split-typing {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 22px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12.5px;
  justify-content: center;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-tertiary);
  border-top-color: var(--accent-color, #3b82f6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.dlg-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--border-color);
}

.foot-stat {
  margin-right: auto;
  font-size: 11.5px;
  color: var(--text-muted);
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

