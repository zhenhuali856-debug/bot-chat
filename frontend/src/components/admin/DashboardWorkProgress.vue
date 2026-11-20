<script setup>
defineProps({
  worksProgress: {
    type: Array,
    default: () => []
  }
})
</script>

<template>
  <div class="progress-panel">
    <div class="panel-hd">
      <h3>作品进度看板</h3>
      <span class="ph-sub">字数完成率与章节数</span>
      <span class="ph-right">共 {{ worksProgress.length }} 部作品</span>
    </div>

    <div class="wp-list">
      <div
        v-for="w in worksProgress"
        :key="w.id"
        class="wp-row"
      >
        <div class="wr-name" :title="w.title">{{ w.title }}</div>
        <div class="wr-genre">{{ w.genre || '未分类' }}</div>
        <div class="wr-track">
          <i :style="{ width: `${Math.min(100, w.pct || 0)}%` }"></i>
        </div>
        <div class="wr-pct">{{ w.pct }}%</div>
        <div class="wr-detail">
          {{ (w.word_count || 0).toLocaleString() }} / {{ (w.target_words || 0).toLocaleString() }} 字 · {{ w.chapter_count || 0 }} 章
        </div>
      </div>

      <div v-if="!worksProgress.length" class="wp-empty">
        暂无作品进度数据，可在创作工作台新建作品与设定目标字数。
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-panel {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 16px 18px;
}

.panel-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.panel-hd h3 {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  margin: 0;
}

.panel-hd .ph-sub {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  margin-left: 2px;
}

.panel-hd .ph-right {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.wp-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
}

.wp-row:last-child {
  border-bottom: none;
}

.wp-row .wr-name {
  width: 170px;
  flex: none;
  font-size: 12.5px;
  color: var(--text-primary, #f8fafc);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wp-row .wr-genre {
  width: 74px;
  flex: none;
  font-size: 10.5px;
  color: var(--accent-color, #3b82f6);
}

.wp-row .wr-track {
  flex: 1;
  height: 8px;
  border-radius: 99px;
  background: var(--bg-primary, #0f172a);
  overflow: hidden;
}

.wp-row .wr-track i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: var(--accent-gradient, linear-gradient(135deg, #0ea5e9, #6366f1));
  transition: width 0.4s ease;
}

.wp-row .wr-pct {
  width: 44px;
  text-align: right;
  font-size: 11.5px;
  color: var(--text-primary, #f8fafc);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.wp-row .wr-detail {
  width: 190px;
  text-align: right;
  font-size: 10.5px;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
}

.wp-empty {
  text-align: center;
  padding: 30px;
  font-size: 12px;
  color: var(--text-muted, #64748b);
}
</style>

