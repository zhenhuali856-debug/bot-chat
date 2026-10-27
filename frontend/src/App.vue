<script setup>
import { ref, onMounted, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

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

// ==========================================
// 会话记忆管理逻辑 (Session Memory Management)
// ==========================================

const fetchSessions = async (autoSelectLatest = true) => {
  try {
    const res = await fetch('/api/sessions')
    if (res.ok) {
      const data = await res.json()
      sessions.value = data.sessions || []

      if (autoSelectLatest) {
        if (sessions.value.length > 0) {
          // 选中最近活跃的会话
          await selectSession(sessions.value[0].id)
        } else {
          // 没有会话时自动新建一个
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
  if (!confirm('确定要删除此会话及其所有历史记忆吗？')) return

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
    if (res.ok) {
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      if (currentSessionId.value === sessionId) {
        if (sessions.value.length > 0) {
          await selectSession(sessions.value[0].id)
        } else {
          await createNewSession()
        }
      }
    }
  } catch (err) {
    console.error('Failed to delete session:', err)
  }
}

const clearCurrentSession = async () => {
  if (!currentSessionId.value) return
  if (!confirm('确定清空当前会话的记忆吗？')) return

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
      await fetchSessions(false)
    }
  } catch (err) {
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
// 消息发送与流式响应 (SSE)
// ==========================================

const sendMessage = async () => {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value) return

  // 1. 如果没有当前会话，先创建一个
  if (!currentSessionId.value) {
    await createNewSession()
  }

  // 2. 本地即时上屏用户问题
  messages.value.push({
    role: 'user',
    content: content
  })

  inputMessage.value = ''
  isLoading.value = true
  scrollToBottom()

  // 3. 准备 AI 助手的空气泡
  const assistantMsgIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    reasoning: '',
    showReasoning: true
  })

  abortController = new AbortController()

  try {
    // 调用后端：直接传入当前会话ID与单条 message
    // 后端自动维护 SQLite 历史记忆与滑动窗口！
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

    // 会话结束后，静默刷新左侧会话列表（标题可能会更新）
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
  <div class="chat-app">
    <!-- Left Sidebar: Session Memory -->
    <aside class="sidebar" :class="{ collapsed: !isSidebarOpen }">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="createNewSession">
          <span class="icon">➕</span>
          <span>新建对话</span>
        </button>
      </div>

      <div class="sessions-list">
        <div class="sessions-label">历史记忆会话</div>
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId }"
          @click="selectSession(s.id)"
        >
          <span class="chat-bubble-icon">💬</span>
          <span class="session-title" :title="s.title">{{ s.title }}</span>
          <button
            class="delete-btn"
            title="删除会话"
            @click="deleteSession(s.id, $event)"
          >
            ×
          </button>
        </div>

        <div v-if="sessions.length === 0" class="empty-sessions">
          暂无历史会话
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="memory-badge">
          <span class="pulse-dot"></span>
          <span>服务端记忆已启用</span>
        </div>
      </div>
    </aside>

    <!-- Main Chat Workspace -->
    <div class="chat-main">
      <!-- Top Navigation Header -->
      <header class="app-header">
        <div class="header-left">
          <button class="toggle-sidebar-btn" @click="isSidebarOpen = !isSidebarOpen" title="切换侧边栏">
            ☰
          </button>
          <div class="logo-box">
            <span class="logo-icon">🐇</span>
            <span class="app-title">Rabbit AI</span>
          </div>

          <div class="model-badge">
            <select v-model="selectedModel" class="model-select">
              <option v-for="m in availableModels" :key="m.id" :value="m.id">
                {{ m.name }}
              </option>
            </select>
          </div>
        </div>

        <div class="header-right">
          <div class="status-indicator" :class="{ active: hasApiKey }">
            <span class="status-dot"></span>
            <span class="status-text">{{ hasApiKey ? 'API 就绪' : '未配置 API Key' }}</span>
          </div>
          <button class="clear-btn" @click="clearCurrentSession" title="清空本会话记忆">
            🗑️ 清空本会话
          </button>
        </div>
      </header>

      <!-- Key Warning Banner -->
      <div v-if="!hasApiKey" class="warning-banner">
        <span class="warning-icon">⚠️</span>
        <div class="warning-content">
          <strong>提示：</strong> 尚未在 <code>backend/.env</code> 中检测到 <code>DEEPSEEK_API_KEY</code>。
        </div>
        <button class="retry-btn" @click="checkHealth">刷新检测</button>
      </div>

      <!-- Messages Stream Scroll View -->
      <main class="chat-window" ref="messagesContainer">
        <div class="messages-list">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="message-row"
            :class="msg.role"
          >
            <div class="avatar">
              {{ msg.role === 'user' ? '🧑‍💻' : '🤖' }}
            </div>

            <div class="message-bubble">
              <!-- R1 Reasoning / Thinking Process -->
              <div
                v-if="msg.reasoning"
                class="reasoning-card"
              >
                <div
                  class="reasoning-header"
                  @click="msg.showReasoning = !msg.showReasoning"
                >
                  <span class="pulse-icon">🧠</span>
                  <span class="reasoning-title">深度思考过程 (Reasoning)</span>
                  <span class="reasoning-toggle">{{ msg.showReasoning ? '收起 ▾' : '展开 ▸' }}</span>
                </div>
                <div v-show="msg.showReasoning" class="reasoning-content">
                  {{ msg.reasoning }}
                </div>
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
      </main>

      <!-- Bottom Chat Input Panel -->
      <footer class="input-panel">
        <div class="input-container">
          <textarea
            v-model="inputMessage"
            class="chat-input"
            placeholder="与 DeepSeek 对话... (Enter 发送，Shift + Enter 换行)"
            rows="1"
            @keydown="handleKeydown"
          ></textarea>

          <div class="input-actions">
            <button
              v-if="isLoading"
              class="stop-btn"
              @click="stopGeneration"
              title="停止生成"
            >
              ⏹ 停止
            </button>
            <button
              v-else
              class="send-btn"
              :disabled="!inputMessage.trim()"
              @click="sendMessage"
            >
              <span>发送</span>
              <svg class="send-icon" viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.chat-app {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-primary);
  overflow: hidden;
}

/* ==========================================
   Sidebar Styles
   ========================================== */
.sidebar {
  width: 260px;
  background: #090d16;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin-left 0.3s ease;
  flex-shrink: 0;
  z-index: 20;
}

.sidebar.collapsed {
  width: 0;
  margin-left: 0px;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent-color);
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
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
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.88rem;
  transition: all 0.15s;
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
  font-size: 0.9rem;
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
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0 4px;
  transition: opacity 0.2s, color 0.2s;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--danger-color);
}

.empty-sessions {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 24px 0;
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

/* ==========================================
   Main Workspace Styles
   ========================================== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-width: 0;
  position: relative;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.toggle-sidebar-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 0.95rem;
}

.toggle-sidebar-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
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

.model-select {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  outline: none;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--warning-color);
}

.status-indicator.active .status-dot {
  background: var(--success-color);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.clear-btn {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
}

.clear-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
  border-color: var(--danger-color);
}

.warning-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(245, 158, 11, 0.15);
  border-bottom: 1px solid rgba(245, 158, 11, 0.3);
  padding: 10px 24px;
  font-size: 0.85rem;
  color: #fde68a;
}

.retry-btn {
  background: #f59e0b;
  color: #111;
  border: none;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  margin-left: auto;
}

.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;
  display: flex;
  justify-content: center;
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
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
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
  font-size: 0.8rem;
  opacity: 0.8;
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
  padding: 8px 14px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  transition: border-color 0.2s;
}

.input-container:focus-within {
  border-color: var(--border-focus);
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 0.95rem;
  font-family: inherit;
  resize: none;
  max-height: 140px;
  line-height: 1.5;
  padding: 6px 0;
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.input-actions {
  display: flex;
  align-items: center;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

.stop-btn {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border: 1px solid #ef4444;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.9rem;
  cursor: pointer;
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
