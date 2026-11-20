<script setup>
defineProps({
  cards: {
    type: Array,
    required: true,
    default: () => []
  }
})
</script>

<template>
  <div class="stat-grid">
    <div
      v-for="(c, idx) in cards"
      :key="idx"
      class="stat-card"
    >
      <div class="sc-top">
        <span class="sc-label">{{ c.label }}</span>
        <span class="sc-ic">{{ c.ic }}</span>
      </div>
      <div class="sc-val">{{ c.val }}</div>
      <div
        class="sc-trend"
        :class="{ up: c.up, down: c.up === false }"
      >
        {{ c.trend }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}

@media (max-width: 1280px) {
  .stat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 15px 16px;
  position: relative;
  overflow: hidden;
}

.stat-card::after {
  content: "";
  position: absolute;
  right: -14px;
  top: -14px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--accent-color, #3b82f6);
  opacity: 0.06;
}

.sc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sc-label {
  font-size: 11.5px;
  color: var(--text-secondary, #94a3b8);
}

.sc-ic {
  font-size: 16px;
  opacity: 0.85;
}

.stat-card .sc-val {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary, #f8fafc);
  margin-top: 8px;
  line-height: 1;
}

.stat-card .sc-trend {
  font-size: 10.5px;
  margin-top: 7px;
  color: var(--text-muted, #64748b);
}

.stat-card .sc-trend.up {
  color: var(--success-color, #10b981);
}

.stat-card .sc-trend.down {
  color: var(--danger-color, #ef4444);
}
</style>

