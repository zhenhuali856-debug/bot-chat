<script setup>
import { computed } from 'vue'
import BaseChart from '../common/BaseChart.vue'

const props = defineProps({
  genreDist: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartOptions = computed(() => {
  const data = (props.genreDist || []).map(g => ({
    name: g.genre || '未分类',
    value: g.count || 0,
    itemStyle: { color: g.color || '#64748b' }
  }))

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: 'rgba(255, 255, 255, 0.12)',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (params) => {
        return `
          <div style="font-weight:700;margin-bottom:2px">${params.name}</div>
          <div>作品数量：<b>${params.value}</b> 部 (${params.percent}%)</div>
        `
      }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'middle',
      textStyle: { color: '#cbd5e1', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 10
    },
    series: [
      {
        name: '体裁分布',
        type: 'pie',
        radius: ['52%', '78%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: 'var(--bg-secondary, #1e293b)',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 6,
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold',
            color: '#f8fafc'
          }
        },
        data: data.length ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#334155' } }]
      }
    ]
  }
})
</script>

<template>
  <div class="panel">
    <div class="panel-hd">
      <h3>体裁分布</h3>
      <span class="ph-sub">作品分类占比</span>
    </div>

    <div class="chart-box">
      <BaseChart
        :options="chartOptions"
        :loading="loading"
        height="190px"
      />
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
  margin-bottom: 8px;
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

.chart-box {
  width: 100%;
  height: 190px;
}
</style>

