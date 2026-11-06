<script setup>
import { Position, VideoPause } from '../plugins/element'

defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  hasApiKey: {
    type: Boolean,
    default: true
  },
  selectedModel: {
    type: String,
    default: 'deepseek-chat'
  }
})

const emit = defineEmits(['update:modelValue', 'send', 'stop'])

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <el-footer class="input-panel" height="auto">
    <div class="input-container">
      <el-input
        :model-value="modelValue"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 5 }"
        placeholder="向 AI 发送消息... (Enter 发送，Shift + Enter 换行)"
        class="custom-chat-input"
        :disabled="isLoading || !hasApiKey"
        @update:model-value="emit('update:modelValue', $event)"
        @keydown="handleKeydown"
      />

      <div class="action-buttons">
        <el-button
          v-if="isLoading"
          type="danger"
          class="stop-btn"
          :icon="VideoPause"
          @click="emit('stop')"
        >
          停止生成
        </el-button>

        <el-button
          v-else
          type="primary"
          class="send-btn"
          :icon="Position"
          :disabled="!modelValue.trim() || !hasApiKey"
          @click="emit('send')"
        >
          发送
        </el-button>
      </div>
    </div>

    <div class="input-tip">
      Rabbit AI 支持服务端多轮记忆持久化 · 当前模型: {{ selectedModel }}
    </div>
  </el-footer>
</template>

<style scoped>
.input-panel {
  padding: 16px 20px 20px 20px;
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
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
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-container:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.15);
}

.custom-chat-input {
  flex: 1;
}

.custom-chat-input :deep(.el-textarea__inner) {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
  color: var(--text-primary) !important;
  font-size: 0.95rem;
  padding: 4px 0;
  resize: none;
}

.action-buttons {
  display: flex;
  align-items: center;
}

.send-btn,
.stop-btn {
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 500;
  height: 36px;
}

.send-btn {
  background: var(--accent-gradient);
  border: none;
}

.send-btn:hover {
  opacity: 0.9;
}

.input-tip {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 8px;
}
</style>

