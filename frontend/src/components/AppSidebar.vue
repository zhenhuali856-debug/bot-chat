<script setup>
import { ref, computed, watch } from 'vue'
import {
  Plus,
  Upload,
  Search,
  ChatDotRound,
  Delete,
  UserFilled,
  CloseBold,
  Check,
  ArrowRight,
  ArrowDown,
  Setting,
  Edit,
  Reading,
  Document,
  FolderOpened,
  ElDialog,
  ElMessage,
  ElMessageBox
} from '../plugins/element'
import * as api from '../api'
import { formatCharCount } from '../utils/fileReader'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: true
  },
  works: {
    type: Array,
    default: () => []
  },
  chapters: {
    type: Array,
    default: () => []
  },
  sessions: {
    type: Array,
    default: () => []
  },
  currentSessionId: {
    type: String,
    default: null
  },
  botNickname: {
    type: String,
    default: '灵感兔'
  },
  botPersona: {
    type: String,
    default: ''
  },
  isSavingBotSettings: {
    type: Boolean,
    default: false
  },
  syncSettings: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'new-session',
  'select-session',
  'delete-session',
  'import-file',
  'save-bot-settings',
  'update:botNickname',
  'update:botPersona',
  'refresh-works',
  'refresh-sessions',
  'open-add-chapter',
  'open-chapter',
  'delete-chapter',
  'open-sync-modal'
])

// 搜索状态管理
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
let searchTimer = null

// 作品展开折叠状态 (默认展开所有有章节的作品)
const expandedWorks = ref(new Set())
const isUncategorizedExpanded = ref(true)

// 监听 works 列表，初始化时默认展开全部作品
watch(
  () => props.works,
  (newWorks) => {
    if (newWorks && newWorks.length > 0) {
      newWorks.forEach(w => expandedWorks.value.add(w.id))
    }
  },
  { immediate: true }
)

// 当切换当前会话时，确保所在作品处于展开态
watch(
  () => props.currentSessionId,
  (newSid) => {
    if (!newSid) return
    const curSession = props.sessions.find(s => s.id === newSid)
    if (curSession && curSession.work_id) {
      expandedWorks.value.add(curSession.work_id)
    }
  }
)

const toggleWorkExpand = (workId) => {
  if (expandedWorks.value.has(workId)) {
    expandedWorks.value.delete(workId)
  } else {
    expandedWorks.value.add(workId)
  }
}

// 分组计算：每个作品下的正文章节列表
const chaptersByWork = computed(() => {
  const map = {}
  props.works.forEach(w => {
    map[w.id] = []
  })
  props.chapters.forEach(ch => {
    if (ch.work_id && map[ch.work_id]) {
      map[ch.work_id].push(ch)
    }
  })
  return map
})

// 分组计算：每个作品下的创作对话列表
const sessionsByWork = computed(() => {
  const map = {}
  props.works.forEach(w => {
    map[w.id] = []
  })
  props.sessions.forEach(s => {
    if (s.work_id && map[s.work_id]) {
      map[s.work_id].push(s)
    }
  })
  return map
})

// 未归类章节 (旧数据或独立会话)
const uncategorizedSessions = computed(() => {
  return props.sessions.filter(s => !s.work_id || !props.works.some(w => w.id === s.work_id))
})

// ==========================================
// 搜索功能
// ==========================================
const onSearchInput = (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  const trimmed = (val || '').trim()
  if (!trimmed) {
    searchResults.value = []
    isSearching.value = false
    return
  }

  isSearching.value = true
  searchTimer = setTimeout(async () => {
    try {
      const data = await api.searchHistory(trimmed)
      searchResults.value = data.results || []
    } catch (err) {
      console.error('Search failed:', err)
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 300)
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  isSearching.value = false
  if (searchTimer) clearTimeout(searchTimer)
}

const highlightKeyword = (text, keyword) => {
  if (!text || !keyword) return text || ''
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return text.replace(regex, '<mark class="search-keyword-highlight">$1</mark>')
}

// ==========================================
// 作品弹窗 (新建 / 编辑设定)
// ==========================================
const isWorkDialogVisible = ref(false)
const isSubmittingWork = ref(false)
const editingWorkId = ref(null)

const workForm = ref({
  title: '',
  genre: '科幻小说',
  summary: '',
  outline: '',
  target_words: 50000
})

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

const openCreateWorkDialog = () => {
  editingWorkId.value = null
  workForm.value = {
    title: '',
    genre: '科幻小说',
    summary: '',
    outline: '',
    target_words: 50000
  }
  isWorkDialogVisible.value = true
}

const openEditWorkDialog = (work) => {
  editingWorkId.value = work.id
  workForm.value = {
    title: work.title,
    genre: work.genre || '科幻小说',
    summary: work.summary || '',
    outline: work.outline || '',
    target_words: work.target_words || 50000
  }
  isWorkDialogVisible.value = true
}

const handleSaveWork = async () => {
  const title = workForm.value.title.trim()
  if (!title) {
    ElMessage.warning('请输入作品名称')
    return
  }

  isSubmittingWork.value = true
  try {
    if (editingWorkId.value) {
      // 更新作品
      await api.updateWork(editingWorkId.value, {
        title: title,
        genre: workForm.value.genre,
        summary: workForm.value.summary,
        outline: workForm.value.outline,
        target_words: Number(workForm.value.target_words) || 0
      })
      ElMessage.success(`作品《${title}》设定已更新！`)
    } else {
      // 新建作品
      const res = await api.createWork({
        title: title,
        genre: workForm.value.genre,
        summary: workForm.value.summary,
        outline: workForm.value.outline,
        target_words: Number(workForm.value.target_words) || 0
      })
      expandedWorks.value.add(res.work.id)
      ElMessage.success(`作品《${title}》已创建，开始创作第一章吧！`)
      // 自动在此作品下创建第一章
      emit('new-session', res.work.id)
    }
    isWorkDialogVisible.value = false
    emit('refresh-works')
  } catch (err) {
    ElMessage.error('保存作品失败: ' + (err.message || '网络错误'))
  } finally {
    isSubmittingWork.value = false
  }
}

const handleDeleteWork = async (work) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除作品《${work.title}》吗？\n删除后作品下保存的正文章节将被清理，关联的创作对话会自动移入「未归类灵感」。`,
      '删除作品提示',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  try {
    await api.deleteWork(work.id)
    expandedWorks.value.delete(work.id)
    ElMessage.success(`作品《${work.title}》已删除，相关对话已移入未归类`)
    emit('refresh-works')
    emit('refresh-sessions')
  } catch (err) {
    ElMessage.error('删除作品失败: ' + (err.message || '网络错误'))
  }
}
</script>

<template>
  <el-aside :width="isOpen ? '300px' : '0px'" class="sidebar-wrapper">
    <div class="sidebar" :class="{ collapsed: !isOpen }">
      <!-- 顶部操作区：新建作品 + 导入 + 搜索框 -->
      <div class="sidebar-header">
        <div class="flex items-center gap-2">
          <el-button
            type="primary"
            class="new-work-btn flex-1"
            :icon="Plus"
            @click="openCreateWorkDialog"
          >
            ＋ 新建作品
          </el-button>
          <el-tooltip content="导入对话/章节记录 (.json / .md)" placement="bottom">
            <el-button
              type="primary"
              plain
              class="sidebar-import-btn"
              :icon="Upload"
              @click="emit('import-file')"
            />
          </el-tooltip>
        </div>

        <!-- 搜索历史对话/章节关键词 -->
        <div class="sidebar-search-box mt-2.5">
          <el-input
            v-model="searchQuery"
            placeholder="搜索创作灵感、章节与对话..."
            size="small"
            clearable
            :prefix-icon="Search"
            class="history-search-input"
            @input="onSearchInput"
            @clear="clearSearch"
          />
        </div>
      </div>

      <!-- 核心树结构：作品 ▸ 章节两级树 -->
      <el-scrollbar class="sessions-list">
        <!-- 搜索结果展示模式 -->
        <template v-if="searchQuery.trim()">
          <div class="sessions-label flex items-center justify-between">
            <span>搜索结果 ({{ searchResults.length }})</span>
            <el-button link type="primary" size="small" class="clear-search-link" @click="clearSearch">
              返回作品树
            </el-button>
          </div>

          <div v-if="isSearching" class="py-6 text-center text-xs text-gray-400">
            正在搜索创作记录...
          </div>

          <template v-else-if="searchResults.length > 0">
            <div
              v-for="item in searchResults"
              :key="item.session_id"
              class="search-result-item"
              :class="{ active: item.session_id === currentSessionId }"
              @click="emit('select-session', item.session_id)"
            >
              <div class="search-result-header">
                <el-icon class="chat-bubble-icon"><ChatDotRound /></el-icon>
                <span class="search-result-title" v-html="highlightKeyword(item.session_title, searchQuery)"></span>
              </div>

              <!-- 匹配的消息片段 -->
              <div v-if="item.snippets && item.snippets.length > 0" class="search-snippets-list">
                <div
                  v-for="snp in item.snippets"
                  :key="snp.message_id"
                  class="snippet-item"
                >
                  <span class="snippet-role">{{ snp.role === 'user' ? '👤 提问:' : '🤖 回复:' }}</span>
                  <span class="snippet-text" v-html="highlightKeyword(snp.snippet, searchQuery)"></span>
                </div>
              </div>
            </div>
          </template>

          <el-empty
            v-else
            description="未找到相关创作记录"
            :image-size="45"
            class="py-6"
          />
        </template>

        <!-- 正常作品 ▸ 章节两级树模式 -->
        <template v-else>
          <!-- 作品分组 -->
          <div class="sessions-label flex items-center justify-between">
            <span>📚 我的作品 ({{ works.length }})</span>
            <el-tooltip
              :content="syncSettings?.sync_dir ? `同步目标: ${syncSettings.sync_dir}` : '设置本地电脑同步目录并导出作品章节'"
              placement="top"
            >
              <button
                type="button"
                class="sync-trigger-btn"
                :class="{ 'is-auto': syncSettings?.auto_sync }"
                @click="emit('open-sync-modal')"
              >
                <el-icon><FolderOpened /></el-icon>
                <span>{{ syncSettings?.auto_sync ? '已自动同步' : '同步本地' }}</span>
              </button>
            </el-tooltip>
          </div>

          <div v-if="works.length === 0" class="no-works-box">
            <div class="text-xs text-gray-400 mb-2">尚未创建作品，点击上方「新建作品」开始</div>
          </div>

          <div
            v-for="work in works"
            :key="work.id"
            class="work-node mb-2"
          >
            <!-- 作品卡片头 -->
            <div
              class="work-header"
              :class="{ 'is-expanded': expandedWorks.has(work.id) }"
              @click="toggleWorkExpand(work.id)"
            >
              <div class="work-header-left">
                <el-icon class="expand-arrow">
                  <ArrowDown v-if="expandedWorks.has(work.id)" />
                  <ArrowRight v-else />
                </el-icon>
                <span class="work-book-icon">📖</span>
                <span class="work-title" :title="work.title">《{{ work.title }}》</span>
                <span v-if="work.genre" class="work-genre-badge">{{ work.genre }}</span>
              </div>

              <!-- 悬停快捷按钮区 -->
              <div class="work-actions" @click.stop>
                <el-tooltip content="为此作品添加正文章节" placement="top">
                  <button class="work-action-btn" @click.stop="emit('open-add-chapter', work.id)">
                    <el-icon><Plus /></el-icon>
                    <span>章节</span>
                  </button>
                </el-tooltip>

                <el-tooltip content="编辑作品设定(大纲/体裁/简介)" placement="top">
                  <button class="work-action-btn" @click.stop="openEditWorkDialog(work)">
                    <el-icon><Setting /></el-icon>
                  </button>
                </el-tooltip>

                <el-tooltip content="删除作品(对话移回未归类)" placement="top">
                  <button class="work-action-btn delete" @click.stop="handleDeleteWork(work)">
                    <el-icon><Delete /></el-icon>
                  </button>
                </el-tooltip>
              </div>
            </div>

            <!-- 作品展开态：正文章节 + 创作对话 -->
            <div v-show="expandedWorks.has(work.id)" class="chapters-container">
              <!-- A. 作品正文章节 (通过弹窗写入的章节与正文内容) -->
              <div class="work-sub-header">
                <span>📄 作品章节 ({{ (chaptersByWork[work.id] || []).length }})</span>
                <button
                  type="button"
                  class="sub-add-btn"
                  @click.stop="emit('open-add-chapter', work.id)"
                >
                  ＋ 添加章节
                </button>
              </div>

              <div
                v-for="ch in chaptersByWork[work.id] || []"
                :key="ch.id"
                class="chapter-doc-item"
                @click="emit('open-chapter', ch)"
              >
                <el-icon class="chapter-doc-icon"><Document /></el-icon>
                <span class="chapter-title" :title="ch.title">{{ ch.title }}</span>
                <span class="chapter-word-badge">{{ formatCharCount(ch.word_count || 0) }}</span>
                <el-button
                  link
                  type="danger"
                  class="delete-btn"
                  :icon="Delete"
                  title="删除此正文章节"
                  @click.stop="emit('delete-chapter', ch)"
                />
              </div>

              <div
                v-if="!chaptersByWork[work.id] || chaptersByWork[work.id].length === 0"
                class="empty-chapters"
                @click="emit('open-add-chapter', work.id)"
              >
                <el-icon class="mr-1"><Plus /></el-icon> 添加章节或从对话存入
              </div>

              <!-- B. 作品关联创作对话 -->
              <div class="work-sub-header mt-1">
                <span>💬 创作对话 ({{ (sessionsByWork[work.id] || []).length }})</span>
                <button
                  type="button"
                  class="sub-add-btn"
                  @click.stop="emit('new-session', work.id)"
                >
                  ＋ 新对话
                </button>
              </div>

              <div
                v-for="s in sessionsByWork[work.id] || []"
                :key="s.id"
                class="chapter-item"
                :class="{ active: s.id === currentSessionId }"
                @click="emit('select-session', s.id)"
              >
                <el-icon class="chapter-bubble-icon"><ChatDotRound /></el-icon>
                <span class="chapter-title" :title="s.title">{{ s.title }}</span>
                <el-button
                  link
                  type="danger"
                  class="delete-btn"
                  :icon="Delete"
                  title="删除此对话"
                  @click.stop="emit('delete-session', s.id, $event)"
                />
              </div>

              <!-- 若作品下暂无对话 -->
              <div
                v-if="!sessionsByWork[work.id] || sessionsByWork[work.id].length === 0"
                class="empty-chapters"
                @click="emit('new-session', work.id)"
              >
                <el-icon class="mr-1"><Plus /></el-icon> 开启专属创作对话
              </div>
            </div>
          </div>

          <!-- 未归类分组 (向后兼容旧会话或未关联作品的会话) -->
          <div class="uncategorized-section mt-4">
            <div
              class="sessions-label flex items-center justify-between cursor-pointer"
              @click="isUncategorizedExpanded = !isUncategorizedExpanded"
            >
              <div class="flex items-center gap-1.5">
                <el-icon class="text-xs">
                  <ArrowDown v-if="isUncategorizedExpanded" />
                  <ArrowRight v-else />
                </el-icon>
                <span>🗂️ 未归类灵感 ({{ uncategorizedSessions.length }})</span>
              </div>
              <el-button
                link
                type="primary"
                size="small"
                class="new-single-btn"
                @click.stop="emit('new-session', null)"
              >
                ＋ 灵感
              </el-button>
            </div>

            <div v-show="isUncategorizedExpanded" class="uncategorized-list">
              <div
                v-for="s in uncategorizedSessions"
                :key="s.id"
                class="session-item"
                :class="{ active: s.id === currentSessionId }"
                @click="emit('select-session', s.id)"
              >
                <el-icon class="chat-bubble-icon"><ChatDotRound /></el-icon>
                <span class="session-title" :title="s.title">{{ s.title }}</span>
                <el-button
                  link
                  type="danger"
                  class="delete-btn"
                  :icon="Delete"
                  title="删除会话"
                  @click.stop="emit('delete-session', s.id, $event)"
                />
              </div>

              <div
                v-if="uncategorizedSessions.length === 0"
                class="text-xs text-gray-500 py-2 px-3 text-center"
              >
                无未归类会话
              </div>
            </div>
          </div>
        </template>
      </el-scrollbar>

      <!-- 创作教练全局人设配置区域 (M0) -->
      <div class="persona-panel">
        <div class="persona-panel-title">
          <el-icon><UserFilled /></el-icon>
          <span>创作教练全局人设</span>
        </div>

        <div class="persona-form">
          <el-input
            :model-value="botNickname"
            class="custom-textarea"
            clearable
            :clear-icon="CloseBold"
            placeholder="创作教练昵称 (如: 灵感兔)"
            size="small"
            @update:model-value="emit('update:botNickname', $event)"
          />

          <el-input
            :model-value="botPersona"
            type="textarea"
            :rows="3"
            class="custom-textarea mt-2"
            clearable
            :clear-icon="CloseBold"
            placeholder="创作教练人设 (所有对话均遵循此身份)"
            size="small"
            @update:model-value="emit('update:botPersona', $event)"
          />

          <div class="mt-2 flex justify-end">
            <el-button
              type="primary"
              size="small"
              plain
              :icon="Check"
              :loading="isSavingBotSettings"
              @click="emit('save-bot-settings')"
            >
              保存助手设置
            </el-button>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="memory-badge">
          <span class="pulse-dot"></span>
          <span>服务端记忆与创作人设已启用</span>
        </div>
      </div>
    </div>

    <!-- 作品创建与设定对话框 (M1 浮层) -->
    <el-dialog
      v-model="isWorkDialogVisible"
      :title="editingWorkId ? `《${workForm.title}》· 作品设定` : '＋ 新建创作作品'"
      width="520px"
      class="work-setting-dialog"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="work-dialog-body">
        <div class="form-group mb-3">
          <label class="form-label"><span class="text-red-400 mr-1">*</span>作品名称</label>
          <el-input
            v-model="workForm.title"
            placeholder="例如: 星海彼端 / 城市夜行 / 悬疑迷雾"
            maxlength="40"
            show-word-limit
          />
        </div>

        <div class="grid grid-cols-2 gap-3 mb-3">
          <div class="form-group">
            <label class="form-label">体裁类型</label>
            <el-select v-model="workForm.genre" class="w-full" placeholder="请选择体裁">
              <el-option
                v-for="item in genreOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </div>

          <div class="form-group">
            <label class="form-label">目标字数</label>
            <el-input
              v-model="workForm.target_words"
              type="number"
              placeholder="例如: 100000"
            />
          </div>
        </div>

        <div class="form-group mb-3">
          <label class="form-label">作品简介 / 世界观背景</label>
          <el-input
            v-model="workForm.summary"
            type="textarea"
            :rows="3"
            placeholder="简述故事核心矛盾、主要角色与核心设定（AI将以此作为创作背景约束）..."
          />
        </div>

        <div class="form-group mb-2">
          <label class="form-label">故事大纲 / 章节规划</label>
          <el-input
            v-model="workForm.outline"
            type="textarea"
            :rows="4"
            placeholder="例如:&#10;一、启航：末日之后幸存者乘星舰出发&#10;二、裂隙：跃迁遇到空间风暴&#10;三、抉择：能源告急面临分歧&#10;四、新家园：抵达未知类地行星"
          />
        </div>

        <div class="text-xs text-gray-400 mt-2">
          💡 说明：作品设定将作为创作背景自动注入给 AI，让其在整个作品的创作中保持连贯的声音与设定。
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isWorkDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="isSubmittingWork"
            @click="handleSaveWork"
          >
            保存作品设定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </el-aside>
</template>

<style scoped>
.sidebar-wrapper {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  background-color: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  position: relative;
  z-index: 20;
}

.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 300px;
  background-color: var(--bg-primary);
}

.sidebar.collapsed {
  display: none;
}

.sidebar-header {
  padding: 16px 12px 12px 12px;
  border-bottom: 1px solid var(--border-color);
}

.new-work-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  height: 38px;
  border-radius: 8px;
  transition: opacity 0.2s;
}

.new-work-btn:hover {
  opacity: 0.9;
}

.sidebar-import-btn {
  height: 38px;
  width: 38px;
  padding: 0;
  border-radius: 8px;
}

.sessions-list {
  flex: 1;
  padding: 10px 10px;
}

.sessions-label {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  padding: 8px 6px 6px 6px;
  letter-spacing: 0.04em;
}

.no-works-box {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  text-align: center;
  margin-bottom: 12px;
}

/* 作品卡片与两级树结构 */
.work-node {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.15s ease;
}

.work-node:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.work-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 10px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.03);
  transition: background-color 0.15s ease;
  user-select: none;
}

.work-header:hover {
  background: rgba(255, 255, 255, 0.07);
}

.work-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow: hidden;
}

.expand-arrow {
  font-size: 0.78rem;
  color: var(--text-muted);
  transition: transform 0.2s;
}

.work-book-icon {
  font-size: 1rem;
}

.work-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-genre-badge {
  font-size: 0.68rem;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.3);
  flex-shrink: 0;
}

.work-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.work-header:hover .work-actions {
  opacity: 1;
}

.work-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.work-action-btn:hover {
  color: #60a5fa;
  border-color: #60a5fa;
  background: rgba(59, 130, 246, 0.15);
}

.work-action-btn.delete:hover {
  color: #ef4444;
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
}

/* 章节列表 */
.chapters-container {
  padding: 6px 6px 8px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.work-sub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.72rem;
  color: var(--text-muted);
  padding: 2px 6px;
}

.sub-add-btn {
  border: none;
  background: transparent;
  color: #60a5fa;
  font-size: 0.72rem;
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 4px;
}

.sub-add-btn:hover {
  background: rgba(59, 130, 246, 0.14);
}

.sync-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid rgba(59, 130, 246, 0.35);
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
  font-size: 0.7rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sync-trigger-btn:hover {
  background: rgba(59, 130, 246, 0.2);
}

.sync-trigger-btn.is-auto {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.chapter-doc-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 0.82rem;
  transition: all 0.15s ease;
}

.chapter-doc-item:hover {
  background-color: rgba(16, 185, 129, 0.12);
}

.chapter-doc-item:hover .delete-btn {
  opacity: 1;
}

.chapter-doc-icon {
  color: #10b981;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.chapter-word-badge {
  font-size: 0.68rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.82rem;
  transition: all 0.15s ease;
}

.chapter-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.chapter-item.active {
  background-color: rgba(59, 130, 246, 0.18);
  color: #60a5fa;
  font-weight: 500;
}

.chapter-bubble-icon {
  font-size: 0.85rem;
  opacity: 0.7;
}

.chapter-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-chapters {
  font-size: 0.75rem;
  color: var(--accent-color);
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  opacity: 0.85;
}

.empty-chapters:hover {
  opacity: 1;
  text-decoration: underline;
}

/* 未归类 */
.uncategorized-section {
  border-top: 1px dashed var(--border-color);
  padding-top: 8px;
}

.uncategorized-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

.new-single-btn {
  font-size: 0.72rem !important;
  padding: 0 !important;
  color: #818cf8 !important;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.84rem;
  transition: all 0.15s ease;
}

.session-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.session-item.active {
  background-color: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  font-weight: 500;
}

.chat-bubble-icon {
  font-size: 0.95rem;
  opacity: 0.7;
}

.session-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  opacity: 0;
  padding: 2px 4px;
  transition: opacity 0.2s;
}

.chapter-item:hover .delete-btn,
.session-item:hover .delete-btn {
  opacity: 1;
}

/* 历史搜索框与结果卡片样式 */
.history-search-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  box-shadow: none !important;
  border-radius: 6px;
  color: var(--text-primary);
}

.history-search-input :deep(.el-input__inner) {
  color: var(--text-primary);
  font-size: 0.8rem;
}

.history-search-input :deep(.el-input__wrapper:focus-within) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.3) !important;
}

.search-result-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 6px;
  transition: all 0.15s ease;
}

.search-result-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(59, 130, 246, 0.3);
}

.search-result-item.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
}

.search-result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.84rem;
  font-weight: 500;
  color: var(--text-primary);
}

.search-result-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-snippets-list {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snippet-item {
  font-size: 0.72rem;
  line-height: 1.4;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.25);
  padding: 4px 6px;
  border-radius: 4px;
  word-break: break-all;
}

.snippet-role {
  color: #94a3b8;
  font-weight: 500;
  margin-right: 4px;
}

:deep(.search-keyword-highlight) {
  background: rgba(234, 179, 8, 0.3) !important;
  color: #fde047 !important;
  font-weight: 600;
  padding: 0 2px;
  border-radius: 2px;
}

.clear-search-link {
  font-size: 0.72rem !important;
  padding: 0 !important;
  color: #60a5fa !important;
}

/* 全局人设面板样式 (M0 创作教练) */
.persona-panel {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.015);
}

.persona-panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #818cf8;
  margin-bottom: 8px;
}

.persona-form :deep(.el-input__wrapper),
.persona-form :deep(.el-textarea__inner) {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
  color: var(--text-primary) !important;
  border-radius: 6px;
}

.persona-form :deep(.el-textarea__inner) {
  font-size: 0.8rem;
  line-height: 1.4;
  padding: 6px 8px;
}

.persona-form :deep(.el-input__wrapper:focus-within),
.persona-form :deep(.el-textarea__inner:focus) {
  border-color: #6366f1 !important;
}

.sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.2);
}

.memory-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  color: #10b981;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #10b981;
  box-shadow: 0 0 8px #10b981;
}

/* 作品设定弹窗表单样式 */
.form-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}
</style>
