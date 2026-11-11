<script setup>
import { ref, computed, watch } from 'vue'
import {
  ElDialog,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElSwitch,
  ElTag,
  ElMessage,
  FolderOpened,
  RefreshRight
} from '../plugins/element'
import * as api from '../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  works: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'synced'])

const syncDir = ref('')
const defaultDir = ref('')
const autoSync = ref(true)
const fileFormat = ref('md')
const isBrowsing = ref(false)
const isSaving = ref(false)
const isSyncing = ref(false)
const lastSyncResult = ref(null)

const loadSettings = async () => {
  try {
    const data = await api.getSyncSettings()
    syncDir.value = data.sync_dir || data.default_dir || ''
    defaultDir.value = data.default_dir || ''
    autoSync.value = Boolean(data.auto_sync)
    fileFormat.value = data.file_format || 'md'
  } catch (err) {
    console.error('Failed to load sync settings:', err)
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      lastSyncResult.value = null
      loadSettings()
    }
  }
)

const previewWorkName = computed(() => {
  if (props.works && props.works.length > 0) {
    return props.works[0].title
  }
  return '示例作品'
})

const handleBrowseFolder = async () => {
  isBrowsing.value = true
  try {
    const res = await api.browseSyncFolder(syncDir.value)
    if (res && !res.cancelled && res.path) {
      syncDir.value = res.path
      ElMessage.success('已选择目录：' + res.path)
    }
  } catch (err) {
    ElMessage.warning(err.message || '打开文件夹选择器失败，可直接粘贴本地路径')
  } finally {
    isBrowsing.value = false
  }
}

const handleUseDefaultDir = () => {
  if (defaultDir.value) {
    syncDir.value = defaultDir.value
  }
}

const handleSaveOnly = async () => {
  if (!syncDir.value.trim()) {
    ElMessage.warning('请填写本地同步文件夹路径')
    return
  }
  isSaving.value = true
  try {
    const res = await api.updateSyncSettings({
      sync_dir: syncDir.value.trim(),
      auto_sync: autoSync.value,
      file_format: fileFormat.value
    })
    syncDir.value = res.settings.sync_dir
    emit('synced', res.settings)
    ElMessage.success('本地同步目录配置已保存！')
  } catch (err) {
    ElMessage.error(err.message || '保存配置失败')
  } finally {
    isSaving.value = false
  }
}

const handleSaveAndSyncNow = async () => {
  if (!syncDir.value.trim()) {
    ElMessage.warning('请先填写或选择本地同步目录')
    return
  }
  isSyncing.value = true
  try {
    const saveRes = await api.updateSyncSettings({
      sync_dir: syncDir.value.trim(),
      auto_sync: autoSync.value,
      file_format: fileFormat.value
    })
    syncDir.value = saveRes.settings.sync_dir

    const syncRes = await api.runLocalSync()
    lastSyncResult.value = syncRes
    emit('synced', saveRes.settings)
    ElMessage.success(
      `已同步 ${syncRes.synced_works} 部作品（共 ${syncRes.synced_chapters} 个章节）到本地！`
    )
  } catch (err) {
    ElMessage.error(err.message || '同步到本地失败')
  } finally {
    isSyncing.value = false
  }
}

const handleOpenFolder = async () => {
  if (!syncDir.value.trim()) {
    ElMessage.warning('请先设置本地目录')
    return
  }
  try {
    await api.updateSyncSettings({
      sync_dir: syncDir.value.trim(),
      auto_sync: autoSync.value,
      file_format: fileFormat.value
    })
    await api.openSyncFolder()
  } catch (err) {
    ElMessage.error(err.message || '打开文件夹失败')
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="620px"
    class="local-sync-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="flex items-center gap-2">
        <el-icon class="text-blue-400"><FolderOpened /></el-icon>
        <span class="dialog-title-text">作品与章节 · 本地电脑同步设置</span>
        <el-tag size="small" :type="autoSync ? 'success' : 'info'" effect="plain">
          {{ autoSync ? '自动实时同步已开启' : '手动同步' }}
        </el-tag>
      </div>
    </template>

    <div class="sync-modal-body">
      <!-- 1. 目录位置设置 -->
      <div class="form-field">
        <div class="field-header">
          <label class="field-label">本地同步目录位置 <span class="text-red-400">*</span></label>
          <el-button
            v-if="defaultDir"
            link
            type="primary"
            size="small"
            @click="handleUseDefaultDir"
          >
            恢复默认目录
          </el-button>
        </div>

        <div class="dir-input-row">
          <el-input
            v-model="syncDir"
            placeholder="例如：D:\我的创作\小说手稿"
            class="flex-1"
          />
          <el-button
            :icon="FolderOpened"
            :loading="isBrowsing"
            @click="handleBrowseFolder"
          >
            浏览选择
          </el-button>
        </div>
        <div class="field-hint">
          可直接粘贴本地文件夹路径，或点击「浏览选择」在电脑中挑选目录（不存在时会自动创建）。
        </div>
      </div>

      <!-- 2. 同步格式与自动同步开关 -->
      <div class="options-row">
        <div class="form-field format-box">
          <label class="field-label">导出文件格式</label>
          <el-select v-model="fileFormat" class="w-full">
            <el-option label="Markdown (.md)" value="md" />
            <el-option label="纯文本 (.txt)" value="txt" />
          </el-select>
        </div>

        <div class="auto-sync-box">
          <div class="auto-sync-text">
            <span class="field-label">自动实时同步到本地</span>
            <span class="field-hint">开启后，每次添加、修改、删除章节或作品时自动写入本地文件夹</span>
          </div>
          <el-switch v-model="autoSync" />
        </div>
      </div>

      <!-- 3. 本地文件结构预览 -->
      <div class="tree-preview-box">
        <div class="preview-title">同步目录结构示例</div>
        <pre class="preview-tree">📁 {{ syncDir || 'C:\\Users\\...\\Documents\\RabbitWorks' }}
└── 📁 {{ previewWorkName }}
    ├── 📄 00_作品设定与大纲.{{ fileFormat }}
    ├── 📄 01_第一章：....{{ fileFormat }}
    └── 📄 02_第二章：....{{ fileFormat }}</pre>
      </div>

      <!-- 4. 同步结果提示 -->
      <div v-if="lastSyncResult" class="sync-result-banner">
        <span>
          ✅ 同步完成：已写入 <strong>{{ lastSyncResult.synced_works }}</strong> 部作品、
          <strong>{{ lastSyncResult.synced_chapters }}</strong> 个章节至
          <code>{{ lastSyncResult.sync_dir }}</code>
        </span>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-row">
        <el-button plain :icon="FolderOpened" @click="handleOpenFolder">
          打开本地文件夹
        </el-button>

        <div class="flex items-center gap-2">
          <el-button :loading="isSaving" @click="handleSaveOnly">
            保存设置
          </el-button>
          <el-button
            type="primary"
            :icon="RefreshRight"
            :loading="isSyncing"
            @click="handleSaveAndSyncNow"
          >
            保存并立即同步
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-title-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.sync-modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}

.dir-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.options-row {
  display: flex;
  gap: 16px;
  align-items: center;
}

.format-box {
  width: 170px;
  flex-shrink: 0;
}

.auto-sync-box {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
}

.auto-sync-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tree-preview-box {
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}

.preview-title {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.preview-tree {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}

.sync-result-banner {
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: var(--text-primary);
  font-size: 12.5px;
}

.dialog-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>

