<script setup>
import { ref, nextTick, onMounted } from 'vue'
import {
  ElContainer,
  ElMain,
  ElAlert,
  ElButton,
  ElMessage,
  ElMessageBox,
  RefreshRight
} from './plugins/element'
import * as api from './api'
import AppSidebar from './components/AppSidebar.vue'
import AppHeader from './components/AppHeader.vue'
import ChatMessageItem from './components/ChatMessageItem.vue'
import ChatInput from './components/ChatInput.vue'

// ==========================================
// 响应式状态定义
// ==========================================
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

// 全局助手昵称与人设
const botNickname = ref('Rabbit AI')
const botPersona = ref('')
const isSavingBotSettings = ref(false)

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
      bot_nickname: botNickname.value.trim() || 'Rabbit AI',
      bot_persona: botPersona.value.trim()
    })
    ElMessage.success('助手设置已成功更新并生效！')
  } catch (err) {
    ElMessage.error('保存设置失败: ' + (err.message || '网络错误'))
  } finally {
    isSavingBotSettings.value = false
  }
}

// ==========================================
// 会话管理 (加载 / 新建 / 切换 / 删除 / 清空)
// ==========================================
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
    messages.value = [
      {
        role: 'assistant',
        content: `本会话的历史记忆已全部清空。我是 ${botNickname.value}，请重新输入你的问题。`,
        reasoning: '',
        showReasoning: false
      }
    ]
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
  if (command === 'markdown') {
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
// 消息发送与流式响应 (SSE)
// ==========================================
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

onMounted(() => {
  loadHealth()
  loadModels()
  loadBotSettings()
  fetchSessions(true)
})
</script>

<template>
  <el-container class="chat-app">
    <!-- 左侧可折叠会话侧边栏组件 -->
    <AppSidebar
      :is-open="isSidebarOpen"
      :sessions="sessions"
      :current-session-id="currentSessionId"
      :bot-nickname="botNickname"
      :bot-persona="botPersona"
      :is-saving-bot-settings="isSavingBotSettings"
      @new-session="createNewSession"
      @select-session="selectSession"
      @delete-session="deleteSession"
      @import-file="triggerImportFile"
      @save-bot-settings="handleSaveBotSettings"
      @update:bot-nickname="botNickname = $event"
      @update:bot-persona="botPersona = $event"
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
            <span>请在后端 .env 中配置 DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 以便正常调用模型服务。</span>
            <el-button size="small" type="warning" plain :icon="RefreshRight" @click="loadHealth">
              刷新检测
            </el-button>
          </div>
        </template>
      </el-alert>

      <!-- 消息列表滚动视图 -->
      <el-main class="chat-window" ref="messagesContainer">
        <div class="messages-list">
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
          />
        </div>
      </el-main>

      <!-- 底部输入栏组件 -->
      <ChatInput
        v-model="inputMessage"
        :is-loading="isLoading"
        :has-api-key="hasApiKey"
        :selected-model="selectedModel"
        @send="sendMessage"
        @stop="stopGeneration"
      />
    </el-container>

    <!-- 隐藏的文件选择器：导入对话 -->
    <input
      type="file"
      ref="importFileInput"
      style="display: none"
      accept=".json,.md,.txt"
      @change="onImportFileSelected"
    />
  </el-container>
</template>

<style scoped>
.chat-app {
  width: 100vw;
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: var(--bg-primary);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
  background-color: var(--bg-primary);
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
</style>
