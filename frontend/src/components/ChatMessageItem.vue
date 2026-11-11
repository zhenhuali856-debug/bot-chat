<script setup>
import {
  ArrowDown,
  ArrowRight,
  CopyDocument,
  RefreshRight,
  Delete,
  Notebook
} from '../plugins/element'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({
  msg: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  isLast: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['copy', 'regenerate', 'delete', 'add-to-chapter'])

const toggleReasoning = () => {
  props.msg.showReasoning = !props.msg.showReasoning
}
</script>

<template>
  <div
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
          @click="toggleReasoning"
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
        v-if="(!isLoading || !isLast) && (msg.content || msg.reasoning)"
        class="message-actions"
      >
        <!-- 复制 -->
        <button
          type="button"
          class="msg-action-btn"
          title="复制消息内容"
          @click="emit('copy', msg)"
        >
          <el-icon><CopyDocument /></el-icon>
          <span>复制</span>
        </button>

        <!-- 添加到作品章节 (仅针对 assistant 生成内容) -->
        <button
          v-if="msg.role === 'assistant' && msg.content"
          type="button"
          class="msg-action-btn msg-action-chapter"
          title="将此内容保存到作品的章节中"
          @click="emit('add-to-chapter', msg)"
        >
          <el-icon><Notebook /></el-icon>
          <span>添加到章节</span>
        </button>

        <!-- 重新生成 (仅针对 assistant 回复) -->
        <button
          v-if="msg.role === 'assistant'"
          type="button"
          class="msg-action-btn"
          title="重新生成此回复"
          :disabled="isLoading"
          @click="emit('regenerate', msg, index)"
        >
          <el-icon><RefreshRight /></el-icon>
          <span>重新生成</span>
        </button>

        <!-- 删除单条消息 -->
        <button
          type="button"
          class="msg-action-btn msg-action-delete"
          title="删除此条消息"
          @click="emit('delete', msg, index)"
        >
          <el-icon><Delete /></el-icon>
          <span>删除</span>
        </button>
      </div>

      <!-- Typing Indicator -->
      <div
        v-if="isLoading && isLast && !msg.content && !msg.reasoning"
        class="typing-indicator"
      >
        <span></span><span></span><span></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
  background: linear-gradient(135deg, var(--accent-color), color-mix(in srgb, var(--accent-color) 80%, black));
  border-color: var(--accent-color);
  border-bottom-right-radius: 4px;
  color: #ffffff;
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
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>

