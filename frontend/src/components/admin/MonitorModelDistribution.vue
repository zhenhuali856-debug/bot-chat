<script setup>
defineProps({
  models: {
    type: Array,
    default: () => []
  },
  scopeLabel: {
    type: String,
    default: '全站调用次数占比'
  }
})
</script>

<template>
  <div class="panel mon-model-panel">
    <div class="panel-hd">
      <h3>模型分布</h3>
      <span class="ph-sub">{{ scopeLabel }}</span>
    </div>

    <div class="mon-model-list">
      <div
        v-for="m in models"
        :key="m.model"
        class="mon-model-row"
      >
        <div class="mmr-top">
          <span class="mmr-name">{{ m.model }}</span>
          <span class="mmr-pct">{{ m.percent }}%</span>
        </div>
        <div class="mmr-track">
          <i :style="{ width: `${m.percent}%`, background: m.color }"></i>
        </div>
      </div>
      <div
        v-if="!models.length"
        class="mon-empty-hint"
      >
        暂无模型调用数据
      </div>
    </div>

    <div class="mon-model-foot">
      数据源：/api/monitor/model-distribution
    </div>
  </div>
</template>

<style scoped>
.panel {
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

.mon-model-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 2px;
  min-height: 140px;
}

.mon-model-row .mmr-top {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  margin-bottom: 6px;
}

.mon-model-row .mmr-name {
  color: var(--text-secondary, #94a3b8);
  font-family: var(--font-mono, monospace);
  font-size: 11px;
}

.mon-model-row .mmr-pct {
  margin-left: auto;
  color: var(--text-primary, #f8fafc);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.mon-model-row .mmr-track {
  height: 6px;
  border-radius: 99px;
  background: var(--bg-primary, #0f172a);
  overflow: hidden;
}

.mon-model-row .mmr-track i {
  display: block;
  height: 100%;
  border-radius: 99px;
  transition: width 0.5s ease;
}

.mon-model-foot {
  font-size: 10.5px;
  color: var(--text-muted, #64748b);
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}

.mon-empty-hint {
  text-align: center;
  color: var(--text-muted, #64748b);
  font-size: 12px;
  padding: 30px 0;
}
</style>

