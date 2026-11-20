<script setup>
import { computed } from 'vue'
import BaseChart from '../common/BaseChart.vue'

const props = defineProps({
  trendData: {
    type: Object,
    default: () => ({ points: [], total_words: 0 })
  },
  trendRange: {
    type: String,
    default: 'day'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['range-change'])

const chartOptions = computed(() => {
  const points = props.trendData?.points || []
  const labels = points.map(p => p.label || '')
  const words = points.map(p => p.words || 0)
  const chapters = points.map(p => p.chapters || 0)

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: 'rgba(255, 255, 255, 0.12)',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (params) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const p = points[idx] || {}
        return `
          <div style="font-weight:700;margin-bottom:4px;color:#93c5fd">${p.label || ''}</div>
          <div style="display:flex;align-items:center;gap:6px;margin:2px 0">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3b82f6"></span>
            <span>新增字数：<b>${(p.words || 0).toLocaleString()}</b> 字</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin:2px 0;color:#94a3b8">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981"></span>
            <span>更新章节：<b>${p.chapters || 0}</b> 章</span>
          </div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '3%',
      top: '12%',
      bottom: '6%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.06)',
          type: 'dashed'
        }
      },
      axisLabel: { color: '#94a3b8', fontSize: 10.5 }
    },
    series: [
      {
        name: '新增字数',
        type: 'line',
        smooth: true,
        data: words,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#3b82f6' },
        lineStyle: {
          width: 2.8,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#0ea5e9' },
              { offset: 1, color: '#6366f1' }
            ]
          }
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(14, 165, 233, 0.38)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.00)' }
            ]
          }
        }
      }
    ]
  }
})
</script>

<template>
  <div class="panel">
    <div class="panel-hd">
      <h3>写作趋势</h3>
      <span class="ph-sub">字数与章节产出</span>
      <div class="seg" style="margin-left: auto">
        <button
          :class="{ active: trendRange === 'day' }"
          @click="emit('range-change', 'day')"
        >
          按日（近7日）
        </button>
        <button
          :class="{ active: trendRange === 'week' }"
          @click="emit('range-change', 'week')"
        >
          按周（近4周）
        </button>
      </div>
    </div>

    <div class="chart-box">
      <BaseChart
        :options="chartOptions"
        :loading="loading"
        height="190px"
      />
    </div>

    <div class="trend-legend">
      <span>
        <i style="background: linear-gradient(135deg, #0ea5e9, #6366f1)"></i>
        新增字数
      </span>
      <span style="margin-left: auto">
        区间累计：<b>{{ (trendData.total_words || 0).toLocaleString() }}</b> 字
      </span>
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
  margin-bottom: 12px;
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

.seg {
  display: inline-flex;
  padding: 3px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  gap: 3px;
}

.seg button {
  background: transparent;
  border: none;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.seg button.active {
  background: var(--bg-tertiary, rgba(255, 255, 255, 0.08));
  color: var(--accent-color, #3b82f6);
  font-weight: 600;
}

.trend-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.trend-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.trend-legend i {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  display: inline-block;
}
</style>

