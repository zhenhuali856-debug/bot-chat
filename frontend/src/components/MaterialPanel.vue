<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from '../plugins/element'
import * as api from '../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  workId: {
    type: String,
    default: null
  },
  workTitle: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'insert-to-chat', 'updated'])

const FILTER_TABS = ['全部', '灵感', '金句', '参考', '设定片段']
const MAT_TYPES = ['灵感', '金句', '参考', '设定片段']
const MAX_MAT_WORDS = 300

const materials = ref([])
const selectedId = ref(null)
const currentFilter = ref('全部')
const searchKeyword = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const contentError = ref(false)
const delArmed = ref(false)
let delTimer = null

const contentInputRef = ref(null)

// 右侧编辑表单数据
const form = ref({
  type: '灵感',
  title: '',
  content: '',
  tags: ''
})

const selectedMat = computed(() =>
  materials.value.find(m => m.id === selectedId.value) || null
)

const filteredMaterials = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  return materials.value
    .filter(m => {
      const mType = m.id === selectedId.value ? form.value.type : m.type
      return currentFilter.value === '全部' || mType === currentFilter.value
    })
    .filter(m => {
      if (!kw) return true
      const haystack = `${m.title || ''}${m.content || ''}${m.tags || ''}`.toLowerCase()
      return haystack.includes(kw)
    })
})

const contentWords = computed(() => (form.value.content || '').length)

const getMatBadgeClass = (matType) => {
  const map = {
    '灵感': 'mat-inspire',
    '金句': 'mat-quote',
    '参考': 'mat-ref',
    '设定片段': 'mat-lore'
  }
  return map[matType] || 'mat-inspire'
}

const parseTags = (tagStr) => {
  if (!tagStr) return []
  return tagStr
    .split(/[,，]/)
    .map(t => t.trim())
    .filter(Boolean)
}

const clearDelArmed = () => {
  delArmed.value = false
  if (delTimer) {
    clearTimeout(delTimer)
    delTimer = null
  }
}

const syncFormFromSelected = (mat) => {
  contentError.value = false
  clearDelArmed()
  if (!mat) {
    form.value = {
      type: '灵感',
      title: '',
      content: '',
      tags: ''
    }
    return
  }
  form.value = {
    type: mat.type || '灵感',
    title: mat.title || '',
    content: mat.content || '',
    tags: mat.tags || ''
  }
}

const loadMaterials = async () => {
  if (!props.workId) return
  isLoading.value = true
  try {
    const data = await api.listMaterials(props.workId)
    materials.value = data.materials || []
    if (materials.value.length > 0) {
      const stillExists = materials.value.find(m => m.id === selectedId.value)
      selectedId.value = stillExists ? stillExists.id : materials.value[0].id
    } else {
      selectedId.value = null
    }
    syncFormFromSelected(selectedMat.value)
  } catch (err) {
    ElMessage.error('加载素材库失败: ' + (err.message || '网络错误'))
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.workId) {
      currentFilter.value = '全部'
      searchKeyword.value = ''
      loadMaterials()
    } else {
      clearDelArmed()
    }
  }
)

const setFilter = (tab) => {
  currentFilter.value = tab
}

const selectMat = (mat) => {
  selectedId.value = mat.id
  syncFormFromSelected(mat)
}

const handleNewMaterial = () => {
  searchKeyword.value = ''
  currentFilter.value = '全部'
  const existingDraft = materials.value.find(m => m.isDraft)
  if (existingDraft) {
    selectedId.value = existingDraft.id
    syncFormFromSelected(existingDraft)
  } else {
    const draft = {
      id: '__draft_' + Date.now(),
      work_id: props.workId,
      type: '灵感',
      title: '',
      content: '',
      tags: '',
      isDraft: true
    }
    materials.value.unshift(draft)
    selectedId.value = draft.id
    syncFormFromSelected(draft)
  }
  nextTick(() => {
    if (contentInputRef.value) {
      contentInputRef.value.focus()
    }
  })
}

const handleSave = async (silent = false) => {
  const cur = selectedMat.value
  if (!cur || !props.workId) return null

  const trimmedContent = (form.value.content || '').trim()
  if (!trimmedContent) {
    contentError.value = true
    ElMessage.warning('素材内容不能为空')
    if (contentInputRef.value) contentInputRef.value.focus()
    return null
  }
  contentError.value = false

  const payload = {
    type: form.value.type || '灵感',
    title: (form.value.title || '').trim(),
    content: trimmedContent,
    tags: (form.value.tags || '').trim()
  }

  isSaving.value = true
  try {
    let savedItem = null
    if (cur.isDraft) {
      const res = await api.createMaterial(props.workId, payload)
      savedItem = res.material
      const idx = materials.value.findIndex(m => m.id === cur.id)
      if (idx !== -1) {
        materials.value[idx] = savedItem
      } else {
        materials.value.unshift(savedItem)
      }
      selectedId.value = savedItem.id
      syncFormFromSelected(savedItem)
    } else {
      const res = await api.updateMaterial(cur.id, payload)
      savedItem = res.material
      const idx = materials.value.findIndex(m => m.id === cur.id)
      if (idx !== -1 && savedItem) {
        materials.value[idx] = savedItem
      }
      syncFormFromSelected(savedItem)
    }
    if (!silent) {
      ElMessage.success('素材已保存')
    }
    emit('updated')
    return savedItem
  } catch (err) {
    ElMessage.error('保存素材失败: ' + (err.message || '网络错误'))
    return null
  } finally {
    isSaving.value = false
  }
}

const handleDelete = async () => {
  const cur = selectedMat.value
  if (!cur) return

  if (!delArmed.value) {
    delArmed.value = true
    delTimer = setTimeout(() => {
      delArmed.value = false
    }, 3000)
    return
  }

  clearDelArmed()
  const matTitle = cur.title || '未命名素材'

  if (cur.isDraft) {
    materials.value = materials.value.filter(m => m.id !== cur.id)
    selectedId.value = materials.value.length > 0 ? materials.value[0].id : null
    syncFormFromSelected(selectedMat.value)
    return
  }

  try {
    await api.deleteMaterial(cur.id)
    materials.value = materials.value.filter(m => m.id !== cur.id)
    selectedId.value = materials.value.length > 0 ? materials.value[0].id : null
    syncFormFromSelected(selectedMat.value)
    ElMessage.success(`素材「${matTitle}」已删除`)
    emit('updated')
  } catch (err) {
    ElMessage.error('删除素材失败: ' + (err.message || '网络错误'))
  }
}

const handleInsertToChat = async () => {
  const cur = selectedMat.value
  if (!cur) return

  const trimmedContent = (form.value.content || '').trim()
  if (!trimmedContent) {
    contentError.value = true
    ElMessage.warning('请先填写素材内容')
    if (contentInputRef.value) contentInputRef.value.focus()
    return
  }

  // 若为新建草稿或有改动，顺带自动保存
  if (cur.isDraft || cur.content !== trimmedContent || cur.title !== (form.value.title || '').trim()) {
    await handleSave(true)
  }

  const matTitle = (form.value.title || '').trim() || '未命名素材'
  emit('insert-to-chat', trimmedContent)
  emit('update:modelValue', false)
  ElMessage.success(`已将素材「${matTitle}」插入到输入框`)
}

const closePanel = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="m2-overlay" @click.self="closePanel">
      <div class="panel-dialog">
        <!-- 弹窗顶栏 -->
        <div class="pd-head">
          <h3>
            <span class="pd-icon">📎</span>
            <span>素材库</span>
            <span v-if="workTitle" class="pd-work">· 《{{ workTitle }}》</span>
          </h3>
          <button type="button" class="dlg-close" title="关闭" @click="closePanel">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <!-- 顶部类型筛选 Tabs -->
        <div class="pd-tabs">
          <div
            v-for="tab in FILTER_TABS"
            :key="tab"
            class="pd-tab"
            :class="{ active: currentFilter === tab }"
            @click="setFilter(tab)"
          >
            {{ tab }}
          </div>
        </div>

        <!-- 主体：左列表 + 右编辑器 -->
        <div class="pd-main">
          <!-- 左侧素材列表 -->
          <div class="pd-list">
            <div class="pd-list-head">
              <button type="button" class="pd-new" @click="handleNewMaterial">
                ＋ 新建素材
              </button>
              <div class="pd-search">
                <svg class="ico ico-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M20 20l-3.5-3.5" />
                </svg>
                <input
                  v-model="searchKeyword"
                  type="text"
                  placeholder="搜索标题 / 内容 / 标签"
                />
              </div>
            </div>

            <div class="pd-items">
              <div v-if="filteredMaterials.length === 0" class="pd-empty-list">
                没有符合条件的素材
              </div>

              <div
                v-for="m in filteredMaterials"
                :key="m.id"
                class="pd-item"
                :class="{ selected: m.id === selectedId }"
                @click="selectMat(m)"
              >
                <div class="pi-body">
                  <div class="pi-name">
                    <span class="badge" :class="getMatBadgeClass(m.id === selectedId ? form.type : m.type)">
                      {{ (m.id === selectedId ? form.type : m.type) || '灵感' }}
                    </span>
                    <span class="pi-name-text">
                      {{ (m.id === selectedId ? form.title : m.title) || '未命名素材' }}
                    </span>
                  </div>
                  <div class="pi-sub">
                    {{ (m.id === selectedId ? form.content : m.content) || '暂无内容...' }}
                  </div>
                  <div
                    v-if="parseTags(m.id === selectedId ? form.tags : m.tags).length > 0"
                    class="pd-tags"
                  >
                    <span
                      v-for="tag in parseTags(m.id === selectedId ? form.tags : m.tags)"
                      :key="tag"
                    >
                      #{{ tag }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧素材编辑器 -->
          <div class="pd-editor">
            <div v-if="!selectedMat" class="pd-editor-empty">
              <div class="ee-icon">📎</div>
              <div class="ee-t">选择一个素材查看或编辑</div>
              <div class="ee-d">左侧可按类型筛选，或点「新建素材」沉淀创作灵感</div>
            </div>

            <template v-else>
              <div class="pd-editor-body">
                <div class="pd-sec">
                  素材信息 <span class="sub">灵感 / 金句 / 参考 / 设定片段</span>
                </div>

                <div class="pf">
                  <label>类型</label>
                  <select v-model="form.type">
                    <option v-for="t in MAT_TYPES" :key="t" :value="t">{{ t }}</option>
                  </select>
                </div>

                <div class="pf">
                  <label>标题</label>
                  <input
                    v-model="form.title"
                    maxlength="40"
                    placeholder="给素材起个名字（选填）"
                  />
                </div>

                <div class="pf" :class="{ error: contentError }">
                  <label>内容 <span class="req">*</span></label>
                  <textarea
                    ref="contentInputRef"
                    v-model="form.content"
                    rows="7"
                    placeholder="写下一句金句、一段灵感或参考片段..."
                    @input="contentError = false"
                  />
                  <div class="err">内容不能为空</div>
                </div>

                <div class="pf">
                  <label>标签</label>
                  <input
                    v-model="form.tags"
                    placeholder="逗号分隔，如：场景,悬疑"
                  />
                  <div class="hint">便于按主题检索与后续关键词召回</div>
                </div>
              </div>

              <div class="pd-editor-foot">
                <span class="foot-note" :class="{ warn: contentWords > MAX_MAT_WORDS }">
                  内容 {{ contentWords }} / {{ MAX_MAT_WORDS }} 字{{ contentWords > MAX_MAT_WORDS ? ' · 超出将被截断' : '' }}
                </span>
                <button
                  type="button"
                  class="btn-ghost"
                  :class="{ 'danger-ghost': delArmed }"
                  @click="handleDelete"
                >
                  {{ delArmed ? '再点一次确认' : '删除' }}
                </button>
                <button
                  type="button"
                  class="btn-ghost accent-ghost"
                  @click="handleInsertToChat"
                >
                  插入到对话
                </button>
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="isSaving"
                  @click="handleSave(false)"
                >
                  {{ isSaving ? '保存中...' : '保存修改' }}
                </button>
              </div>
            </template>
          </div>
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
.ico-sm {
  width: 15px;
  height: 15px;
}

.m2-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.66);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(3px);
}

.panel-dialog {
  width: 900px;
  max-width: 100%;
  height: 620px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  color: var(--text-primary);
}

.pd-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
}

.pd-head h3 {
  font-size: 15.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
}

.pd-head h3 .pd-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  font-size: 15px;
}

.pd-head .pd-work {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 400;
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
  transition: all 0.15s ease;
}

.dlg-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.pd-tabs {
  flex: none;
  display: flex;
  gap: 5px;
  padding: 11px 20px 0;
  flex-wrap: wrap;
}

.pd-tab {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  border: 1px solid transparent;
  transition: all 0.15s;
  user-select: none;
}

.pd-tab:hover {
  color: var(--text-primary);
}

.pd-tab.active {
  color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.28);
}

.pd-main {
  flex: 1;
  display: flex;
  min-height: 0;
  margin-top: 12px;
  border-top: 1px solid var(--border-color);
}

.pd-list {
  width: 264px;
  flex: none;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.pd-list-head {
  flex: none;
  padding: 12px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  border-bottom: 1px solid var(--border-color);
}

.pd-new {
  height: 36px;
  border-radius: 9px;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  color: #fff;
  font-size: 12.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  transition: filter 0.15s ease;
}

.pd-new:hover {
  filter: brightness(1.1);
}

.pd-search {
  height: 32px;
  border-radius: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 9px;
  color: var(--text-muted);
}

.pd-search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 12px;
}

.pd-search input::placeholder {
  color: var(--text-muted);
}

.pd-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 12px;
}

.pd-empty-list {
  padding: 28px 10px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.pd-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
  margin-bottom: 5px;
  transition: all 0.15s;
}

.pd-item:hover {
  background: var(--bg-tertiary);
}

.pd-item.selected {
  background: rgba(59, 130, 246, 0.13);
  border-color: rgba(59, 130, 246, 0.32);
}

.pd-item .pi-body {
  flex: 1;
  min-width: 0;
}

.pd-item .pi-name {
  font-size: 12.5px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
}

.pi-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

.pd-item .pi-sub {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pd-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.pd-tags span {
  font-size: 10px;
  color: var(--text-muted);
  background: rgba(148, 163, 184, 0.1);
  border-radius: 4px;
  padding: 1px 5px;
}

.badge {
  font-size: 10px;
  border-radius: 5px;
  padding: 1.5px 5px;
  white-space: nowrap;
  font-weight: 600;
  flex: none;
}

.badge.mat-inspire {
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.15);
}

.badge.mat-quote {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.15);
}

.badge.mat-ref {
  color: #38bdf8;
  background: rgba(14, 165, 233, 0.15);
}

.badge.mat-lore {
  color: #34d399;
  background: rgba(16, 185, 129, 0.15);
}

.pd-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-secondary);
}

.pd-editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px 8px;
}

.pd-editor-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 9px;
  color: var(--text-muted);
}

.pd-editor-empty .ee-icon {
  width: 58px;
  height: 58px;
  border-radius: 17px;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  border: 1px dashed var(--bg-tertiary);
}

.pd-editor-empty .ee-t {
  font-size: 13.5px;
  color: var(--text-secondary);
}

.pd-editor-empty .ee-d {
  font-size: 12px;
  max-width: 280px;
  line-height: 1.6;
}

.pd-sec {
  font-size: 11.5px;
  color: var(--accent-color, #3b82f6);
  font-weight: 600;
  margin: 4px 0 12px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.pd-sec::before {
  content: '';
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: var(--accent-color, #3b82f6);
}

.pd-sec .sub {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 11px;
}

.pf {
  margin-bottom: 14px;
}

.pf label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.pf label .req {
  color: var(--danger-color, #ef4444);
}

.pf input,
.pf select,
.pf textarea {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 12.5px;
  padding: 9px 11px;
  outline: none;
  font-family: inherit;
}

.pf input:focus,
.pf select:focus,
.pf textarea:focus {
  border-color: var(--border-focus, #3b82f6);
}

.pf textarea {
  resize: vertical;
  line-height: 1.6;
  min-height: 120px;
}

.pf input::placeholder,
.pf textarea::placeholder {
  color: var(--text-muted);
}

.pf .err {
  color: var(--danger-color, #ef4444);
  font-size: 11px;
  margin-top: 4px;
  display: none;
}

.pf.error .err {
  display: block;
}

.pf.error input,
.pf.error textarea {
  border-color: var(--danger-color, #ef4444);
}

.pf .hint {
  font-size: 10.5px;
  color: var(--text-muted);
  margin-top: 4px;
}

.pd-editor-foot {
  flex: none;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 12px 22px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.pd-editor-foot .foot-note {
  margin-right: auto;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
}

.pd-editor-foot .foot-note.warn {
  color: var(--warning-color, #f59e0b);
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
  transition: all 0.15s ease;
}

.btn-ghost:hover {
  color: var(--text-primary);
}

.btn-ghost.danger-ghost {
  color: var(--danger-color, #ef4444);
  border-color: rgba(239, 68, 68, 0.45);
}

.btn-ghost.accent-ghost {
  color: var(--accent-color, #3b82f6);
  border-color: rgba(59, 130, 246, 0.42);
}

.btn-ghost.accent-ghost:hover {
  background: rgba(59, 130, 246, 0.1);
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
  transition: filter 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

