<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  work: {
    type: Object,
    required: true
  },
  chapters: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['edit-target'])

const isDistOpen = ref(false)

const workChapters = computed(() =>
  (props.chapters || [])
    .filter((c) => c.work_id === props.work?.id)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
)

const totalWords = computed(() =>
  workChapters.value.reduce((sum, ch) => sum + (ch.word_count || ch.content?.length || 0), 0)
)

const targetWords = computed(() => props.work?.target_words || 0)

const progressPct = computed(() => {
  if (!targetWords.value) return 0
  return Math.min(100, Math.round((totalWords.value / targetWords.value) * 100))
})

const distribution = computed(() => {
  const list = workChapters.value.map((c) => ({
    id: c.id,
    name: c.title,
    words: c.word_count || c.content?.length || 0
  }))
  const maxWords = Math.max(1, ...list.map((c) => c.words))
  const topN = 5
  const shown = list.slice(0, topN).map((c) => ({
    ...c,
    pct: Math.round((c.words / maxWords) * 100)
  }))
  const rest = list.slice(topN)
  let restItem = null
  if (rest.length > 0) {
    const restSum = rest.reduce((s, c) => s + c.words, 0)
    restItem = {
      name: `其余 ${rest.length} 章`,
      words: restSum,
      pct: Math.round((restSum / maxWords) * 100)
    }
  }
  return { shown, restItem }
})
</script>

<template>
  <div class="word-progress-bar">
    <div class="wp-line">
      <span class="wp-label">📊 《{{ work.title }}》</span>
      <span class="wp-count">
        <b>{{ totalWords.toLocaleString() }}</b>
        <template v-if="targetWords > 0"> / {{ targetWords.toLocaleString() }}</template> 字
      </span>
      <div v-if="targetWords > 0" class="wp-track">
        <div class="wp-fill" :style="{ width: `${progressPct}%` }"></div>
      </div>
      <span class="wp-pct">{{ targetWords > 0 ? `${progressPct}%` : '—' }}</span>

      <span class="wp-toggle" @click="isDistOpen = !isDistOpen">
        章节分布 <span>{{ isDistOpen ? '▴' : '▾' }}</span>
      </span>

      <span class="wp-tools">
        <button
          type="button"
          class="wp-tool"
          title="打开作品设定以调整目标字数"
          @click="emit('edit-target', work)"
        >
          ⚙️ 设定目标
        </button>
      </span>
    </div>

    <div v-if="isDistOpen" class="wp-dist">
      <div v-for="item in distribution.shown" :key="item.id" class="wp-dist-row">
        <span class="wd-name" :title="item.name">{{ item.name }}</span>
        <span class="wd-bar"><i :style="{ width: `${item.pct}%` }"></i></span>
        <span class="wd-words">{{ item.words ? item.words.toLocaleString() : '—' }}</span>
      </div>
      <div v-if="distribution.restItem" class="wp-dist-row">
        <span class="wd-name">{{ distribution.restItem.name }}</span>
        <span class="wd-bar"><i :style="{ width: `${distribution.restItem.pct}%` }"></i></span>
        <span class="wd-words">
          {{ distribution.restItem.words ? distribution.restItem.words.toLocaleString() : '—' }}
        </span>
      </div>
      <div class="wp-noTarget" style="margin-top: 6px">
        {{
          targetWords > 0
            ? `完成率 = 全部章节字数 ${totalWords.toLocaleString()} ÷ 目标 ${targetWords.toLocaleString()} 字 · 进度条随各章编辑实时更新`
            : `未设目标字数（target_words=0）：仅显示全书总字数 ${totalWords.toLocaleString()} 字，点击右侧「设定目标」可开启进度追踪`
        }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.word-progress-bar {
  padding: 10px 22px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  transition: all 0.25s ease;
}

.wp-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
}

.wp-label {
  color: var(--text-primary);
  font-weight: 600;
  white-space: nowrap;
}

.wp-count {
  color: var(--text-secondary);
  white-space: nowrap;
}

.wp-count b {
  color: var(--text-primary);
  font-weight: 700;
}

.wp-track {
  position: relative;
  flex: 1;
  min-width: 120px;
  max-width: 280px;
  height: 8px;
  border-radius: 99px;
  background: var(--bg-tertiary);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.wp-fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--accent-color), #8b5cf6);
  transition: width 0.5s ease;
}

.wp-pct {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-color);
  min-width: 36px;
  text-align: right;
}

.wp-toggle {
  font-size: 11.5px;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.wp-toggle:hover {
  color: var(--accent-color);
  border-color: rgba(59, 130, 246, 0.4);
}

.wp-tools {
  margin-left: auto;
  display: inline-flex;
  gap: 6px;
}

.wp-tool {
  font-size: 10.5px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  transition: all 0.2s ease;
}

.wp-tool:hover {
  color: var(--accent-color);
  border-color: rgba(59, 130, 246, 0.4);
}

.wp-dist {
  margin-top: 9px;
  padding: 10px 12px;
  border-radius: 9px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
}

.wp-dist-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 11.5px;
  color: var(--text-secondary);
}

.wp-dist-row .wd-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wp-dist-row .wd-bar {
  width: 120px;
  height: 6px;
  border-radius: 99px;
  background: var(--bg-primary);
  overflow: hidden;
}

.wp-dist-row .wd-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent-color), #8b5cf6);
  border-radius: 99px;
}

.wp-dist-row .wd-words {
  width: 56px;
  text-align: right;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.wp-noTarget {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
}
</style>

