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

const emit = defineEmits(['update:modelValue', 'updated'])

const ROLE_TYPES = ['主角', '配角', '反派', '路人']
const MAX_ACTIVE_CHARS = 8
const MAX_CHAR_WORDS = 400

const characters = ref([])
const selectedId = ref(null)
const searchKeyword = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const nameError = ref(false)
const delArmed = ref(false)
let delTimer = null

const nameInputRef = ref(null)

// 右侧编辑表单数据
const form = ref({
  name: '',
  role_type: '配角',
  traits: '',
  appearance: '',
  speech_style: '',
  background: '',
  relationships: '',
  notes: '',
  is_active: true
})

const selectedChar = computed(() =>
  characters.value.find(c => c.id === selectedId.value) || null
)

const filteredCharacters = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return characters.value
  return characters.value.filter(c => {
    const haystack = `${c.name || ''}${c.traits || ''}${c.speech_style || ''}${c.role_type || ''}`.toLowerCase()
    return haystack.includes(kw)
  })
})

const activeCount = computed(() =>
  characters.value.filter(c => c.is_active && !c.isDraft).length
)

const totalWords = computed(() => {
  const keys = ['traits', 'appearance', 'speech_style', 'background', 'relationships', 'notes']
  return keys.reduce((sum, k) => sum + ((form.value[k] || '').length), 0)
})

const getRoleAvatar = (roleType) => {
  if (roleType === '反派') return '😈'
  if (roleType === '路人') return '🧍'
  return '🧑‍🎤'
}

const getRoleBadgeClass = (roleType) => {
  const map = {
    '主角': 'main',
    '配角': 'support',
    '反派': 'villain',
    '路人': 'extra'
  }
  return map[roleType] || 'support'
}

const syncFormFromSelected = (char) => {
  nameError.value = false
  clearDelArmed()
  if (!char) {
    form.value = {
      name: '',
      role_type: '配角',
      traits: '',
      appearance: '',
      speech_style: '',
      background: '',
      relationships: '',
      notes: '',
      is_active: true
    }
    return
  }
  form.value = {
    name: char.name || '',
    role_type: char.role_type || '配角',
    traits: char.traits || '',
    appearance: char.appearance || '',
    speech_style: char.speech_style || '',
    background: char.background || '',
    relationships: char.relationships || '',
    notes: char.notes || '',
    is_active: char.is_active !== false
  }
}

const clearDelArmed = () => {
  delArmed.value = false
  if (delTimer) {
    clearTimeout(delTimer)
    delTimer = null
  }
}

const loadCharacters = async () => {
  if (!props.workId) return
  isLoading.value = true
  try {
    const data = await api.listCharacters(props.workId)
    characters.value = data.characters || []
    if (characters.value.length > 0) {
      const stillExists = characters.value.find(c => c.id === selectedId.value)
      selectedId.value = stillExists ? stillExists.id : characters.value[0].id
    } else {
      selectedId.value = null
    }
    syncFormFromSelected(selectedChar.value)
  } catch (err) {
    ElMessage.error('加载角色列表失败: ' + (err.message || '网络错误'))
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.workId) {
      searchKeyword.value = ''
      loadCharacters()
    } else {
      clearDelArmed()
    }
  }
)

const selectChar = (char) => {
  selectedId.value = char.id
  syncFormFromSelected(char)
}

const handleNewCharacter = () => {
  searchKeyword.value = ''
  const existingDraft = characters.value.find(c => c.isDraft)
  if (existingDraft) {
    selectedId.value = existingDraft.id
    syncFormFromSelected(existingDraft)
  } else {
    const draft = {
      id: '__draft_' + Date.now(),
      work_id: props.workId,
      name: '',
      role_type: '配角',
      traits: '',
      appearance: '',
      speech_style: '',
      background: '',
      relationships: '',
      notes: '',
      is_active: true,
      isDraft: true
    }
    characters.value.push(draft)
    selectedId.value = draft.id
    syncFormFromSelected(draft)
  }
  nextTick(() => {
    if (nameInputRef.value) {
      nameInputRef.value.focus()
    }
  })
}

const handleToggleActive = async (char) => {
  if (char.isDraft) {
    char.is_active = !char.is_active
    if (selectedId.value === char.id) {
      form.value.is_active = char.is_active
    }
    return
  }
  const nextState = !char.is_active
  try {
    const res = await api.updateCharacter(char.id, { is_active: nextState })
    const updated = res.character
    const idx = characters.value.findIndex(c => c.id === char.id)
    if (idx !== -1 && updated) {
      characters.value[idx] = updated
    } else {
      char.is_active = nextState
    }
    if (selectedId.value === char.id) {
      form.value.is_active = nextState
    }
    ElMessage.success(
      `角色「${char.name}」已${nextState ? '启用，创作时将注入' : '停用，不再注入上下文'}`
    )
    emit('updated')
  } catch (err) {
    ElMessage.error('切换角色状态失败: ' + (err.message || '网络错误'))
  }
}

const handleSave = async () => {
  const cur = selectedChar.value
  if (!cur || !props.workId) return

  const trimmedName = (form.value.name || '').trim()
  if (!trimmedName) {
    nameError.value = true
    ElMessage.warning('请输入角色名')
    if (nameInputRef.value) nameInputRef.value.focus()
    return
  }
  nameError.value = false

  const payload = {
    name: trimmedName,
    role_type: form.value.role_type || '配角',
    traits: (form.value.traits || '').trim(),
    appearance: (form.value.appearance || '').trim(),
    speech_style: (form.value.speech_style || '').trim(),
    background: (form.value.background || '').trim(),
    relationships: (form.value.relationships || '').trim(),
    notes: (form.value.notes || '').trim(),
    is_active: form.value.is_active
  }

  isSaving.value = true
  try {
    if (cur.isDraft) {
      const res = await api.createCharacter(props.workId, payload)
      const created = res.character
      const idx = characters.value.findIndex(c => c.id === cur.id)
      if (idx !== -1) {
        characters.value[idx] = created
      } else {
        characters.value.push(created)
      }
      selectedId.value = created.id
      syncFormFromSelected(created)
    } else {
      const res = await api.updateCharacter(cur.id, payload)
      const updated = res.character
      const idx = characters.value.findIndex(c => c.id === cur.id)
      if (idx !== -1 && updated) {
        characters.value[idx] = updated
      }
      syncFormFromSelected(updated)
    }
    ElMessage.success(`角色「${trimmedName}」已保存，将在本作品创作时注入`)
    emit('updated')
  } catch (err) {
    ElMessage.error('保存角色失败: ' + (err.message || '网络错误'))
  } finally {
    isSaving.value = false
  }
}

const handleDelete = async () => {
  const cur = selectedChar.value
  if (!cur) return

  if (!delArmed.value) {
    delArmed.value = true
    delTimer = setTimeout(() => {
      delArmed.value = false
    }, 3000)
    return
  }

  clearDelArmed()
  const charName = cur.name || '未命名角色'

  if (cur.isDraft) {
    characters.value = characters.value.filter(c => c.id !== cur.id)
    selectedId.value = characters.value.length > 0 ? characters.value[0].id : null
    syncFormFromSelected(selectedChar.value)
    return
  }

  try {
    await api.deleteCharacter(cur.id)
    characters.value = characters.value.filter(c => c.id !== cur.id)
    selectedId.value = characters.value.length > 0 ? characters.value[0].id : null
    syncFormFromSelected(selectedChar.value)
    ElMessage.success(`角色「${charName}」已删除`)
    emit('updated')
  } catch (err) {
    ElMessage.error('删除角色失败: ' + (err.message || '网络错误'))
  }
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
            <span class="pd-icon">👥</span>
            <span>角色管理</span>
            <span v-if="workTitle" class="pd-work">· 《{{ workTitle }}》</span>
          </h3>
          <button type="button" class="dlg-close" title="关闭" @click="closePanel">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <!-- 顶部防 OOC 提示条 -->
        <div class="pd-tip">
          <span>💡</span>
          <span>启用的角色会在本作品创作时自动注入，防止人物崩坏</span>
          <span
            class="tip-stat"
            :style="{ color: activeCount >= MAX_ACTIVE_CHARS ? 'var(--warning-color, #f59e0b)' : 'var(--accent-color, #3b82f6)' }"
          >
            已启用 {{ activeCount }} / {{ MAX_ACTIVE_CHARS }}
          </span>
        </div>

        <!-- 主体：左列表 + 右编辑器 -->
        <div class="pd-main">
          <!-- 左侧角色列表 -->
          <div class="pd-list">
            <div class="pd-list-head">
              <button type="button" class="pd-new" @click="handleNewCharacter">
                ＋ 新建角色
              </button>
              <div class="pd-search">
                <svg class="ico ico-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M20 20l-3.5-3.5" />
                </svg>
                <input
                  v-model="searchKeyword"
                  type="text"
                  placeholder="搜索角色名 / 说话风格"
                />
              </div>
            </div>

            <div class="pd-items">
              <div v-if="filteredCharacters.length === 0" class="pd-empty-list">
                {{ searchKeyword.trim() ? '没有匹配的角色' : '还没有角色，点上方「新建角色」添加' }}
              </div>

              <div
                v-for="c in filteredCharacters"
                :key="c.id"
                class="pd-item"
                :class="{
                  selected: c.id === selectedId,
                  off: !c.is_active
                }"
                @click="selectChar(c)"
              >
                <div class="pi-avatar">{{ getRoleAvatar(c.id === selectedId ? form.role_type : c.role_type) }}</div>
                <div class="pi-body">
                  <div class="pi-name">
                    <span class="pi-name-text">{{ (c.id === selectedId ? form.name : c.name) || '未命名角色' }}</span>
                    <span class="badge" :class="getRoleBadgeClass(c.id === selectedId ? form.role_type : c.role_type)">
                      {{ (c.id === selectedId ? form.role_type : c.role_type) || '配角' }}
                    </span>
                  </div>
                  <div class="pi-sub">
                    {{ (c.id === selectedId ? form.speech_style : c.speech_style) || '未填写说话风格' }}
                  </div>
                </div>
                <div
                  class="switch"
                  :class="{ on: c.is_active }"
                  :title="c.is_active ? '已启用注入' : '已停用'"
                  @click.stop="handleToggleActive(c)"
                />
              </div>
            </div>
          </div>

          <!-- 右侧角色结构化编辑器 -->
          <div class="pd-editor">
            <div v-if="!selectedChar" class="pd-editor-empty">
              <div class="ee-icon">👤</div>
              <div class="ee-t">选择一个角色开始编辑</div>
              <div class="ee-d">左侧点击角色卡片，或点「新建角色」填写结构化设定</div>
            </div>

            <template v-else>
              <div class="pd-editor-body">
                <div class="pd-sec">
                  基础信息 <span class="sub">角色身份与定位</span>
                </div>

                <div class="pf" :class="{ error: nameError }">
                  <label>角色名 <span class="req">*</span></label>
                  <input
                    ref="nameInputRef"
                    v-model="form.name"
                    maxlength="30"
                    placeholder="如：林深"
                    @input="nameError = false"
                  />
                  <div class="err">请输入角色名</div>
                </div>

                <div class="pf">
                  <label>身份定位</label>
                  <select v-model="form.role_type">
                    <option v-for="t in ROLE_TYPES" :key="t" :value="t">{{ t }}</option>
                  </select>
                </div>

                <div class="pd-sec">
                  角色设定 <span class="sub">按结构化格式注入创作上下文</span>
                </div>

                <div class="pf">
                  <label>性格特征</label>
                  <textarea
                    v-model="form.traits"
                    rows="2"
                    placeholder="如：冷静警觉，习惯先观察再开口"
                  />
                </div>

                <div class="pf">
                  <label>外貌</label>
                  <textarea
                    v-model="form.appearance"
                    rows="2"
                    placeholder="如：短发，深色眼窝，左手腕一道旧疤"
                  />
                </div>

                <div class="pf">
                  <label>
                    说话风格 / 口头禅
                    <span class="key-tag">防 OOC 关键</span>
                  </label>
                  <textarea
                    v-model="form.speech_style"
                    rows="2"
                    placeholder="如：冷峻简短，爱用反问，几乎不用感叹号"
                  />
                  <div class="hint">写明语气、句式与口头禅，AI 才不会把不同角色写成同一种声音</div>
                </div>

                <div class="pf">
                  <label>身世背景</label>
                  <textarea
                    v-model="form.background"
                    rows="2"
                    placeholder="角色的来历、经历与关键事件"
                  />
                </div>

                <div class="pf">
                  <label>人物关系</label>
                  <textarea
                    v-model="form.relationships"
                    rows="2"
                    placeholder="与其他角色的羁绊、矛盾或秘密"
                  />
                </div>

                <div class="pf">
                  <label>备注</label>
                  <textarea
                    v-model="form.notes"
                    rows="2"
                    placeholder="其他需要 AI 记住的细节"
                  />
                </div>
              </div>

              <div class="pd-editor-foot">
                <span class="foot-note" :class="{ warn: totalWords > MAX_CHAR_WORDS }">
                  设定约 {{ totalWords }} / {{ MAX_CHAR_WORDS }} 字{{ totalWords > MAX_CHAR_WORDS ? ' · 超出部分将被截断' : '' }}
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
                  class="btn-primary"
                  :disabled="isSaving"
                  @click="handleSave"
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

.pd-tip {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 20px 0;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.pd-tip .tip-stat {
  margin-left: auto;
  white-space: nowrap;
  color: var(--accent-color);
  font-size: 11.5px;
  font-weight: 600;
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

.pd-item.off .pi-name,
.pd-item.off .pi-sub {
  opacity: 0.5;
}

.pd-item .pi-avatar {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  background: var(--bg-secondary);
}

.pd-item.selected .pi-avatar {
  background: rgba(59, 130, 246, 0.2);
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

.badge {
  font-size: 10px;
  border-radius: 5px;
  padding: 1.5px 5px;
  white-space: nowrap;
  font-weight: 600;
  flex: none;
}

.badge.main {
  color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.14);
}

.badge.support {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.14);
}

.badge.villain {
  color: #f87171;
  background: rgba(248, 113, 113, 0.14);
}

.badge.extra {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.14);
}

.switch {
  width: 32px;
  height: 18px;
  flex: none;
  border-radius: 99px;
  background: var(--bg-tertiary);
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
}

.switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.switch.on {
  background: var(--success-color, #10b981);
}

.switch.on::after {
  transform: translateX(14px);
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

.pf label .key-tag {
  font-size: 10px;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.14);
  border-radius: 4px;
  padding: 1px 5px;
  font-weight: 600;
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
  min-height: 54px;
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

