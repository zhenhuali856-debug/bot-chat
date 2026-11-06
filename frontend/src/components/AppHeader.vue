<script setup>
import {
  Fold,
  Expand,
  CircleCheckFilled,
  CircleCloseFilled,
  Upload,
  Download,
  Document,
  Files,
  ArrowDown,
  Delete
} from '../plugins/element'
import ThemeSettingsPopover from './ThemeSettingsPopover.vue'

defineProps({
  isSidebarOpen: {
    type: Boolean,
    default: true
  },
  botNickname: {
    type: String,
    default: 'Rabbit AI'
  },
  selectedModel: {
    type: String,
    default: 'deepseek-chat'
  },
  availableModels: {
    type: Array,
    default: () => []
  },
  hasApiKey: {
    type: Boolean,
    default: true
  },
  disabledClear: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'toggle-sidebar',
  'update:selectedModel',
  'import-file',
  'export-command',
  'clear-session'
])

const handleModelChange = (val) => {
  emit('update:selectedModel', val)
}

const handleExportCommand = (command) => {
  emit('export-command', command)
}
</script>

<template>
  <el-header class="app-header" height="56px">
    <div class="header-left">
      <el-button
        circle
        text
        class="toggle-sidebar-btn"
        :icon="isSidebarOpen ? Fold : Expand"
        title="切换侧边栏"
        @click="emit('toggle-sidebar')"
      />
      <div class="logo-box">
        <span class="logo-icon">🐇</span>
        <span class="app-title">{{ botNickname }}</span>
      </div>

      <div class="model-select-wrap">
        <el-select
          :model-value="selectedModel"
          placeholder="请选择模型"
          size="default"
          style="width: 220px;"
          @update:model-value="handleModelChange"
        >
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
      <!-- 页面主题与自由配色调节组件 -->
      <ThemeSettingsPopover />

      <el-tag
        :type="hasApiKey ? 'success' : 'warning'"
        effect="dark"
        round
        class="status-tag"
      >
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
        title="导入对话记录 (.json / .md)"
        @click="emit('import-file')"
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
        :disabled="disabledClear"
        title="清空本会话记忆"
        @click="emit('clear-session')"
      >
        清空本会话
      </el-button>
    </div>
  </el-header>
</template>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
  background-color: var(--bg-primary);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle-sidebar-btn {
  font-size: 1.2rem;
  color: var(--text-secondary) !important;
}

.toggle-sidebar-btn:hover {
  color: var(--text-primary) !important;
  background: rgba(255, 255, 255, 0.05) !important;
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

.model-select-wrap :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  box-shadow: none;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  font-weight: 500;
}
</style>

