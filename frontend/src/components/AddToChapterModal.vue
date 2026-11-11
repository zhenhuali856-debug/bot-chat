<script setup>
import { ref, computed, watch } from 'vue'
import {
  ElDialog,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElTag,
  ElMessage,
  Notebook,
  Plus
} from '../plugins/element'
import * as api from '../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  works: {
    type: Array,
    default: () => []
  },
  chapters: {
    type: Array,
    default: () => []
  },
  initialContent: {
    type: String,
    default: ''
  },
  defaultWorkId: {
    type: String,
    default: null
  },
  sourceSessionId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const genreOptions = [
  '科幻小说',
  '奇幻仙侠',
  '悬疑推理',
  '都市言情',
  '短篇小说',
  '剧本文本',
  '商业文案',
  '故事大纲',
  '散文随笔',
  '诗歌'
]

const targetWorkId = ref('')
const isCreatingNewWork = ref(false)
const newWorkTitle = ref('')
const newWorkGenre = ref('科幻小说')

const actionMode = ref('create') // 'create' | 'append'
const chapterTitle = ref('')
const targetChapterId = ref('')
const appendMethod = ref('append') // 'append' | 'replace'
const chapterContent = ref('')
const isSaving = ref(false)

const workChapters = computed(() => {
  if (!targetWorkId.value || isCreatingNewWork.value) return []
  return props.chapters.filter(c => c.work_id === targetWorkId.value)
})

const wordCount = computed(() => {
  const txt = chapterContent.value || ''
  return txt.replace(/\s+/g, '').length
})

const guessTitleFromContent = (text, fallbackIndex) => {
  if (text) {
    const firstLine = text.trim().split('\n')[0].trim()
    const clean = firstLine.replace(/^#+\s*/, '').replace(/[*_`]/g, '').trim()
    if (clean && clean.length <= 35 && /^(第.{1,8}[章回节卷]|序幕|楔子|尾声)/.test(clean)) {
      return clean
    }
  }
  return `第 ${fallbackIndex} 章`
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return

    chapterContent.value = props.initialContent || ''
    actionMode.value = 'create'
    appendMethod.value = 'append'
    newWorkTitle.value = ''
    newWorkGenre.value = '科幻小说'

    if (props.works.length === 0) {
      isCreatingNewWork.value = true
      targetWorkId.value = ''
      chapterTitle.value = guessTitleFromContent(props.initialContent, 1)
    } else {
      isCreatingNewWork.value = false
      const preferredWork =
        (props.defaultWorkId && props.works.find(w => w.id === props.defaultWorkId)) ||
        props.works[0]
      targetWorkId.value = preferredWork.id
      const existingCount = props.chapters.filter(c => c.work_id === preferredWork.id).length
      chapterTitle.value = guessTitleFromContent(props.initialContent, existingCount + 1)
      const firstChap = props.chapters.find(c => c.work_id === preferredWork.id)
      targetChapterId.value = firstChap ? firstChap.id : ''
    }
  }
)

watch(targetWorkId, (newWorkId) => {
  if (!newWorkId || isCreatingNewWork.value) return
  const list = props.chapters.filter(c => c.work_id === newWorkId)
  if (actionMode.value === 'create' && (!chapterTitle.value || /^第\s*\d+\s*章$/.test(chapterTitle.value))) {
    chapterTitle.value = guessTitleFromContent(chapterContent.value, list.length + 1)
  }
  if (list.length > 0) {
    targetChapterId.value = list[0].id
  } else {
    targetChapterId.value = ''
    if (actionMode.value === 'append') {
      actionMode.value = 'create'
    }
  }
})

const toggleNewWorkMode = () => {
  isCreatingNewWork.value = !isCreatingNewWork.value
  if (isCreatingNewWork.value) {
    actionMode.value = 'create'
  }
}

const handleClose = () => {
  emit('update:modelValue', false)
}

const handleSubmit = async () => {
  if (!chapterContent.value.trim()) {
    ElMessage.warning('请填写要添加的章节内容')
    return
  }

  let resolvedWorkId = targetWorkId.value
  let resolvedWorkTitle = ''

  if (isCreatingNewWork.value) {
    if (!newWorkTitle.value.trim()) {
      ElMessage.warning('请输入新作品名称')
      return
    }
  } else if (!resolvedWorkId) {
    ElMessage.warning('请选择目标作品，或新建一个作品')
    return
  }

  if (actionMode.value === 'create' && !chapterTitle.value.trim()) {
    ElMessage.warning('请输入章节名称')
    return
  }

  if (actionMode.value === 'append' && !targetChapterId.value) {
    ElMessage.warning('请选择要追加的目标章节')
    return
  }

  isSaving.value = true
  try {
    // 1. 如需新建作品，先创建作品
    if (isCreatingNewWork.value) {
      const workRes = await api.createWork({
        title: newWorkTitle.value.trim(),
        genre: newWorkGenre.value,
        summary: '',
        outline: '',
        target_words: 50000
      })
      resolvedWorkId = workRes.work.id
      resolvedWorkTitle = workRes.work.title
    } else {
      const w = props.works.find(item => item.id === resolvedWorkId)
      resolvedWorkTitle = w ? w.title : ''
    }

    // 2. 创建新章节或追加到已有章节
    let savedChapter = null
    if (actionMode.value === 'create' || isCreatingNewWork.value) {
      const res = await api.createChapter(resolvedWorkId, {
        title: chapterTitle.value.trim(),
        content: chapterContent.value,
        source_session_id: props.sourceSessionId || null
      })
      savedChapter = res.chapter
      ElMessage.success(`已成功添加到《${resolvedWorkTitle}》· ${savedChapter.title}`)
    } else {
      const payload =
        appendMethod.value === 'append'
          ? { append_content: chapterContent.value }
          : { content: chapterContent.value }
      const res = await api.updateChapter(targetChapterId.value, payload)
      savedChapter = res.chapter
      ElMessage.success(
        appendMethod.value === 'append'
          ? `已追加内容到《${resolvedWorkTitle}》· ${savedChapter.title}`
          : `已更新《${resolvedWorkTitle}》· ${savedChapter.title}`
      )
    }

    emit('saved', { workId: resolvedWorkId, chapter: savedChapter })
    emit('update:modelValue', false)
  } catch (err) {
    ElMessage.error('添加到章节失败: ' + (err.message || '网络错误'))
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="640px"
    class="add-chapter-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="flex items-center gap-2">
        <el-icon class="text-blue-400"><Notebook /></el-icon>
        <span class="dialog-title-text">添加内容到作品章节</span>
        <el-tag size="small" type="info" effect="plain">
          约 {{ wordCount.toLocaleString() }} 字
        </el-tag>
      </div>
    </template>

    <div class="chapter-modal-body">
      <!-- 1. 选择目标作品或快速新建作品 -->
      <div class="form-field">
        <div class="field-header">
          <label class="field-label">目标作品 <span class="text-red-400">*</span></label>
          <el-button
            v-if="works.length > 0"
            link
            type="primary"
            size="small"
            :icon="Plus"
            @click="toggleNewWorkMode"
          >
            {{ isCreatingNewWork ? '选择已有作品' : '快速新建作品' }}
          </el-button>
        </div>

        <div v-if="!isCreatingNewWork && works.length > 0">
          <el-select
            v-model="targetWorkId"
            placeholder="请选择要存入的作品"
            class="w-full"
          >
            <el-option
              v-for="w in works"
              :key="w.id"
              :label="`《${w.title}》${w.genre ? ' · ' + w.genre : ''}`"
              :value="w.id"
            />
          </el-select>
        </div>

        <div v-else class="new-work-inline">
          <el-input
            v-model="newWorkTitle"
            placeholder="请输入新作品名称（如：星海纪元）"
            maxlength="40"
            show-word-limit
            class="flex-1"
          />
          <el-select v-model="newWorkGenre" class="genre-select">
            <el-option v-for="g in genreOptions" :key="g" :label="g" :value="g" />
          </el-select>
        </div>
      </div>

      <!-- 2. 选择新建章节还是追加到已有章节 -->
      <div v-if="!isCreatingNewWork && workChapters.length > 0" class="form-field">
        <label class="field-label">添加方式</label>
        <div class="mode-switch-row">
          <button
            type="button"
            class="mode-pill"
            :class="{ active: actionMode === 'create' }"
            @click="actionMode = 'create'"
          >
            ✨ 新建章节
          </button>
          <button
            type="button"
            class="mode-pill"
            :class="{ active: actionMode === 'append' }"
            @click="actionMode = 'append'"
          >
            ➕ 追加到已有章节 ({{ workChapters.length }})
          </button>
        </div>
      </div>

      <!-- 3A. 新建章节名称 -->
      <div v-if="actionMode === 'create' || isCreatingNewWork" class="form-field">
        <label class="field-label">章节名称 <span class="text-red-400">*</span></label>
        <el-input
          v-model="chapterTitle"
          placeholder="例如：第一章 初入星海"
          maxlength="60"
          show-word-limit
        />
      </div>

      <!-- 3B. 选择已有章节及追加方式 -->
      <div v-else class="form-row-two">
        <div class="form-field flex-1">
          <label class="field-label">选择已有章节 <span class="text-red-400">*</span></label>
          <el-select v-model="targetChapterId" placeholder="请选择章节" class="w-full">
            <el-option
              v-for="ch in workChapters"
              :key="ch.id"
              :label="`${ch.title} (${(ch.word_count || 0).toLocaleString()} 字)`"
              :value="ch.id"
            />
          </el-select>
        </div>

        <div class="form-field method-select">
          <label class="field-label">写入方式</label>
          <el-select v-model="appendMethod" class="w-full">
            <el-option label="追加到末尾" value="append" />
            <el-option label="覆盖原内容" value="replace" />
          </el-select>
        </div>
      </div>

      <!-- 4. 章节内容（可自由编辑裁剪） -->
      <div class="form-field">
        <div class="field-header">
          <label class="field-label">章节内容 <span class="text-red-400">*</span></label>
          <span class="field-hint">可直接删改、润色后再保存</span>
        </div>
        <el-input
          v-model="chapterContent"
          type="textarea"
          :rows="11"
          placeholder="在这里编辑要存入章节的正文内容..."
          class="chapter-content-textarea"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="isSaving" @click="handleSubmit">
          确认添加到章节
        </el-button>
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

.chapter-modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row-two {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.method-select {
  width: 150px;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.new-work-inline {
  display: flex;
  gap: 10px;
  align-items: center;
}

.genre-select {
  width: 140px;
}

.mode-switch-row {
  display: flex;
  gap: 8px;
}

.mode-pill {
  flex: 1;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-pill:hover {
  color: var(--text-primary);
}

.mode-pill.active {
  background: var(--reasoning-bg);
  border-color: var(--accent-color, #3b82f6);
  color: var(--text-primary);
  font-weight: 500;
}

.chapter-content-textarea :deep(.el-textarea__inner) {
  font-size: 13.5px;
  line-height: 1.7;
}
</style>

