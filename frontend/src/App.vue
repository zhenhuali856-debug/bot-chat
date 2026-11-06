<script setup>
import { ref, onMounted, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import {
  Plus,
  ChatDotRound,
  Delete,
  Fold,
  Expand,
  VideoPause,
  Position,
  RefreshRight,
  CircleCheckFilled,
  CircleCloseFilled,
  ArrowRight,
  ArrowDown,
  CloseBold,
  Check,
  UserFilled,
  Download,
  Upload,
  Document,
  Files,
  Search,
  CopyDocument,
  ElMessage,
  ElMessageBox,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElTooltip
} from './plugins/element'
import * as api from './api'

// Markdown 解析器
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><div class="code-header"><span class="lang-tag">${lang}</span></div><code>${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`
      } catch (__) {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  }
})

// 状态定义
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
let abortController = null

// 历史记录搜索状态与方法
const searchQuery = ref('')
const isSearching = ref(false)
const searchResults = ref([])
let searchTimer = null

const onSearchInput = () => {
  if (searchTimer) clearTimeout(searchTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    isSearching.value = false
    return
  }

  isSearching.value = true
  searchTimer = setTimeout(async () => {
    try {
      const data = await api.searchHistory(q)
      searchResults.value = data.results || []
    } catch (err) {
      console.error('Failed to search history:', err)
    } finally {
      isSearching.value = false
    }
  }, 250)
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  isSearching.value = false
}

const highlightKeyword = (text, keyword) => {
  if (!text || !keyword) return text || ''
  const escaped = keyword.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  if (!escaped) return text
  const regex = new RegExp(`(${escaped})`, 'gi')
  return String(text).replace(regex, '<mark class="search-keyword-highlight">$1</mark>')
}

// 开发助手全局设定（应用到整个助手）
const botNickname = ref('Rabbit AI')
const botPersona = ref('你是由 DeepSeek 驱动的高级全栈开发助手，擅长分析、架构与编写高质量代码，回答准确专业、富有逻辑。')
const isSavingBotSettings = ref(false)

const loadBotSettings = async () => {
  try {
    const data = await api.getBotSettings()
    if (data.bot_nickname) {
      botNickname.value = data.bot_nickname
    }
    if (data.bot_persona) {
      botPersona.value = data.bot_persona
    }
  } catch (err) {
    console.warn('Failed to load bot settings:', err)
  }
}

const handleSaveBotSettings = async () => {
  if (!botNickname.value.trim()) {
    ElMessage.warning('助手昵称不能为空')
    return
  }
  isSavingBotSettings.value = true
  try {
    await api.updateBotSettings({
      bot_nickname: botNickname.value.trim(),
      bot_persona: botPersona.value.trim()
    })
    ElMessage.success('开发助手昵称与人设已全局更新！')
  } catch (err) {
    ElMessage.error(err.message || '保存设置失败')
  } finally {
    isSavingBotSettings.value = false
  }
}

const loadHealth = async () => {
  try {
    const data = await api.checkHealth()
    hasApiKey.value = data.has_api_key
    if (data.default_model) {
      selectedModel.value = data.default_model
    }
  } catch (err) {
    console.warn('Backend not reachable:', err)
    hasApiKey.value = false
  }
}

const loadModels = async () => {
  try {
    const data = await api.getModels()
    availableModels.value = data.models || []
  } catch (err) {
    availableModels.value = [
      { id: 'deepseek-chat', name: 'DeepSeek V3 (通用对话)' },
      { id: 'deepseek-reasoner', name: 'DeepSeek R1 (深度思考)' },
      { id: 'glm-4-flash', name: '智谱 GLM-4-Flash (免费开源/极速)' }
    ]
  }
}

// ==========================================
// 会话记忆管理逻辑
// ==========================================

const fetchSessions = async (autoSelectLatest = true) => {
  try {
    const data = await api.getSessions()
    sessions.value = data.sessions || []

    if (autoSelectLatest) {
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
    const dbMessages = (data.messages || []).map(m => ({
      id: m.id,
      role: m.role,
      content: m.content,
      reasoning: m.reasoning_content || '',
      showReasoning: false
    }))

    if (dbMessages.length === 0) {
      messages.value = [
        {
          role: 'assistant',
          content: `你好！我是 ${botNickname.value}。已为你开启新的会话记忆，请随时提问！`,
          reasoning: '',
          showReasoning: false
        }
      ]
    } else {
      messages.value = dbMessages
    }
    scrollToBottom()
  } catch (err) {
    console.error('Failed to load session messages:', err)
  }
}

const createNewSession = async () => {
  try {
    const data = await api.createSession({ title: '新建对话' })
    const newSession = data.session
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
    messages.value = [
      {
        role: 'assistant',
        content: `你好！我是 ${botNickname.value}，新会话已创建。本会话的所有多轮记忆都会在服务端独立保存，刷新页面不丢失！`,
        reasoning: '',
        showReasoning: false
      }
    ]
    scrollToBottom()
  } catch (err) {
    console.error('Failed to create session:', err)
  }
}

const deleteSession = async (sessionId, e) => {
  e.stopPropagation()
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
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id)
      } else {
        await createNewSession()
      }
    }
  } catch (err) {
    ElMessage.error('删除会话失败')
    console.error('Failed to delete session:', err)
  }
}

const clearCurrentSession = async () => {
  if (!currentSessionId.value) return
  try {
    await ElMessageBox.confirm('确定清空当前会话的记忆吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    await api.clearSession(currentSessionId.value)
    messages.value = [
      {
        role: 'assistant',
        content: '当前会话的上下文记忆已清空，我们可以开始新的话题。',
        reasoning: '',
        showReasoning: false
      }
    ]
    ElMessage.success('已清空当前会话记忆')
    await fetchSessions(false)
  } catch (err) {
    ElMessage.error('清空会话失败')
    console.error('Failed to clear session:', err)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// ==========================================
// 对话导出与导入逻辑 (Markdown & JSON)
// ==========================================
const importFileInput = ref(null)

const downloadFile = (content, filename, mimeType = 'text/plain;charset=utf-8') => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const getCurrentSessionTitle = () => {
  const current = sessions.value.find(s => s.id === currentSessionId.value)
  return current ? current.title.replace(/[\\/:*?"<>|]/g, '_').slice(0, 30) : 'rabbit_chat'
}

const handleExportCommand = async (command) => {
  if (command === 'all') {
    await handleExportAll()
  } else if (command === 'markdown') {
    await handleExportMarkdown()
  } else if (command === 'json') {
    await handleExportJson()
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
          return
        }

        const res = await api.importSession(parsed)
        if (res && res.success) {
          ElMessage.success(`成功导入对话：【${res.session.title}】(${res.message_count} 条消息)`)
          await fetchSessions(false)
          await selectSession(res.session.id)
        }
      } else {
        const defaultTitle = fileName.replace(/\.(md|txt)$/i, '')
        const res = await api.importSession({
          format: 'markdown',
          markdown_content: rawText,
          title: defaultTitle
        })
        if (res && res.success) {
          ElMessage.success(`成功导入 Markdown 对话：【${res.session.title}】(${res.message_count} 条消息)`)
          await fetchSessions(false)
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
// 消息发送与流式响应 (SSE)
// ==========================================

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

  } catch (err) {
    if (err.name !== 'AbortError') {
      messages.value[assistantMsgIndex].content += `\n\n> ⚠️ **异常**: ${err.message}`
    }
  } finally {
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

const syncCurrentMessages = async () => {
  if (!currentSessionId.value) return
  try {
    const data = await api.getSessionMessages(currentSessionId.value)
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

// ==========================================
// 消息级操作：复制 / 重新生成 / 删除单条
// ==========================================

// 1. 复制消息内容
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

// 2. 删除单条消息
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
    if (messages.value.length === 0) {
      messages.value = [
        {
          role: 'assistant',
          content: `你好！我是 ${botNickname.value}。已为你开启新的会话记忆，请随时提问！`,
          reasoning: '',
          showReasoning: false
        }
      ]
    }
    ElMessage.success('消息已删除')
    fetchSessions(false)
  } catch (err) {
    console.error('删除消息失败:', err)
    ElMessage.error('删除消息失败: ' + (err.message || '网络错误'))
  }
}

// 3. 重新生成回答 (仅针对 assistant 消息)
const regenerateMessage = async (msg, index) => {
  if (isLoading.value) {
    ElMessage.warning('AI 正在回复中，请稍候或先停止生成')
    return
  }

  // 寻找该条回答前面的对应用户问题
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

  // 如果不是最后一条消息，提示用户后续对话将被重置
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

  // 若数据库中已有记录，同步删除
  if (msg.id && currentSessionId.value) {
    try {
      await api.deleteMessage(currentSessionId.value, msg.id, !isLastMessage)
    } catch (err) {
      console.error('Failed to clean previous message in DB:', err)
    }
  }

  // 截断前端列表
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

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const renderMarkdown = (text) => {
  return md.render(text || '')
}

onMounted(() => {
  loadHealth()
  loadModels()
  loadBotSettings()
  fetchSessions(true)
})
</script>

<template>
  <el-container class="chat-app">
    <!-- Left Sidebar: Session Memory & Bot Settings -->
    <el-aside :width="isSidebarOpen ? '280px' : '0px'" class="sidebar-wrapper">
      <div class="sidebar" :class="{ collapsed: !isSidebarOpen }">
        <div class="sidebar-header">
          <div class="flex items-center gap-2">
            <el-button type="primary" class="new-chat-btn flex-1" :icon="Plus" @click="createNewSession">
              新建对话
            </el-button>
            <el-tooltip content="导入对话记录 (.json / .md)" placement="bottom">
              <el-button
                type="primary"
                plain
                class="sidebar-import-btn"
                :icon="Upload"
                @click="triggerImportFile"
              />
            </el-tooltip>
          </div>

          <!-- 搜索历史对话关键词 -->
          <div class="sidebar-search-box mt-2.5">
            <el-input
              v-model="searchQuery"
              placeholder="搜索历史对话与关键词..."
              size="small"
              clearable
              :prefix-icon="Search"
              class="history-search-input"
              @input="onSearchInput"
              @clear="clearSearch"
            />
          </div>
        </div>

        <!-- 历史会话列表 / 搜索结果列表 -->
        <el-scrollbar class="sessions-list">
          <!-- 搜索模式 -->
          <template v-if="searchQuery.trim()">
            <div class="sessions-label flex items-center justify-between">
              <span>搜索结果 ({{ searchResults.length }})</span>
              <el-button link type="primary" size="small" class="clear-search-link" @click="clearSearch">
                返回全量
              </el-button>
            </div>

            <div v-if="isSearching" class="py-6 text-center text-xs text-gray-400">
              正在搜索历史记录...
            </div>

            <template v-else-if="searchResults.length > 0">
              <div
                v-for="item in searchResults"
                :key="item.session_id"
                class="search-result-item"
                :class="{ active: item.session_id === currentSessionId }"
                @click="selectSession(item.session_id)"
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
              description="未找到相关历史对话"
              :image-size="45"
              class="py-6"
            />
          </template>

          <!-- 常规历史会话列表 -->
          <template v-else>
            <div class="sessions-label">历史记忆会话</div>
            <div
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              @click="selectSession(s.id)"
            >
              <el-icon class="chat-bubble-icon"><ChatDotRound /></el-icon>
              <span class="session-title" :title="s.title">{{ s.title }}</span>
              <el-button
                link
                type="danger"
                class="delete-btn"
                :icon="Delete"
                title="删除会话"
                @click="deleteSession(s.id, $event)"
              />
            </div>

            <el-empty
              v-if="sessions.length === 0"
              description="暂无历史会话"
              :image-size="50"
              class="py-4"
            />
          </template>
        
        </el-scrollbar>

        <!-- 全局开发助手昵称与人设配置区域 -->
        <div class="persona-panel">
          <div class="persona-panel-title">
            <el-icon><UserFilled /></el-icon>
            <span>开发助手全局人设</span>
          </div>

          <div class="persona-form">
            <el-input
              v-model="botNickname"
              class="custom-textarea"
              clearable
              :clear-icon="CloseBold"
              placeholder="助手全局昵称 (如: 小p)"
              size="small"
            />

            <el-input
              v-model="botPersona"
              class="custom-textarea mt-2"
              type="textarea"
              :rows="3"
              resize="none"
              clearable
              :clear-icon="CloseBold"
              placeholder="助手全局人设 (所有对话均遵循此身份)"
              size="small"
            />

            <div class="mt-2 flex justify-end">
              <el-button
                type="primary"
                size="small"
                plain
                :icon="Check"
                :loading="isSavingBotSettings"
                @click="handleSaveBotSettings"
              >
                保存助手设置
              </el-button>
            </div>
          </div>
        </div>

        <div class="sidebar-footer">
          <div class="memory-badge">
            <span class="pulse-dot"></span>
            <span>服务端记忆与全局人设已启用</span>
          </div>
        </div>
      </div>
    </el-aside>

    <!-- Main Chat Workspace -->
    <el-container class="chat-main">
      <!-- Top Navigation Header -->
      <el-header class="app-header" height="56px">
        <div class="header-left">
          <el-button
            circle
            text
            class="toggle-sidebar-btn"
            :icon="isSidebarOpen ? Fold : Expand"
            @click="isSidebarOpen = !isSidebarOpen"
            title="切换侧边栏"
          />
          <div class="logo-box">
            <span class="logo-icon">🐇</span>
            <span class="app-title">{{ botNickname }}</span>
          </div>

          <div class="model-select-wrap">
            <el-select v-model="selectedModel" placeholder="请选择模型" size="default" style="width: 220px;">
              <el-option
                v-for="m in availableModels"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              />
            </el-select>
          </div>
        </div>

        <div class="header-right flex items-center gap-2">
          <el-tag :type="hasApiKey ? 'success' : 'warning'" effect="dark" round class="status-tag">
            <el-icon class="mr-1">
              <CircleCheckFilled v-if="hasApiKey" />
              <CircleCloseFilled v-else />
            </el-icon>
            {{ hasApiKey ? 'API 就绪' : '未配置 API Key' }}
          </el-tag>

          <!-- 导入对话 -->
          <el-button
            type="info"
            plain
            size="small"
            :icon="Upload"
            @click="triggerImportFile"
            title="导入对话记录 (.json / .md)"
          >
            导入对话
          </el-button>

          <!-- 导出对话下拉菜单 -->
          <el-dropdown trigger="click" @command="handleExportCommand">
            <el-button
              type="primary"
              plain
              size="small"
              :icon="Download"
            >
              导出对话 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu class="custom-dropdown-menu">
                <el-dropdown-item command="markdown" :icon="Document">
                  导出为 Markdown (.md)
                </el-dropdown-item>
                <el-dropdown-item command="json" :icon="Files">
                  导出为 JSON (.json)
                </el-dropdown-item>
                <el-dropdown-item divided command="all" :icon="Download">
                  导出全部会话备份 (.json)
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-button
            type="danger"
            plain
            size="small"
            :icon="Delete"
            @click="clearCurrentSession"
            title="清空本会话记忆"
          >
            清空本会话
          </el-button>
        </div>
      </el-header>

      <!-- Key Warning Banner -->
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
            <span>请在后端 .env 中配置 DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 以便正常调用模型服务。</span>
            <el-button size="small" type="warning" plain :icon="RefreshRight" @click="loadHealth">
              刷新检测
            </el-button>
          </div>
        </template>
      </el-alert>

      <!-- Messages Stream Scroll View -->
      <el-main class="chat-window" ref="messagesContainer">
        <div class="messages-list">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="message-row"
            :class="msg.role"
          >
            <el-avatar
              :size="36"
              class="avatar"
              :class="msg.role === 'user' ? 'bg-blue-600' : 'bg-slate-700'"
            >
              {{ msg.role === 'user' ? '🧑‍💻' : '🤖' }}
            </el-avatar>

            <div class="message-bubble">
              <!-- R1 Reasoning / Thinking Process -->
              <div v-if="msg.reasoning" class="reasoning-card">
                <div
                  class="reasoning-header"
                  @click="msg.showReasoning = !msg.showReasoning"
                >
                  <span class="pulse-icon">🧠</span>
                  <span class="reasoning-title">深度思考过程 (Reasoning)</span>
                  <el-icon class="reasoning-toggle">
                    <ArrowDown v-if="msg.showReasoning" />
                    <ArrowRight v-else />
                  </el-icon>
                </div>
                <el-collapse-transition>
                  <div v-show="msg.showReasoning" class="reasoning-content">
                    {{ msg.reasoning }}
                  </div>
                </el-collapse-transition>
              </div>

              <!-- Main Content -->
              <div
                class="markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <!-- 消息级操作：复制 / 重新生成 / 删除单条 -->
              <div
                v-if="(!isLoading || index !== messages.length - 1) && (msg.content || msg.reasoning)"
                class="message-actions"
              >
                <!-- 复制 -->
                <button
                  type="button"
                  class="msg-action-btn"
                  title="复制消息内容"
                  @click="copyMessage(msg)"
                >
                  <el-icon><CopyDocument /></el-icon>
                  <span>复制</span>
                </button>

                <!-- 重新生成 (仅针对 assistant 回复) -->
                <button
                  v-if="msg.role === 'assistant'"
                  type="button"
                  class="msg-action-btn"
                  title="重新生成此回复"
                  :disabled="isLoading"
                  @click="regenerateMessage(msg, index)"
                >
                  <el-icon><RefreshRight /></el-icon>
                  <span>重新生成</span>
                </button>

                <!-- 删除单条消息 -->
                <button
                  type="button"
                  class="msg-action-btn msg-action-delete"
                  title="删除此条消息"
                  @click="handleDeleteMessage(msg, index)"
                >
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </button>
              </div>

              <!-- Typing Indicator -->
              <div
                v-if="isLoading && index === messages.length - 1 && !msg.content && !msg.reasoning"
                class="typing-indicator"
              >
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
      </el-main>

      <!-- Bottom Chat Input Panel -->
      <el-footer class="input-panel" height="auto">
        <div class="input-container">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 5 }"
            resize="none"
            class="chat-input-el"
            placeholder="与 DeepSeek 对话... (Enter 发送，Shift + Enter 换行)"
            @keydown="handleKeydown"
          />

          <div class="input-actions">
            <el-button
              v-if="isLoading"
              type="danger"
              round
              :icon="VideoPause"
              @click="stopGeneration"
            >
              停止
            </el-button>
            <el-button
              v-else
              type="primary"
              round
              :icon="Position"
              :disabled="!inputMessage.trim()"
              @click="sendMessage"
            >
              发送
            </el-button>
          </div>
        </div>
      </el-footer>
    </el-container>
  </el-container>

  <!-- 隐藏的导入文件 input -->
  <input
    ref="importFileInput"
    type="file"
    accept=".json,.md,.txt"
    style="display: none"
    @change="onImportFileSelected"
  />
</template>

<style scoped>
.chat-app {
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-primary);
  overflow: hidden;
}

.sidebar-wrapper {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #090d16;
  border-right: 1px solid var(--border-color);
  overflow: hidden;
}

.sidebar {
  width: 280px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
}

.new-chat-btn {
  border-radius: 8px;
}

.sessions-list {
  flex: 1;
  padding: 0 12px;
}

.sessions-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 6px 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.88rem;
  transition: all 0.15s;
  margin-bottom: 4px;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.session-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.chat-bubble-icon {
  font-size: 1rem;
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

.search-keyword-highlight {
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

/* 助手全局人设面板样式 */
.persona-panel {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.02);
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}

.persona-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 8px;
}

.sidebar-import-btn {
  padding: 8px 10px !important;
  border-radius: 8px !important;
  background: rgba(59, 130, 246, 0.1) !important;
  border-color: rgba(59, 130, 246, 0.3) !important;
  color: #60a5fa !important;
}

.sidebar-import-btn:hover {
  background: rgba(59, 130, 246, 0.25) !important;
  border-color: #60a5fa !important;
  color: #ffffff !important;
}

/* 导出下拉菜单样式 */
:deep(.custom-dropdown-menu) {
  background: #141b2a !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

:deep(.custom-dropdown-menu .el-dropdown-menu__item) {
  color: #cbd5e1 !important;
}

:deep(.custom-dropdown-menu .el-dropdown-menu__item:hover) {
  background: rgba(59, 130, 246, 0.15) !important;
  color: #60a5fa !important;
}

:deep(.custom-dropdown-menu .el-dropdown-menu__item--divided) {
  border-top-color: rgba(255, 255, 255, 0.08) !important;
}

/* 输入框样式与尺寸控制 */
.custom-textarea {
  width: 100% !important; /* 宽度撑满侧边栏表单区域 */
}

:deep(.custom-textarea .el-input__wrapper) {
  background: #141b2a !important;
  box-shadow: 0 0 0 1px rgba(135, 38, 194, 0.3) inset !important;
  color: #f8fafc !important;
  border-radius: 6px;
  min-height: 32px !important; /* 单行昵称高度 */
}

:deep(.custom-textarea .el-textarea__inner) {
  background: #141b2a !important;
  box-shadow: 0 0 0 1px rgba(135, 38, 194, 0.3) inset !important;
  color: #f8fafc !important;
  border-radius: 6px;
  min-height: 64px !important; /* 多行文本域最小高度 */
  font-size: 13px;
  padding: 8px;
}

:deep(.custom-textarea .el-textarea__inner:focus),
:deep(.custom-textarea .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #8726c2 inset !important;
}

.sidebar-footer {
  padding: 12px 16px;
}

.memory-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.76rem;
  color: #10b981;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.8);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-width: 0;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-sidebar-btn {
  font-size: 1.1rem;
}

.logo-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 1.4rem;
}

.app-title {
  font-weight: 700;
  font-size: 1.1rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.warning-banner {
  border-radius: 0;
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

.message-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.message-row.user {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.message-bubble {
  max-width: 85%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 14px 18px;
  color: var(--text-primary);
  line-height: 1.6;
  font-size: 0.95rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.message-row.user .message-bubble {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border-color: #3b82f6;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .message-bubble {
  border-bottom-left-radius: 4px;
}

.reasoning-card {
  background: var(--reasoning-bg);
  border: 1px solid var(--reasoning-border);
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 0.85rem;
  color: #a78bfa;
}

.reasoning-title {
  font-weight: 600;
  flex: 1;
}

.reasoning-toggle {
  font-size: 0.85rem;
}

.reasoning-content {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(167, 139, 250, 0.3);
  font-size: 0.85rem;
  color: #cbd5e1;
  white-space: pre-wrap;
  line-height: 1.5;
}

/* 消息级操作栏 (复制 / 重新生成 / 删除单条) */
.message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 0.76rem;
  opacity: 0.75;
  transition: opacity 0.2s ease;
}

.message-row:hover .message-actions {
  opacity: 1;
}

.message-row.user .message-actions {
  justify-content: flex-end;
  border-top-color: rgba(255, 255, 255, 0.15);
}

.msg-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 3px 7px;
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 0.75rem;
  line-height: 1.2;
  transition: all 0.15s ease;
  user-select: none;
}

.message-row.user .msg-action-btn {
  color: rgba(255, 255, 255, 0.85);
}

.msg-action-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.message-row.user .msg-action-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.msg-action-delete:hover {
  color: #f87171 !important;
  background: rgba(239, 68, 68, 0.15) !important;
}

.message-row.user .msg-action-delete:hover {
  color: #fecaca !important;
  background: rgba(220, 38, 38, 0.35) !important;
}

.msg-action-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.typing-indicator span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: var(--accent-color);
  border-radius: 50%;
  margin: 0 2px;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}
.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-6px); opacity: 1; }
}

.input-panel {
  padding: 16px 24px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}

.input-container {
  width: 100%;
  max-width: 840px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 8px 12px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

:deep(.chat-input-el .el-textarea__inner) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: var(--text-primary) !important;
  padding: 6px 0 !important;
  font-size: 0.95rem;
  font-family: inherit;
}

.input-actions {
  display: flex;
  align-items: center;
}

:deep(.markdown-body pre) {
  background: var(--code-bg);
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  margin: 10px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

:deep(.markdown-body code) {
  font-family: "Fira Code", monospace;
  font-size: 0.88rem;
}

:deep(.markdown-body p) {
  margin-bottom: 8px;
}

:deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}
</style>
