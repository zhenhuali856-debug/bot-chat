<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import {
  ElContainer,
  ElMain,
  ElAlert,
  ElButton,
  ElMessage,
  ElMessageBox,
  ElNotification,
  RefreshRight
} from '../plugins/element'
import * as api from '../api'
import AppSidebar from '../components/AppSidebar.vue'
import CreativeModeBar from '../components/CreativeModeBar.vue'
import WordProgressBar from '../components/WordProgressBar.vue'
import { useAuthStore } from '../stores/auth'

import AppHeader from '../components/AppHeader.vue'
import ChatMessageItem from '../components/ChatMessageItem.vue'
import ChatInput from '../components/ChatInput.vue'
import PromptFileModal from '../components/PromptFileModal.vue'
import AddToChapterModal from '../components/AddToChapterModal.vue'
import ChapterEditorModal from '../components/ChapterEditorModal.vue'
import LocalSyncModal from '../components/LocalSyncModal.vue'
import CharacterPanel from '../components/CharacterPanel.vue'
import MaterialPanel from '../components/MaterialPanel.vue'
import BookExportModal from '../components/BookExportModal.vue'
import OutlineSplitModal from '../components/OutlineSplitModal.vue'
import ChapterVersionModal from '../components/ChapterVersionModal.vue'
import InsightDrawer from '../components/InsightDrawer.vue'


// ==========================================
// 响应式状态定义
// ==========================================
const works = ref([])
const chapters = ref([])
const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const selectedModel = ref('deepseek-chat')
const availableModels = ref([])
const hasApiKey = ref(true)
const isSidebarOpen = ref(true)
const messagesContainer = ref(null)
const sidebarRef = ref(null)

// 洞察抽屉状态 (合一工作台 · 迭代 1)
const insightDrawerVisible = ref(false)
const insightLoading = ref(false)
const insightError = ref(null)
const insightData = ref({
  trend: { points: [], total_words: 0 },
  overview: null
})

const loadInsightData = async () => {
  insightLoading.value = true
  insightError.value = null
  try {
    const [trendRes, overviewRes] = await Promise.all([
      api.getStatsTrend('day', 'mine'),
      api.getStatsOverview('mine')
    ])
    insightData.value = {
      trend: trendRes?.data || trendRes || { points: [], total_words: 0 },
      overview: overviewRes?.data || overviewRes || null
    }
  } catch (err) {
    console.error('加载创作洞察数据异常:', err)
    insightError.value = err?.message || '数据暂时不可用'
  } finally {
    insightLoading.value = false
  }
}

// 当前会话所绑定的作品 (M1 创作工作台核心计算属性)
const currentWork = computed(() => {
  const cur = sessions.value.find(s => s.id === currentSessionId.value)
  if (!cur || !cur.work_id) return null
  return works.value.find(w => w.id === cur.work_id) || null
})

const handleEditWorkTarget = () => {
  if (currentWork.value && sidebarRef.value?.openEditWorkDialog) {
    sidebarRef.value.openEditWorkDialog(currentWork.value)
  }
}

// 动态创作建议胶囊 (根据当前作品体裁或通用创作生成)
const currentSuggestions = computed(() => {
  if (currentWork.value) {
    const genre = currentWork.value.genre || ''
    if (genre.includes('科幻')) {
      return [
        '帮我写一个外星信号的开篇',
        '为女主角设计人物小传',
        '梳理三方势力的关系'
      ]
    }
    if (genre.includes('悬疑') || genre.includes('推理')) {
      return [
        '构思一个密室作案的诡计核心',
        '为侦探设计一个性格反差与弱点',
        '梳理开篇发现第一起线索的场景'
      ]
    }
    if (genre.includes('仙侠') || genre.includes('奇幻')) {
      return [
        '设计修仙门派的世界观与力量境界体系',
        '构思开篇废柴觉醒或禁地遇险的剧情',
        '为反派势力设计行事动机与底牌'
      ]
    }
    return [
      `构思一部《${currentWork.value.title}》的精彩开篇钩子`,
      '为主要角色设计详细人物小传与动机',
      '梳理主线故事的冲突高潮与节奏大纲'
    ]
  }
  return [
    '帮我想一个极具悬念感的故事核心设定',
    '如何把日常对话写出潜台词和张力',
    '为长篇故事梳理起承转合的大纲脉络'
  ]
})

// 当前选中的模型展示名称
const currentSelectedModelName = computed(() => {
  const m = availableModels.value.find(item => item.id === selectedModel.value)
  return m ? m.name : selectedModel.value
})

const handleQuickPrompt = (promptText) => {
  if (isLoading.value || !promptText) return
  inputMessage.value = promptText
  sendMessage()
}

// 全局助手昵称与人设 (M0 创作教练)
const botNickname = ref('灵感兔')
const botPersona = ref('')
const isSavingBotSettings = ref(false)
const showCreativeBar = ref(true)
const prevChapterInfo = ref(null)
const isCreativeModeAutoSave = ref(false)

const handleSelectPrevChapter = async (targetChapterId) => {
  if (!currentSessionId.value) return
  try {
    const data = await api.updateSession(currentSessionId.value, {
      target_chapter_id: targetChapterId
    })
    prevChapterInfo.value = data.prev_chapter || null
    if (targetChapterId === 'none') {
      ElMessage.info('已设为不承接前情，本章将作为独立情节展开')
    } else {
      const selectedCh = prevChapterInfo.value?.available_chapters?.find(c => c.id === targetChapterId)
      ElMessage.success(`已切换承接章节为：《${selectedCh?.title || prevChapterInfo.value?.title}》`)
    }
  } catch (err) {
    ElMessage.error('切换承接章节失败: ' + (err.message || '网络错误'))
  }
}

// Markdown 提示词文件状态 (.md Prompt Files)
const promptFiles = ref([])
const isPromptModalVisible = ref(false)
const activePreviewPromptFile = ref(null)

// 添加到章节 & 章节正文编辑弹窗状态
const isAddToChapterVisible = ref(false)
const addToChapterInitialContent = ref('')
const addToChapterDefaultWorkId = ref(null)
const isChapterEditorVisible = ref(false)
const activeChapter = ref(null)

// 本地目录同步状态
const syncSettings = ref({})
const isLocalSyncModalVisible = ref(false)

// M2 角色卡与素材库弹窗状态
const isCharPanelVisible = ref(false)
const isMaterialPanelVisible = ref(false)
const activePanelWork = ref(null)

const openCharacterPanel = (work) => {
  const targetWork = typeof work === 'object' ? work : works.value.find(w => w.id === work)
  if (!targetWork) return
  activePanelWork.value = targetWork
  isCharPanelVisible.value = true
}

const openMaterialPanel = (work) => {
  const targetWork = typeof work === 'object' ? work : works.value.find(w => w.id === work)
  if (!targetWork) return
  activePanelWork.value = targetWork
  isMaterialPanelVisible.value = true
}

const handleInsertMaterialToChat = (content) => {
  if (!content) return
  inputMessage.value = inputMessage.value
    ? `${inputMessage.value}\n${content}`
    : content
}

// M3 创作专用功能弹窗状态（整书导出 / AI 拆章 / 章节版本对比）
const isExportBookModalVisible = ref(false)
const activeExportWork = ref(null)
const isSplitOutlineModalVisible = ref(false)
const activeSplitWork = ref(null)
const activeSplitOutlineOverride = ref(null)
const isChapterVersionModalVisible = ref(false)
const activeVersionChapter = ref(null)

const openExportBookModal = (work = null) => {
  const target =
    (work && typeof work === 'object' ? work : works.value.find(w => w.id === work)) ||
    currentWork.value ||
    works.value[0] ||
    null
  if (!target) {
    ElMessage.warning('请先创建或选择一个作品')
    return
  }
  activeExportWork.value = target
  isExportBookModalVisible.value = true
}

const openSplitOutlineModal = (payload = null) => {
  let targetWork = null
  let outlineOverride = null
  if (payload && payload.work) {
    targetWork = payload.work
    outlineOverride = payload.outlineOverride ?? null
  } else if (payload && typeof payload === 'object') {
    targetWork = payload
  } else {
    targetWork = currentWork.value || works.value[0] || null
  }
  if (!targetWork) {
    ElMessage.warning('请先创建或选择一个作品')
    return
  }
  activeSplitWork.value = targetWork
  activeSplitOutlineOverride.value = outlineOverride
  isSplitOutlineModalVisible.value = true
}

const openChapterVersionModal = (chapter) => {
  if (!chapter) return
  activeVersionChapter.value = chapter
  isChapterVersionModalVisible.value = true
}

// 对话文件导入
const importFileInput = ref(null)

let abortController = null

// ==========================================
// 工具辅助函数
// ==========================================
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      const el = messagesContainer.value.$el || messagesContainer.value
      el.scrollTop = el.scrollHeight
    }
  })
}

const getCurrentSessionTitle = () => {
  const current = sessions.value.find(s => s.id === currentSessionId.value)
  return current ? current.title : '对话记录'
}

const downloadFile = (content, filename, mimeType) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ==========================================
// 系统信息与助手配置
// ==========================================
const loadHealth = async () => {
  try {
    const data = await api.checkHealth()
    hasApiKey.value = data.has_api_key
    if (data.default_model) {
      selectedModel.value = data.default_model
    }
  } catch (err) {
    console.error('Failed to check backend health:', err)
    hasApiKey.value = false
  }
}

const loadModels = async () => {
  try {
    const data = await api.getModels()
    availableModels.value = data.models || []
    if (availableModels.value.length > 0 && !availableModels.value.some(m => m.id === selectedModel.value)) {
      selectedModel.value = availableModels.value[0].id
    }
  } catch (err) {
    console.error('Failed to load models:', err)
  }
}

const loadBotSettings = async () => {
  try {
    const settings = await api.getBotSettings()
    if (settings) {
      if (settings.bot_nickname) botNickname.value = settings.bot_nickname
      if (settings.bot_persona) botPersona.value = settings.bot_persona
    }
  } catch (err) {
    console.error('Failed to load bot settings:', err)
  }
}

const handleSaveBotSettings = async () => {
  isSavingBotSettings.value = true
  try {
    await api.updateBotSettings({
      bot_nickname: botNickname.value.trim() || '灵感兔',
      bot_persona: botPersona.value.trim()
    })
    ElMessage.success('创作教练设置已成功更新并生效！')
  } catch (err) {
    ElMessage.error('保存设置失败: ' + (err.message || '网络错误'))
  } finally {
    isSavingBotSettings.value = false
  }
}

// ==========================================
// 作品与章节管理 (M1 创作工作台核心调度)
// ==========================================
const fetchWorks = async () => {
  try {
    const data = await api.listWorks()
    works.value = data.works || []
  } catch (err) {
    console.error('Failed to fetch works:', err)
  }
}

const fetchChapters = async () => {
  try {
    const data = await api.listChapters()
    chapters.value = data.chapters || []
  } catch (err) {
    console.error('Failed to fetch chapters:', err)
  }
}

const handleRefreshWorksAndChapters = async () => {
  await Promise.all([fetchWorks(), fetchChapters()])
  if (currentSessionId.value) {
    try {
      const data = await api.getSessionMessages(currentSessionId.value)
      prevChapterInfo.value = data.prev_chapter || null
    } catch {
      // ignore
    }
  }
}

const openAddToChapterModal = (msg) => {
  addToChapterInitialContent.value = msg?.content || ''
  addToChapterDefaultWorkId.value = currentWork.value ? currentWork.value.id : null
  isAddToChapterVisible.value = true
}

const openAddChapterForWork = (workId) => {
  addToChapterInitialContent.value = ''
  addToChapterDefaultWorkId.value = workId || null
  isAddToChapterVisible.value = true
}

const handleChapterAdded = async () => {
  await handleRefreshWorksAndChapters()
}

const openChapterEditor = (chapter) => {
  activeChapter.value = chapter
  isChapterEditorVisible.value = true
}

const handleUpdateChapter = async (chapterId, payload) => {
  try {
    await api.updateChapter(chapterId, payload)
    await handleRefreshWorksAndChapters()
    ElMessage.success('章节内容已保存！')
  } catch (err) {
    ElMessage.error('保存章节失败: ' + (err.message || '网络错误'))
  }
}

const handleDeleteChapter = async (chapterOrId, skipConfirm = false) => {
  const chapterId = typeof chapterOrId === 'string' ? chapterOrId : chapterOrId.id
  const chapterTitle = typeof chapterOrId === 'string' ? '' : chapterOrId.title
  if (!skipConfirm) {
    try {
      await ElMessageBox.confirm(
        `确定要删除章节${chapterTitle ? `《${chapterTitle}》` : ''}吗？此操作不可恢复。`,
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
  }
  try {
    await api.deleteChapter(chapterId)
    await handleRefreshWorksAndChapters()
    ElMessage.success('章节已删除')
  } catch (err) {
    ElMessage.error('删除章节失败: ' + (err.message || '网络错误'))
  }
}

const fetchSessions = async (autoSelectFirst = false) => {
  try {
    const data = await api.getSessions()
    sessions.value = data.sessions || []

    if (autoSelectFirst) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id)
      } else {
        await createNewSession()
      }
    }
  } catch (err) {
    console.error('Failed to fetch sessions:', err)
  }
}

const selectSession = async (sessionId) => {
  if (currentSessionId.value === sessionId && messages.value.length > 0) return
  currentSessionId.value = sessionId

  try {
    const data = await api.getSessionMessages(sessionId)
    prevChapterInfo.value = data.prev_chapter || null
    const dbMessages = (data.messages || []).map(m => ({
      id: m.id,
      role: m.role,
      content: m.content,
      reasoning: m.reasoning_content || '',
      showReasoning: false
    }))

    if (dbMessages.length === 1 && dbMessages[0].role === 'assistant' && dbMessages[0].content.startsWith('你好！我是')) {
      messages.value = []
    } else {
      messages.value = dbMessages
    }
    scrollToBottom()
    await fetchPromptFiles()
  } catch (err) {
    console.error('Failed to load session messages:', err)
  }
}

const createNewSession = async (workId = null) => {
  try {
    const work = workId ? works.value.find(w => w.id === workId) : null
    const defaultTitle = work ? '新章节' : '新建对话'
    const data = await api.createSession({ title: defaultTitle, work_id: workId })
    const newSession = data.session
    prevChapterInfo.value = data.prev_chapter || null
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id

    const welcomeMsg = work
      ? `你好！我是你的创作教练 ${botNickname.value}。已为你开启作品《${work.title}》的全新创作章节，让我们开始构思吧！`
      : `你好！我是你的创作教练 ${botNickname.value}，新会话已创建。本会话的所有多轮记忆都会在服务端独立保存，刷新页面不丢失！`

    messages.value = [
      {
        role: 'assistant',
        content: welcomeMsg,
        reasoning: '',
        showReasoning: false
      }
    ]
    scrollToBottom()
    await fetchWorks()
    await fetchPromptFiles()
  } catch (err) {
    console.error('Failed to create session:', err)
  }
}

const deleteSession = async (sessionId, e) => {
  if (e && e.stopPropagation) e.stopPropagation()
  try {
    await ElMessageBox.confirm('确定要删除此会话及其所有历史记忆吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    await api.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    ElMessage.success('会话已删除')
    await fetchWorks()
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id)
      } else {
        await createNewSession()
      }
    }
  } catch (err) {
    ElMessage.error('删除会话失败: ' + (err.message || '网络错误'))
  }
}

const clearCurrentSession = async () => {
  if (!currentSessionId.value) return

  try {
    await ElMessageBox.confirm(
      '确定要清空当前会话的全部消息记忆吗？（此操作不可恢复）',
      '清空记忆提示',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  try {
    await api.clearSession(currentSessionId.value)
    messages.value = []
    ElMessage.success('当前会话记忆已清空')
    fetchSessions(false)
  } catch (err) {
    ElMessage.error('清空失败: ' + (err.message || '网络错误'))
  }
}

// ==========================================
// 对话导入与导出
// ==========================================
const handleExportCommand = (command) => {
  if (command === 'export-book') {
    openExportBookModal(currentWork.value || works.value[0])
  } else if (command === 'markdown') {
    handleExportMarkdown()
  } else if (command === 'json') {
    handleExportJson()
  } else if (command === 'all') {
    handleExportAll()
  }
}

const handleExportMarkdown = async () => {
  if (!currentSessionId.value) {
    ElMessage.warning('请先选择一个会话')
    return
  }
  if (messages.value.length === 0 || (messages.value.length === 1 && messages.value[0].role === 'assistant' && !messages.value[0].reasoning)) {
    ElMessage.warning('当前会话暂无聊天内容可导出')
    return
  }

  try {
    const mdText = await api.exportSessionMarkdown(currentSessionId.value)
    const title = getCurrentSessionTitle()
    const nowStr = new Date().toISOString().slice(0, 10)
    downloadFile(mdText, `${title}_${nowStr}.md`, 'text/markdown;charset=utf-8')
    ElMessage.success('已导出为 Markdown 文件！')
  } catch (err) {
    ElMessage.error('导出 Markdown 失败: ' + (err.message || '网络错误'))
  }
}

const handleExportJson = async () => {
  if (!currentSessionId.value) {
    ElMessage.warning('请先选择一个会话')
    return
  }
  if (messages.value.length === 0 || (messages.value.length === 1 && messages.value[0].role === 'assistant' && !messages.value[0].reasoning)) {
    ElMessage.warning('当前会话暂无聊天内容可导出')
    return
  }

  try {
    const data = await api.exportSessionJson(currentSessionId.value)
    const title = getCurrentSessionTitle()
    const nowStr = new Date().toISOString().slice(0, 10)
    downloadFile(JSON.stringify(data, null, 2), `${title}_${nowStr}.json`, 'application/json;charset=utf-8')
    ElMessage.success('已导出为 JSON 数据文件！')
  } catch (err) {
    ElMessage.error('导出 JSON 失败: ' + (err.message || '网络错误'))
  }
}

const handleExportAll = async () => {
  try {
    const data = await api.exportAllSessions()
    const nowStr = new Date().toISOString().slice(0, 10)
    downloadFile(
      JSON.stringify(data, null, 2),
      `rabbit_chat_all_backup_${nowStr}.json`,
      'application/json;charset=utf-8'
    )
    ElMessage.success(`全量备份已导出（共 ${data.total_sessions || 0} 个会话）！`)
  } catch (err) {
    ElMessage.error('导出全量备份失败: ' + (err.message || '网络错误'))
  }
}

const triggerImportFile = () => {
  if (importFileInput.value) {
    importFileInput.value.value = ''
    importFileInput.value.click()
  }
}

const onImportFileSelected = async (event) => {
  const file = event.target.files && event.target.files[0]
  if (!file) return

  const fileName = file.name
  const isJson = fileName.toLowerCase().endsWith('.json')
  const isMarkdown = fileName.toLowerCase().endsWith('.md') || fileName.toLowerCase().endsWith('.txt')

  if (!isJson && !isMarkdown) {
    ElMessage.warning('仅支持导入 .json 或 .md / .txt 格式的对话记录')
    return
  }

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const rawText = e.target.result
      if (isJson) {
        const parsed = JSON.parse(rawText)
        if (parsed.sessions && Array.isArray(parsed.sessions)) {
          let count = 0
          for (const s of parsed.sessions) {
            await api.importSession(s)
            count++
          }
          await fetchSessions(true)
          ElMessage.success(`成功导入全量备份中的 ${count} 个会话！`)
        } else {
          const res = await api.importSession(parsed)
          await fetchSessions(false)
          if (res.session && res.session.id) {
            await selectSession(res.session.id)
          }
          ElMessage.success(`已成功导入会话 “${res.session.title}”！`)
        }
      } else if (isMarkdown) {
        const defaultTitle = fileName.replace(/\.[^/.]+$/, '')
        const res = await api.importSession({
          format: 'markdown',
          title: defaultTitle,
          markdown_content: rawText
        })
        await fetchSessions(false)
        ElMessage.success(`已导入 Markdown 对话 “${res.session.title}”（共 ${res.message_count} 条消息）！`)
        if (res.session && res.session.id) {
          await selectSession(res.session.id)
        }
      }
    } catch (err) {
      ElMessage.error('导入失败：' + (err.message || '格式错误'))
    } finally {
      if (importFileInput.value) {
        importFileInput.value.value = ''
      }
    }
  }
  reader.readAsText(file, 'utf-8')
}

// ==========================================
// Markdown 提示词文件管理 (.md Prompt Files)
// ==========================================
const fetchPromptFiles = async () => {
  try {
    const curSession = sessions.value.find(s => s.id === currentSessionId.value)
    const data = await api.listPromptFiles({
      session_id: currentSessionId.value || undefined,
      work_id: curSession?.work_id || undefined
    })
    promptFiles.value = data.prompt_files || []
  } catch (err) {
    console.error('Failed to fetch prompt files:', err)
  }
}

const handleUploadPromptFiles = async (parsedFiles) => {
  if (!currentSessionId.value) {
    await createNewSession()
  }

  let successCount = 0
  const names = []
  for (const item of parsedFiles) {
    try {
      await api.createPromptFile({
        filename: item.filename,
        content: item.content,
        scope: 'session',
        session_id: currentSessionId.value,
        enabled: true
      })
      successCount++
      names.push(`《${item.filename}》`)
    } catch (err) {
      ElMessage.error(`上传《${item.filename}》失败: ` + (err.message || '网络错误'))
    }
  }

  if (successCount > 0) {
    await fetchPromptFiles()
    ElMessage.success(`已读取并挂载提示词 ${names.join('、')}，模型将在对话中自动读取遵循！`)
  }
}

const openPromptFileModal = (file) => {
  activePreviewPromptFile.value = file
  isPromptModalVisible.value = true
}

const handleTogglePromptFile = async (file) => {
  try {
    const nextEnabled = !file.enabled
    await api.updatePromptFile(file.id, { enabled: nextEnabled })
    await fetchPromptFiles()
    ElMessage.success(nextEnabled ? `已启用提示词《${file.filename}》` : `已暂停注入《${file.filename}》`)
  } catch (err) {
    ElMessage.error('切换提示词状态失败: ' + (err.message || '网络错误'))
  }
}

const handleUpdatePromptFile = async (fileId, payload) => {
  try {
    await api.updatePromptFile(fileId, payload)
    await fetchPromptFiles()
    ElMessage.success('Markdown 提示词已更新并生效！')
  } catch (err) {
    ElMessage.error('保存提示词失败: ' + (err.message || '网络错误'))
  }
}

const handleDeletePromptFile = async (file) => {
  try {
    await api.deletePromptFile(file.id)
    await fetchPromptFiles()
    ElMessage.success(`已移除提示词《${file.filename}》`)
  } catch (err) {
    ElMessage.error('移除提示词失败: ' + (err.message || '网络错误'))
  }
}

const handleRunWithPrompts = () => {
  if (isLoading.value) return
  inputMessage.value = '请完整读取我上传的 Markdown 提示词文件，并严格按其中的设定和指令开始执行回复。'
  sendMessage()
}

const handleStartCreativeMode = () => {
  if (isLoading.value || !hasApiKey.value) return
  const custom = inputMessage.value.trim()
  let promptText = ''
  if (custom) {
    promptText = `【小说正文创作模式】：${custom}\n\n请以专业网络小说作家的叙事节奏、细腻文笔与镜头感，严格承接上一章剧情与作品设定，正式开始撰写本章节的完整正文！`
  } else if (promptFiles.value.some(f => f.enabled)) {
    promptText = '请完整读取并严格遵循我挂载的 Markdown 提示词文件，结合上一章的剧情承接与作品设定，以沉浸式的小说笔触，正式开始创作撰写本章节的完整正文！'
  } else if (prevChapterInfo.value && prevChapterInfo.value.title && prevChapterInfo.value.id !== 'none') {
    promptText = `请紧密衔接上一章《${prevChapterInfo.value.title}》结尾的情节动作与未解悬念，延续全书风格基调，正式开始撰写下一章节的精彩正文！`
  } else if (currentWork.value) {
    promptText = `请在作品《${currentWork.value.title}》的世界观与故事大纲基调下，开始构思并正式撰写全新章节的正文内容！`
  } else {
    promptText = '请以富有文学张力与生动画面感的小说笔触，开始构思并撰写本章节的完整正文。'
  }
  inputMessage.value = promptText
  isCreativeModeAutoSave.value = true
  sendMessage()
}

const autoSaveToChapter = async (fullText, msgIndex) => {
  if (!currentWork.value || !fullText) return
  try {
    // 1. 智能提取或推算章节标题
    const existingWorkChapters = chapters.value.filter(c => c.work_id === currentWork.value.id)
    const fallbackNum = existingWorkChapters.length + 1

    const toCnNum = (n) => {
      const cnNums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
      if (n <= 10) return cnNums[n]
      if (n < 20) return '十' + cnNums[n % 10]
      if (n < 100) return cnNums[Math.floor(n / 10)] + '十' + (n % 10 > 0 ? cnNums[n % 10] : '')
      return String(n)
    }

    let parsedTitle = ''
    const lines = fullText.split('\n')
    for (let i = 0; i < Math.min(lines.length, 6); i++) {
      const line = lines[i].trim()
      if (!line) continue
      const clean = line.replace(/^[#>\s*`_]+/, '').replace(/[*`_]/g, '').trim()
      if (/^(第\s*[\d零一二三四五六七八九十百千万]+\s*[章回节卷]|序幕|楔子|尾声|引子|番外)/.test(clean)) {
        if (clean.length <= 40) {
          parsedTitle = clean
          break
        }
      }
    }

    if (!parsedTitle) {
      parsedTitle = `第${toCnNum(fallbackNum)}章`
    }

    // 2. 检查是否存在由「AI 一键拆章」预建的同名或同序号未写占位章节，若存在则直接写入该占位章，避免重复创建
    const isPlaceholderChapter = (ch) => {
      const c = (ch.content || '').trim()
      return !c || c.startsWith('【本章规划要点】')
    }
    const extractChapterPrefix = (t) => {
      const m = (t || '').trim().match(/^(第\s*[\d零一二三四五六七八九十百千万]+\s*[章回节场])/)
      return m ? m[1].replace(/\s+/g, '') : ''
    }
    const targetPrefix = extractChapterPrefix(parsedTitle)
    const matchedPlaceholder = existingWorkChapters.find(ch => {
      if (!isPlaceholderChapter(ch)) return false
      if ((ch.title || '').trim() === parsedTitle) return true
      const chPrefix = extractChapterPrefix(ch.title)
      return Boolean(targetPrefix && chPrefix && targetPrefix === chPrefix)
    })

    let savedChapter = null
    if (matchedPlaceholder) {
      const res = await api.updateChapter(matchedPlaceholder.id, {
        title: parsedTitle,
        content: fullText,
        source_session_id: currentSessionId.value || null
      })
      savedChapter = res.chapter
    } else {
      const res = await api.createChapter(currentWork.value.id, {
        title: parsedTitle,
        content: fullText,
        source_session_id: currentSessionId.value || null
      })
      savedChapter = res.chapter
    }

    // 3. 关联消息标记
    if (messages.value[msgIndex]) {
      messages.value[msgIndex].savedChapterTitle = savedChapter.title
      messages.value[msgIndex].savedWorkTitle = currentWork.value.title
    }

    // 4. 刷新作品与章节列表，左侧侧边栏立即呈现新章节
    await handleRefreshWorksAndChapters()
    await syncCurrentMessages()

    const words = savedChapter.word_count || fullText.replace(/\s+/g, '').length
    ElNotification.success({
      title: '创作模式 · 已自动存入章节',
      message: `已自动为《${currentWork.value.title}》创建《${savedChapter.title}》（${words} 字），并同步至左侧章节树！`,
      duration: 5000
    })

    // 5. 自动清空本会话已使用的挂载提示词（方案 A），避免下一章重复残留
    if (promptFiles.value.length > 0) {
      for (const pf of promptFiles.value) {
        if (pf.scope === 'session') {
          api.deletePromptFile(pf.id).catch(() => {})
        }
      }
      await fetchPromptFiles()
    }
  } catch (err) {
    console.error('创作模式自动入库章节失败:', err)
    ElMessage.warning('正文已生成，但自动存入章节失败: ' + (err.message || '网络错误'))
  }
}

// ==========================================
// 消息发送与流式响应 (SSE)
// ==========================================
const syncCurrentMessages = async () => {
  if (!currentSessionId.value) return
  try {
    const data = await api.getSessionMessages(currentSessionId.value)
    prevChapterInfo.value = data.prev_chapter || null
    messages.value = (data.messages || []).map(m => ({
      id: m.id,
      role: m.role,
      content: m.content,
      reasoning: m.reasoning_content || '',
      showReasoning: false
    }))
  } catch (err) {
    console.error('Failed to sync messages:', err)
  }
}

const sendMessage = async () => {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value) return

  if (!currentSessionId.value) {
    await createNewSession()
  }

  messages.value.push({
    role: 'user',
    content: content
  })

  inputMessage.value = ''
  isLoading.value = true
  scrollToBottom()

  const assistantMsgIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    reasoning: '',
    showReasoning: true
  })

  abortController = new AbortController()

  try {
    const res = await api.sendChatStream(
      {
        session_id: currentSessionId.value,
        message: content,
        model: selectedModel.value,
        stream: true
      },
      abortController.signal
    )

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP 错误: ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue

        const dataStr = trimmed.slice(6)
        if (dataStr === '[DONE]') break

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.session_id) {
            currentSessionId.value = parsed.session_id
          }
          if (parsed.error) {
            messages.value[assistantMsgIndex].content += `\n\n> ⚠️ **错误**: ${parsed.error}`
          }
          if (parsed.reasoning_content) {
            messages.value[assistantMsgIndex].reasoning += parsed.reasoning_content
          }
          if (parsed.content) {
            messages.value[assistantMsgIndex].content += parsed.content
          }
          scrollToBottom()
        } catch (e) {
          console.error('Failed to parse SSE chunk:', dataStr, e)
        }
      }
    }

    fetchSessions(false)
    await syncCurrentMessages()

    // 🌟 核心：如果是创作模式触发的生成，自动将该生成内容创建并存入作品章节列表！
    if (isCreativeModeAutoSave.value) {
      isCreativeModeAutoSave.value = false
      const fullText = messages.value[assistantMsgIndex]?.content || ''
      if (fullText.trim().length >= 30 && currentWork.value) {
        await autoSaveToChapter(fullText.trim(), assistantMsgIndex)
      }
    }

  } catch (err) {
    if (err.name !== 'AbortError') {
      messages.value[assistantMsgIndex].content += `\n\n> ⚠️ **异常**: ${err.message}`
    }
  } finally {
    isCreativeModeAutoSave.value = false
    isLoading.value = false
    abortController = null
    scrollToBottom()
  }
}

const stopGeneration = () => {
  if (abortController) {
    abortController.abort()
  }
}

// ==========================================
// 消息级操作：复制 / 重新生成 / 删除单条
// ==========================================
const copyMessage = async (msg) => {
  const textToCopy = msg.content || msg.reasoning || ''
  if (!textToCopy) {
    ElMessage.warning('该消息内容为空')
    return
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(textToCopy)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = textToCopy
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      textArea.style.top = '-9999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
    }
    ElMessage.success('已复制到剪贴板！')
  } catch (err) {
    console.error('复制失败:', err)
    ElMessage.error('复制失败，请手动选取复制')
  }
}

const handleDeleteMessage = async (msg, index) => {
  try {
    await ElMessageBox.confirm('确定要删除此条消息吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    if (msg.id && currentSessionId.value) {
      await api.deleteMessage(currentSessionId.value, msg.id, false)
    }
    messages.value.splice(index, 1)
    ElMessage.success('消息已删除')
    fetchSessions(false)
  } catch (err) {
    console.error('删除消息失败:', err)
    ElMessage.error('删除消息失败: ' + (err.message || '网络错误'))
  }
}

const regenerateMessage = async (msg, index) => {
  if (isLoading.value) {
    ElMessage.warning('AI 正在回复中，请稍候或先停止生成')
    return
  }

  let userMsgIndex = -1
  for (let i = index - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      userMsgIndex = i
      break
    }
  }

  if (userMsgIndex === -1) {
    ElMessage.warning('未找到对应的前置用户提问，无法重新生成')
    return
  }

  const userPrompt = messages.value[userMsgIndex].content
  const isLastMessage = index === messages.value.length - 1

  if (!isLastMessage) {
    try {
      await ElMessageBox.confirm(
        '重新生成该轮回答将截断并清除其后续的所有对话记录，确定继续吗？',
        '重新生成提示',
        {
          confirmButtonText: '确定重新生成',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  if (msg.id && currentSessionId.value) {
    try {
      await api.deleteMessage(currentSessionId.value, msg.id, !isLastMessage)
    } catch (err) {
      console.error('Failed to clean previous message in DB:', err)
    }
  }

  if (!isLastMessage) {
    messages.value = messages.value.slice(0, index + 1)
  }

  const targetIndex = index
  if (messages.value[targetIndex]) {
    messages.value[targetIndex].content = ''
    messages.value[targetIndex].reasoning = ''
    messages.value[targetIndex].showReasoning = true
  } else {
    messages.value.push({
      role: 'assistant',
      content: '',
      reasoning: '',
      showReasoning: true
    })
  }
  
  isLoading.value = true
  abortController = new AbortController()

  try {
    const res = await api.sendChatStream(
      {
        session_id: currentSessionId.value,
        message: userPrompt,
        model: selectedModel.value,
        stream: true,
        regenerate: true
      },
      abortController.signal
    )

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP 错误: ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue

        const dataStr = trimmed.slice(6)
        if (dataStr === '[DONE]') break

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.session_id) {
            currentSessionId.value = parsed.session_id
          }
          if (parsed.error) {
            messages.value[targetIndex].content += `\n\n> ⚠️ **错误**: ${parsed.error}`
          }
          if (parsed.reasoning_content) {
            messages.value[targetIndex].reasoning += parsed.reasoning_content
          }
          if (parsed.content) {
            messages.value[targetIndex].content += parsed.content
          }
          scrollToBottom()
        } catch (e) {
          console.error('Failed to parse SSE chunk:', dataStr, e)
        }
      }
    }

    fetchSessions(false)
    await syncCurrentMessages()

  } catch (err) {
    if (err.name !== 'AbortError') {
      messages.value[targetIndex].content += `\n\n> ⚠️ **异常**: ${err.message}`
    }
  } finally {
    isLoading.value = false
    abortController = null
    scrollToBottom()
  }
}

const fetchSyncSettings = async () => {
  try {
    syncSettings.value = await api.getSyncSettings()
  } catch (err) {
    console.error('Failed to fetch sync settings:', err)
  }
}


const { authVersion, authInitialized, isLoginVisible } = useAuthStore()

const loadWorkspaceData = async () => {
  if (isLoginVisible.value) return
  currentSessionId.value = null
  messages.value = []
  loadHealth()
  loadModels()
  loadBotSettings()
  fetchSyncSettings()
  await handleRefreshWorksAndChapters()
  await fetchSessions(true)
  loadInsightData()
}

watch(authVersion, () => {
  if (!isLoginVisible.value) {
    loadWorkspaceData()
  }
})

onMounted(() => {
  if (authInitialized.value && !isLoginVisible.value) {
    loadWorkspaceData()
  }
})
</script>

<template>
  <el-container class="chat-app" :class="{ 'insight-open': insightDrawerVisible }">
    <!-- 左侧可折叠会话侧边栏组件 -->
    <AppSidebar
      ref="sidebarRef"
      :is-open="isSidebarOpen"
      :works="works"
      :chapters="chapters"
      :sessions="sessions"
      :current-session-id="currentSessionId"
      :bot-nickname="botNickname"
      :bot-persona="botPersona"
      :is-saving-bot-settings="isSavingBotSettings"
      :sync-settings="syncSettings"
      @new-session="createNewSession"
      @select-session="selectSession"
      @delete-session="deleteSession"
      @import-file="triggerImportFile"
      @save-bot-settings="handleSaveBotSettings"
      @update:bot-nickname="botNickname = $event"
      @update:bot-persona="botPersona = $event"
      @refresh-works="handleRefreshWorksAndChapters"
      @refresh-sessions="fetchSessions(false)"
      @open-add-chapter="openAddChapterForWork"
      @open-chapter="openChapterEditor"
      @delete-chapter="handleDeleteChapter"
      @open-sync-modal="isLocalSyncModalVisible = true"
      @open-characters="openCharacterPanel"
      @open-materials="openMaterialPanel"
      @open-export-book="openExportBookModal"
      @open-split-outline="openSplitOutlineModal"
      @open-chapter-versions="openChapterVersionModal"
    />

    <!-- 右侧主工作区容器 -->
    <el-container class="chat-main">
      <!-- 顶部状态导航栏组件 -->
      <AppHeader
        :is-sidebar-open="isSidebarOpen"
        :bot-nickname="botNickname"
        :selected-model="selectedModel"
        :available-models="availableModels"
        :has-api-key="hasApiKey"
        :disabled-clear="messages.length === 0"
        @toggle-sidebar="isSidebarOpen = !isSidebarOpen"
        @open-insight="insightDrawerVisible = !insightDrawerVisible"
        @update:selected-model="selectedModel = $event"
        @import-file="triggerImportFile"
        @export-command="handleExportCommand"
        @clear-session="clearCurrentSession"
      />

      <!-- API Key 警告条 -->
      <el-alert
        v-if="!hasApiKey"
        title="尚未在 backend/.env 中检测到有效 API Key"
        type="warning"
        show-icon
        :closable="false"
        class="warning-banner"
      >
        <template #default>
          <div class="flex items-center justify-between w-full">
            <span>请在后端 .env 中配置 DEEPSEEK_API_KEY、ZHIPU_API_KEY 或 GEMINI_API_KEY 以便正常调用模型服务。</span>
            <el-button size="small" type="warning" plain :icon="RefreshRight" @click="loadHealth">
              刷新检测
            </el-button>
          </div>
        </template>
      </el-alert>

      <!-- 模块 5 · 创作模式提示条（独立复用组件） -->
      <CreativeModeBar
        v-if="currentWork && showCreativeBar"
        :work="currentWork"
        :prev-chapter-info="prevChapterInfo"
        @select-prev-chapter="handleSelectPrevChapter"
        @open-characters="openCharacterPanel"
        @open-materials="openMaterialPanel"
        @open-split-outline="openSplitOutlineModal"
        @open-export-book="openExportBookModal"
      />

      <!-- M4c · 字数进度看板（独立复用组件） -->
      <WordProgressBar
        v-if="currentWork && showCreativeBar"
        :work="currentWork"
        :chapters="chapters"
        @edit-target="handleEditWorkTarget"
      />

      <!-- 消息列表滚动视图 -->
      <el-main class="chat-window" ref="messagesContainer">
        <div class="messages-list">
          <!-- 欢迎语 (模块 6 / 原型) -->
          <div class="welcome">
            <div class="wm-logo">🐇</div>
            <div class="wm-content">
              <h2>你好，我是{{ botNickname || '灵感兔' }}</h2>
              <p>你的 AI 创作教练。告诉我你想创作的故事、角色或大纲，我们一起把灵感变成作品。{{ currentWork ? `当前正在创作《${currentWork.title}》· ${currentWork.genre || '故事'}。` : '' }}</p>
              <div class="chips">
                <span
                  v-for="sug in currentSuggestions"
                  :key="sug"
                  class="chip"
                  @click="handleQuickPrompt(sug)"
                >
                  {{ sug }}
                </span>
              </div>
            </div>
          </div>

          <ChatMessageItem
            v-for="(msg, index) in messages"
            :key="msg.id || index"
            :msg="msg"
            :index="index"
            :is-loading="isLoading"
            :is-last="index === messages.length - 1"
            @copy="copyMessage"
            @regenerate="regenerateMessage"
            @delete="handleDeleteMessage"
            @add-to-chapter="openAddToChapterModal"
          />
        </div>
      </el-main>

      <!-- 底部输入栏组件 -->
      <ChatInput
        v-model="inputMessage"
        :is-loading="isLoading"
        :has-api-key="hasApiKey"
        :selected-model="selectedModel"
        :prompt-files="promptFiles"
        :show-creative-bar="showCreativeBar"
        @send="sendMessage"
        @stop="stopGeneration"
        @upload-prompt-files="handleUploadPromptFiles"
        @preview-prompt-file="openPromptFileModal"
        @toggle-prompt-file="handleTogglePromptFile"
        @delete-prompt-file="handleDeletePromptFile"
        @run-with-prompts="handleRunWithPrompts"
        @quick-prompt="handleQuickPrompt"
        @start-creative-mode="handleStartCreativeMode"
        @toggle-creative-bar="showCreativeBar = !showCreativeBar"
      />

      <!-- 页面底部原型状态栏 (对照需求文档与原型) -->
      <footer class="app-bottom-bar">
        <span>灵感兔 · 创作工作台 UI 原型 ｜ 原 8 模块 + M2 角色卡/素材库 + M3 整书导出/体裁模板/AI拆章/版本对比</span>
        <span class="bottom-model-badge">{{ currentSelectedModelName }}</span>
      </footer>
    </el-container>

    <!-- M2a · 角色管理弹窗 -->
    <CharacterPanel
      v-model="isCharPanelVisible"
      :work-id="activePanelWork?.id"
      :work-title="activePanelWork?.title"
    />

    <!-- M2b · 素材库弹窗 -->
    <MaterialPanel
      v-model="isMaterialPanelVisible"
      :work-id="activePanelWork?.id"
      :work-title="activePanelWork?.title"
      @insert-to-chat="handleInsertMaterialToChat"
    />

    <!-- M3a-1 · 整书单文件导出弹窗 -->
    <BookExportModal
      v-model="isExportBookModalVisible"
      :work="activeExportWork"
      :chapters="chapters"
    />

    <!-- M3b · AI 一键拆章审核弹窗 -->
    <OutlineSplitModal
      v-model="isSplitOutlineModalVisible"
      :work="activeSplitWork"
      :outline-override="activeSplitOutlineOverride"
      :selected-model="selectedModel"
      @created="handleRefreshWorksAndChapters"
    />

    <!-- M3c · 章节版本历史与并排对比弹窗 -->
    <ChapterVersionModal
      v-model="isChapterVersionModalVisible"
      :chapter="activeVersionChapter"
    />

    <!-- Markdown 提示词文件读取与编辑弹窗 -->
    <PromptFileModal
      v-model="isPromptModalVisible"
      :file="activePreviewPromptFile"
      :current-work="currentWork"
      :current-session-id="currentSessionId"
      @save="handleUpdatePromptFile"
      @delete="handleDeletePromptFile"
    />

    <!-- 将对话生成内容添加到作品章节弹窗 -->
    <AddToChapterModal
      v-model="isAddToChapterVisible"
      :works="works"
      :chapters="chapters"
      :initial-content="addToChapterInitialContent"
      :default-work-id="addToChapterDefaultWorkId"
      :source-session-id="currentSessionId"
      @saved="handleChapterAdded"
    />

    <!-- 作品正文章节阅读与编辑弹窗 -->
    <ChapterEditorModal
      v-model="isChapterEditorVisible"
      :chapter="activeChapter"
      :work-title="works.find(w => w.id === activeChapter?.work_id)?.title || ''"
      @save="handleUpdateChapter"
      @delete="(id) => handleDeleteChapter(id, true)"
      @open-versions="openChapterVersionModal"
    />

    <!-- 本地电脑目录同步设置弹窗 -->
    <LocalSyncModal
      v-model="isLocalSyncModalVisible"
      :works="works"
      @synced="syncSettings = $event"
    />

    <!-- 隐藏的文件选择器：导入对话 -->
    <input
      type="file"
      ref="importFileInput"
      style="display: none"
      accept=".json,.md,.txt"
      @change="onImportFileSelected"
    />

    <!-- 创作洞察抽屉 (合一工作台 · 迭代 1) -->
    <InsightDrawer
      v-model="insightDrawerVisible"
      :work="currentWork"
      :chapters="chapters"
      :trend="insightData.trend"
      :overview="insightData.overview"
      :loading="insightLoading"
      :error="insightError"
      @refresh="loadInsightData"
    />
  </el-container>
</template>

<style scoped>
.chat-app {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
  position: relative;
  background-color: var(--bg-primary);
  --drawer-w: 360px;
}

@media (max-width: 1120px) {
  .chat-app {
    --drawer-w: 32vw;
  }
}

@media (max-width: 900px) {
  .chat-app {
    --drawer-w: min(360px, 86vw);
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
  background-color: var(--bg-primary);
  transition: margin-right 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

@media (min-width: 901px) {
  .chat-app.insight-open .chat-main {
    margin-right: var(--drawer-w);
  }
}

.warning-banner {
  border-radius: 0;
}

/* ---------- 欢迎语 (模块 6 / 原型) ---------- */
.welcome {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 6px 0;
}

.welcome .wm-logo {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex: none;
}

.welcome .wm-content {
  flex: 1;
}

.welcome h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.welcome p {
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.chip {
  font-size: 12px;
  padding: 7px 12px;
  border-radius: 9px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.chip:hover {
  color: var(--accent-color, #3b82f6);
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.08);
}

/* 底部状态条 (原型与文档) */
.app-bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 16px;
  background-color: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
  user-select: none;
  flex-shrink: 0;
}

.bottom-model-badge {
  font-size: 10px;
  color: #818cf8;
  padding: 1px 6px;
  background: rgba(99, 102, 241, 0.12);
  border-radius: 4px;
  font-weight: 500;
}

.chat-window {
  flex: 1;
  padding: 24px 16px;
  display: flex;
  justify-content: center;
  overflow-y: auto;
}

.messages-list {
  width: 100%;
  max-width: 840px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>

