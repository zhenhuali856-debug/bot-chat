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
  ElMessage,
  ElMessageBox
} from './plugins/element'

// Markdown parser
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

// States
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

const checkHealth = async () => {
  try {
    const res = await fetch('/api/health')
    if (res.ok) {
      const data = await res.json()
      hasApiKey.value = data.has_api_key
      if (data.default_model) {
        selectedModel.value = data.default_model
      }
    }
  } catch (err) {
    console.warn('Backend not reachable:', err)
    hasApiKey.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await fetch('/api/models')
    if (res.ok) {
      const data = await res.json()
      availableModels.value = data.models || []
    }
  } catch (err) {
    availableModels.value = [
      { id: 'deepseek-chat', name: 'DeepSeek V3 (通用对话)' },
      { id: 'deepseek-reasoner', name: 'DeepSeek R1 (深度思考)' }
    ]
  }
}

// 会话记忆管理
const fetchSessions = async (autoSelectLatest = true) => {
  try {
    const res = await fetch('/api/sessions')
    if (res.ok) {
      const data = await res.json()
      sessions.value = data.sessions || []

      if (autoSelectLatest) {
        if (sessions.value.length > 0) {
          await selectSession(sessions.value[0].id)
        } else {
          await createNewSession()
        }
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
    const res = await fetch(`/api/sessions/${sessionId}/messages`)
    if (res.ok) {
      const data = await res.json()
      const dbMessages = (data.messages || []).map(m => ({
        role: m.role,
        content: m.content,
        reasoning: m.reasoning_content || '',
        showReasoning: false
      }))

      if (dbMessages.length === 0) {
        messages.value = [
          {
            role: 'assistant',
            content: '你好！我是基于 DeepSeek 的 AI 助手。已为你开启新的会话记忆，请随时提问！',
            reasoning: '',
            showReasoning: false
          }
        ]
      } else {
        messages.value = dbMessages
      }
      scrollToBottom()
    }
  } catch (err) {
    console.error('Failed to load session messages:', err)
  }
}

const createNewSession = async () => {
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '新建对话' })
    })
    if (res.ok) {
      const data = await res.json()
      const newSession = data.session
      sessions.value.unshift(newSession)
      currentSessionId.value = newSession.id
      messages.value = [
        {
          role: 'assistant',
          content: '新会话已创建。本会话的所有多轮记忆都会在服务端独立保存，刷新页面不丢失！',
          reasoning: '',
          showReasoning: false
        }
      ]
      scrollToBottom()
    }
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
    const res = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
    if (res.ok) {
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      ElMessage.success('会话已删除')
      if (currentSessionId.value === sessionId) {
        if (sessions.value.length > 0) {
          await selectSession(sessions.value[0].id)
        } else {
          await createNewSession()
        }
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
    const res = await fetch(`/api/sessions/${currentSessionId.value}/clear`, { method: 'POST' })
    if (res.ok) {
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
    }
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

// 消息发送与流式响应 (SSE)
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
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: currentSessionId.value,
        message: content,
        model: selectedModel.value,
        stream: true
      }),
      signal: abortController.signal
    })

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
  checkHealth()
  fetchModels()
  fetchSessions(true)
})
</script>

<template>
  <el-container class="chat-app">
    <!-- Left Sidebar: Session Memory -->
    <el-aside :width="isSidebarOpen ? '260px' : '0px'" class="sidebar-wrapper">
      <div class="sidebar" :class="{ collapsed: !isSidebarOpen }">
        <div class="sidebar-header">
          <el-button type="primary" class="w-full new-chat-btn" :icon="Plus" @click="createNewSession">
            新建对话
          </el-button>
        </div>

        <el-scrollbar class="sessions-list">
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
            :image-size="60"
            class="py-6"
          />
        </el-scrollbar>
       
        <div class="sidebar-footer">
          <div class="memory-badge">
            <span class="pulse-dot"></span>
            <span>服务端记忆已启用</span>
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
            <span class="app-title">Rabbit AI</span>
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

        <div class="header-right">
          <el-tag :type="hasApiKey ? 'success' : 'warning'" effect="dark" round class="status-tag">
            <el-icon class="mr-1">
              <CircleCheckFilled v-if="hasApiKey" />
              <CircleCloseFilled v-else />
            </el-icon>
            {{ hasApiKey ? 'API 就绪' : '未配置 API Key' }}
          </el-tag>

          <el-button
            type="danger"
            plain
            
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
        title="尚未在 backend/.env 中检测到 DEEPSEEK_API_KEY"
        type="warning"
        show-icon
        :closable="false"
        class="warning-banner"
      >
        <template #default>
          <div class="flex items-center justify-between w-full">
            <span>请在后端根目录下配置 API Key 以便正常调用 DeepSeek 服务。</span>
            <el-button size="small" type="warning" plain :icon="RefreshRight" @click="checkHealth">
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
  width: 260px;
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

.sidebar-footer {
  padding: 14px 16px;
  border-top: 1px solid var(--border-color);
}

.memory-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
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
