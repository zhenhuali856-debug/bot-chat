<script setup>
import { ref } from 'vue'
import {
  Plus,
  Upload,
  Search,
  ChatDotRound,
  Delete,
  UserFilled,
  CloseBold,
  Check
} from '../plugins/element'
import * as api from '../api'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: true
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
    default: 'Rabbit AI'
  },
  botPersona: {
    type: String,
    default: ''
  },
  isSavingBotSettings: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'new-session',
  'select-session',
  'delete-session',
  'import-file',
  'save-bot-settings',
  'update:botNickname',
  'update:botPersona'
])

// 搜索状态管理
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
let searchTimer = null

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
</script>

<template>
  <el-aside :width="isOpen ? '280px' : '0px'" class="sidebar-wrapper">
    <div class="sidebar" :class="{ collapsed: !isOpen }">
      <div class="sidebar-header">
        <div class="flex items-center gap-2">
          <el-button
            type="primary"
            class="new-chat-btn flex-1"
            :icon="Plus"
            @click="emit('new-session')"
          >
            新建对话
          </el-button>
          <el-tooltip content="导入对话记录 (.json / .md)" placement="bottom">
            <el-button
              type="primary"
              plain
              class="sidebar-import-btn"
              :icon="Upload"
              @click="emit('import-file')"
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
            :model-value="botNickname"
            class="custom-textarea"
            clearable
            :clear-icon="CloseBold"
            placeholder="助手全局昵称 (如: 小p)"
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
            placeholder="助手全局人设 (所有对话均遵循此身份)"
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
          <span>服务端记忆与全局人设已启用</span>
        </div>
      </div>
    </div>
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
  width: 280px;
  background-color: var(--bg-primary);
}

.sidebar.collapsed {
  display: none;
}

.sidebar-header {
  padding: 16px 12px 12px 12px;
  border-bottom: 1px solid var(--border-color);
}

.new-chat-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 500;
  height: 38px;
  border-radius: 8px;
  transition: opacity 0.2s;
}

.new-chat-btn:hover {
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
  padding: 8px 10px;
}

.sessions-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  padding: 8px 6px 4px 6px;
  letter-spacing: 0.05em;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin-bottom: 2px;
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
  font-size: 1rem;
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

/* 全局人设面板样式 */
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
</style>

