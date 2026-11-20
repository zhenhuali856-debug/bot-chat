<script setup>
import { computed } from 'vue'
import BaseChart from '../common/BaseChart.vue'

const props = defineProps({
  trendData: {
    type: Object,
    default: () => ({ labels: [], calls: [], success: [], tokens: [] })
  },
  rangeLabel: {
    type: String,
    default: '近 7 日'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartOptions = computed(() => {
  const labels = props.trendData?.labels || []
  const calls = props.trendData?.calls || []
  const success = props.trendData?.success || []
  const tokens = props.trendData?.tokens || []

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: 'rgba(255, 255, 255, 0.12)',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (params) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const day = labels[idx] || ''
        const callVal = calls[idx] || 0
        const succVal = success[idx] || 0
        const tokVal = (tokens[idx] || 0).toLocaleString('en-US')
        return `
          <div style="font-weight:700;margin-bottom:4px;color:#93c5fd">${day}</div>
          <div style="display:flex;align-items:center;gap:6px;margin:2px 0">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3b82f6"></span>
            <span>调用次数：<b>${callVal}</b></span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin:2px 0">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981"></span>
            <span>成功调用：<b>${succVal}</b></span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin:2px 0;color:#cbd5e1">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#a855f7"></span>
            <span>Token 吞吐：<b>${tokVal}</b></span>
          </div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '3%',
      top: '16%',
      bottom: '6%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10.5 },
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
        name: '调用次数',
        type: 'line',
        smooth: true,
        data: calls,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#8b5cf6' },
        lineStyle: {
          width: 2.6,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#8b5cf6' }
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
              { offset: 0, color: 'rgba(59, 130, 246, 0.35)' },
              { offset: 1, color: 'rgba(139, 92, 246, 0.00)' }
            ]
          }
        }
      },
      {
        name: '成功',
        type: 'line',
        smooth: true,
        data: success,
        symbol: 'none',
        lineStyle: {
          width: 1.8,
          color: '#10b981',
          type: 'dashed'
        }
      }
    ]
  }
})
</script>

<template>
  <div class="panel mon-trend-panel">
    <div class="panel-hd">
      <h3>调用趋势</h3>
      <span class="ph-sub">每日调用次数 / Token</span>
      <span class="ph-right">{{ rangeLabel }}</span>
    </div>

    <div class="chart-box">
      <BaseChart
        :options="chartOptions"
        :loading="loading"
        height="180px"
      />
    </div>

    <div class="mon-trend-legend">
      <span>
        <i style="background: linear-gradient(135deg, #3b82f6, #8b5cf6)"></i>
        调用次数
      </span>
      <span>
        <i style="background: #10b981"></i>
        成功
      </span>
      <span style="margin-left: auto">ECharts 图表引擎 · 数据源：/api/monitor/overview</span>
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
  margin-bottom: 10px;
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

.chart-box {
  width: 100%;
  height: 180px;
}

.mon-trend-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  font-size: 10.5px;
  color: var(--text-muted, #64748b);
}

.mon-trend-legend span {
  display: flex;
  align-items: center;
  gap: 5px;
}

.mon-trend-legend i {
  width: 12px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
}
</style>

