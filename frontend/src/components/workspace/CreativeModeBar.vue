<script setup>
defineProps({
  work: {
    type: Object,
    required: true
  },
  prevChapterInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'select-prev-chapter',
  'open-characters',
  'open-materials',
  'open-split-outline',
  'open-export-book'
])
</script>

<template>
  <div class="creative-bar" id="creativeBar">
    <span class="cb-badge">📚 创作模式：作品《{{ work.title }}》</span>
    <span v-if="work.genre" class="cb-genre">{{ work.genre }}</span>
    <span v-if="work.target_words" class="cb-words">
      目标 {{ work.target_words.toLocaleString() }} 字
    </span>

    <!-- 跨章节无缝承接标识与正文预览浮窗 -->
    <div v-if="prevChapterInfo && prevChapterInfo.available_chapters?.length" class="cb-continuity-container">
      <el-popover
        trigger="hover"
        :width="420"
        placement="bottom-start"
        popper-class="continuity-popover"
      >
        <template #reference>
          <div class="cb-prev-chapter-group">
            <span
              class="cb-prev-chapter-label"
              :class="{ 'is-none': prevChapterInfo.id === 'none' }"
            >
              🔗 {{ prevChapterInfo.title ? `已承接：《${prevChapterInfo.title}》` : '不承接前文' }}
            </span>
            <el-dropdown trigger="click" @command="(cmd) => emit('select-prev-chapter', cmd)">
              <span class="cb-prev-chapter-switch" title="点击自由切换任意前序章节或关闭承接">
                切换 ▾
              </span>
              <template #dropdown>
                <el-dropdown-menu class="continuity-dropdown-menu">
                  <div class="continuity-dd-title">选择前情承接章节（自动提取末尾 800 字）</div>
                  <el-dropdown-item
                    v-for="ch in prevChapterInfo.available_chapters"
                    :key="ch.id"
                    :command="ch.id"
                    :class="{ 'is-active-item': ch.id === prevChapterInfo.id }"
                  >
                    <div class="flex items-center justify-between w-full min-w-[200px]">
                      <span class="font-medium mr-2">{{ ch.title }}</span>
                      <span class="text-xs text-gray-400">
                        {{
                          (ch.word_count || 0) > 1000
                            ? `${(ch.word_count / 1000).toFixed(1)}k字`
                            : `${ch.word_count || 0}字`
                        }}
                      </span>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    command="none"
                    :class="{ 'is-active-item': prevChapterInfo.id === 'none' }"
                  >
                    <span class="text-gray-400">🚫 不承接任何章节（独立创作）</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
        <div class="popover-continuity-box">
          <div class="popover-continuity-header">
            <span class="popover-title">📖 上一章《{{ prevChapterInfo.title || '无' }}》末尾片段</span>
            <span v-if="prevChapterInfo.tail_chars" class="popover-tag">
              {{ prevChapterInfo.tail_chars }} 字
            </span>
          </div>
          <div class="popover-continuity-body">
            {{ prevChapterInfo.tail_content || '当前未承接任何前情片段（作为独立章节展开）。' }}
          </div>
          <div class="popover-continuity-footer">
            ✨ 该片段已作为核心上下文自动注入大模型，创作本章时将紧扣上述情节与人物状态进行无缝续写。支持点击右侧“切换”随时指定任意前序章节。
          </div>
        </div>
      </el-popover>
    </div>

    <span
      v-if="work.summary || work.outline"
      class="cb-summary"
      :title="work.summary || work.outline"
    >
      {{ work.summary || work.outline }}
    </span>

    <!-- M2 + M3 快捷入口 -->
    <div class="cb-m2-actions">
      <button
        type="button"
        class="cb-m2-btn role"
        title="管理本作品角色卡（防 OOC 自动注入）"
        @click="emit('open-characters', work)"
      >
        👥 角色卡
      </button>
      <button
        type="button"
        class="cb-m2-btn material"
        title="打开本作品创作素材库"
        @click="emit('open-materials', work)"
      >
        📎 素材库
      </button>
      <button
        type="button"
        class="cb-m2-btn role"
        title="基于作品大纲 AI 一键拆解章节规划"
        @click="emit('open-split-outline', work)"
      >
        ✨ AI 拆章
      </button>
      <button
        type="button"
        class="cb-m2-btn"
        title="将本作品导出为单文件 Markdown 全书"
        @click="emit('open-export-book', work)"
      >
        📖 导出整书
      </button>
    </div>
  </div>
</template>

<style scoped>
.creative-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 9px 22px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-size: 12.5px;
  color: var(--text-secondary);
  transition: all 0.25s ease;
}

.cb-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-primary);
  font-weight: 600;
}

.cb-genre {
  font-size: 11px;
  color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.13);
  border-radius: 5px;
  padding: 2px 7px;
}

.cb-words {
  font-size: 11.5px;
  color: var(--text-secondary);
}

.cb-continuity-container {
  display: inline-flex;
  align-items: center;
}

.cb-prev-chapter-group {
  display: inline-flex;
  align-items: center;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 9999px;
  padding: 2px 6px 2px 10px;
  font-size: 11.5px;
  color: #10b981;
  transition: all 0.2s ease;
}

.cb-prev-chapter-group:hover {
  background: rgba(16, 185, 129, 0.18);
  border-color: rgba(16, 185, 129, 0.5);
}

.cb-prev-chapter-label {
  font-weight: 500;
  cursor: default;
}

.cb-prev-chapter-label.is-none {
  color: var(--text-muted);
}

.cb-prev-chapter-switch {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  margin-left: 6px;
  background: rgba(16, 185, 129, 0.22);
  color: #059669;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 10.5px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.cb-prev-chapter-switch:hover {
  background: #10b981;
  color: #ffffff;
}

.cb-summary {
  font-size: 11.5px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 340px;
}

.cb-m2-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.cb-m2-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 7px;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s ease;
}

.cb-m2-btn:hover {
  color: var(--text-primary);
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.1);
}

.cb-m2-btn.role:hover {
  color: var(--accent-color, #3b82f6);
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.1);
}

.cb-m2-btn.material:hover {
  color: var(--warning-color, #f59e0b);
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.1);
}

.popover-continuity-box {
  padding: 4px 2px;
}

.popover-continuity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.popover-continuity-header .popover-tag {
  font-size: 11px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: normal;
}

.popover-continuity-body {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-secondary, #475569);
  background: var(--bg-tertiary, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 6px;
  padding: 10px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.popover-continuity-footer {
  margin-top: 8px;
  font-size: 11px;
  color: #10b981;
  line-height: 1.45;
}
</style>

