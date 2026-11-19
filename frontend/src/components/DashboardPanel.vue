<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import * as api from '../api'

const props = defineProps({
  currentUser: {
    type: Object,
    default: () => ({ username: 'admin', display_name: '系统管理员', role: 'admin' })
  }
})

const isAdmin = computed(() => props.currentUser?.role === 'admin')
const viewScope = ref('auto') // admin: 'all' | 'mine'; member: forced 'auto' (personal)
const trendRange = ref('day') // 'day' | 'week'
const isLoading = ref(false)

const overview = ref({
  scope: 'all',
  works: { value: 0, delta_month: 0 },
  chapters: { value: 0, delta_month: 0 },
  total_words: { value: 0, delta_7d: 0 },
  characters: { value: 0, delta_month: 0 },
  materials: { value: 0, delta_month: 0 },
  sessions: { value: 0, delta_month: 0 }
})

const trendData = ref({
  range: 'day',
  total_words: 0,
  points: []
})

const worksProgress = ref([])
const genreDist = ref([])

const formatShortNum = (n) => {
  const num = Number(n || 0)
  if (num >= 10000) return `${(num / 1000).toFixed(1)}k`
  return num.toLocaleString()
}

const statCards = computed(() => {
  const o = overview.value
  return [
    {
      label: '作品数',
      val: formatShortNum(o.works?.value),
      ic: '📚',
      trend: o.works?.delta_month > 0 ? `↑ ${o.works.delta_month} 近30日` : '持平',
      up: (o.works?.delta_month || 0) > 0
    },
    {
      label: '章节数',
      val: formatShortNum(o.chapters?.value),
      ic: '📖',
      trend: o.chapters?.delta_month > 0 ? `↑ ${o.chapters.delta_month} 近30日` : '持平',
      up: (o.chapters?.delta_month || 0) > 0
    },
    {
      label: '总字数',
      val: formatShortNum(o.total_words?.value),
      ic: '✍️',
      trend: o.total_words?.delta_7d > 0 ? `↑ ${formatShortNum(o.total_words.delta_7d)} 近7日` : '近7日无更新',
      up: (o.total_words?.delta_7d || 0) > 0
    },
    {
      label: '角色卡',
      val: formatShortNum(o.characters?.value),
      ic: '👤',
      trend: o.characters?.delta_month > 0 ? `↑ ${o.characters.delta_month} 近30日` : '持平',
      up: (o.characters?.delta_month || 0) > 0
    },
    {
      label: '素材数',
      val: formatShortNum(o.materials?.value),
      ic: '🧩',
      trend: o.materials?.delta_month > 0 ? `↑ ${o.materials.delta_month} 近30日` : '持平',
      up: (o.materials?.delta_month || 0) > 0
    },
    {
      label: '会话数',
      val: formatShortNum(o.sessions?.value),
      ic: '💬',
      trend: o.sessions?.delta_month > 0 ? `↑ ${o.sessions.delta_month} 近30日` : '持平',
      up: (o.sessions?.delta_month || 0) > 0
    }
  ]
})

// SVG 折线趋势图计算
const trendSvgModel = computed(() => {
  const ptsRaw = trendData.value.points || []
  const W = 620
  const H = 190
  const padL = 34
  const padB = 26
  const padT = 16
  const padR = 14
  if (!ptsRaw.length) {
    return { gridLines: [], areaPath: '', polyPoints: '', dots: [], xLabels: [] }
  }
  const values = ptsRaw.map((p) => Number(p.words || 0))
  const maxVal = Math.max(100, ...values) * 1.15
  const stepX = ptsRaw.length > 1 ? (W - padL - padR) / (ptsRaw.length - 1) : 0

  const coords = ptsRaw.map((p, i) => {
    const x = padL + i * stepX
    const y = padT + (H - padT - padB) * (1 - Number(p.words || 0) / maxVal)
    return { x, y, label: p.label, words: Number(p.words || 0), chapters: Number(p.chapters || 0) }
  })

  const polyPoints = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ')
  const areaPath =
    `M${coords[0].x.toFixed(1)},${H - padB} ` +
    coords.map((c) => `L${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ') +
    ` L${coords[coords.length - 1].x.toFixed(1)},${H - padB} Z`

  const gridLines = Array.from({ length: 4 }, (_, i) => {
    const y = padT + ((H - padT - padB) * i) / 3
    return { x1: padL, x2: W - padR, y: y.toFixed(1) }
  })

  return { gridLines, areaPath, polyPoints, dots: coords, xLabels: coords }
})

// SVG 体裁分布环形图计算
const pieSegments = computed(() => {
  const list = genreDist.value || []
  if (!list.length) return []
  const total = list.reduce((acc, item) => acc + (item.count || 0), 0) || 1
  const R = 15.9155
  const C = 2 * Math.PI * R
  let accPct = 0
  return list.map((item) => {
    const pct = (item.count / total) * 100
    const dash = `${((pct / 100) * C).toFixed(3)} ${C.toFixed(3)}`
    const offset = ((-accPct / 100) * C).toFixed(3)
    accPct += pct
    return {
      ...item,
      dash,
      offset
    }
  })
})

const isShowingAllSite = computed(() => isAdmin.value && viewScope.value !== 'mine')

const loadDashboard = async () => {
  isLoading.value = true
  const scopeParam = isAdmin.value ? (viewScope.value === 'mine' ? 'mine' : 'all') : 'auto'
  try {
    const [ov, tr, wp, gd] = await Promise.all([
      api.getStatsOverview(scopeParam),
      api.getStatsTrend(trendRange.value, scopeParam),
      api.getStatsWorksProgress(scopeParam),
      api.getStatsGenreDistribution(scopeParam)
    ])
    overview.value = ov || overview.value
    trendData.value = tr || trendData.value
    worksProgress.value = wp?.works || []
    genreDist.value = gd?.genres || []
  } catch (err) {
    console.error('Failed to load dashboard stats:', err)
  } finally {
    isLoading.value = false
  }
}

const setTrendRange = async (r) => {
  if (trendRange.value === r) return
  trendRange.value = r
  const scopeParam = isAdmin.value ? (viewScope.value === 'mine' ? 'mine' : 'all') : 'auto'
  try {
    trendData.value = await api.getStatsTrend(r, scopeParam)
  } catch (err) {
    console.error('Failed to load trend:', err)
  }
}

const setScope = (s) => {
  viewScope.value = s
  loadDashboard()
}

watch(
  () => props.currentUser?.id,
  () => {
    viewScope.value = 'auto'
    loadDashboard()
  }
)

onMounted(() => {
  loadDashboard()
})

defineExpose({ loadDashboard })
</script>

<template>
  <section class="admin-page">
    <div class="ap-head">
      <span class="aph-icon">📊</span>
      <div>
        <h1>{{ isShowingAllSite ? '创作数据看板 · 全站汇总' : '创作数据看板 · 我的数据' }}</h1>
        <p>
          {{
            isShowingAllSite
              ? '作品 / 章节 / 字数 / 趋势一屏掌握 · 实时聚合数据库统计'
              : `仅统计 ${currentUser?.display_name || currentUser?.username} 名下的创作数据`
          }}
        </p>
      </div>
      <div class="aph-right">
        <div v-if="isAdmin" class="seg" title="管理员可切换全站汇总或个人视角">
          <button
            type="button"
            :class="{ active: viewScope !== 'mine' }"
            @click="setScope('all')"
          >
            全站汇总
          </button>
          <button
            type="button"
            :class="{ active: viewScope === 'mine' }"
            @click="setScope('mine')"
          >
            仅我的
          </button>
        </div>

        <div class="seg">
          <button
            type="button"
            :class="{ active: trendRange === 'day' }"
            @click="setTrendRange('day')"
          >
            按日
          </button>
          <button
            type="button"
            :class="{ active: trendRange === 'week' }"
            @click="setTrendRange('week')"
          >
            按周
          </button>
        </div>

        <button type="button" class="refresh-btn" :disabled="isLoading" @click="loadDashboard">
          {{ isLoading ? '刷新中...' : '↻ 刷新' }}
        </button>
      </div>
    </div>

    <!-- 6 概览卡 -->
    <div class="stat-grid">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="sc-top">
          <span class="sc-label">{{ card.label }}</span>
          <span class="sc-ic">{{ card.ic }}</span>
        </div>
        <div class="sc-val">{{ card.val }}</div>
        <div class="sc-trend" :class="{ up: card.up }">{{ card.trend }}</div>
      </div>
    </div>

    <!-- 图表区：趋势折线 + 体裁饼图 -->
    <div class="chart-grid">
      <div class="panel">
        <div class="panel-hd">
          <h3>写作趋势</h3>
          <span class="ph-sub">{{ trendRange === 'day' ? '每日更新字数' : '每周更新字数' }}</span>
          <span class="ph-right">
            {{ trendRange === 'day' ? '近 7 日' : '近 4 周' }}
            {{ (trendData.total_words || 0).toLocaleString() }} 字
          </span>
        </div>

        <svg class="trend-svg" viewBox="0 0 620 190" preserveAspectRatio="none">
          <defs>
            <linearGradient id="dashTgArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.35" />
              <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0" />
            </linearGradient>
            <linearGradient id="dashTgLine" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#3b82f6" />
              <stop offset="100%" stop-color="#8b5cf6" />
            </linearGradient>
          </defs>
          <line
            v-for="(g, idx) in trendSvgModel.gridLines"
            :key="idx"
            :x1="g.x1"
            :y1="g.y"
            :x2="g.x2"
            :y2="g.y"
            stroke="var(--border-color)"
            stroke-dasharray="3 4"
          />
          <path v-if="trendSvgModel.areaPath" :d="trendSvgModel.areaPath" fill="url(#dashTgArea)" />
          <polyline
            v-if="trendSvgModel.polyPoints"
            :points="trendSvgModel.polyPoints"
            fill="none"
            stroke="url(#dashTgLine)"
            stroke-width="2.5"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          <g v-for="(pt, idx) in trendSvgModel.dots" :key="idx">
            <circle
              :cx="pt.x.toFixed(1)"
              :cy="pt.y.toFixed(1)"
              r="4"
              fill="var(--bg-secondary)"
              stroke="#8b5cf6"
              stroke-width="2"
            >
              <title>{{ pt.label }}：{{ pt.words.toLocaleString() }} 字（{{ pt.chapters }} 章）</title>
            </circle>
            <text
              :x="pt.x.toFixed(1)"
              y="184"
              fill="var(--text-muted)"
              font-size="10"
              text-anchor="middle"
            >
              {{ pt.label }}
            </text>
          </g>
        </svg>

        <div class="trend-legend">
          <span><i style="background: linear-gradient(135deg, #3b82f6, #8b5cf6)"></i>更新字数</span>
          <span style="margin-left: auto">数据源：/api/stats/trend</span>
        </div>
      </div>

      <div class="panel">
        <div class="panel-hd">
          <h3>体裁分布</h3>
          <span class="ph-sub">作品占比</span>
        </div>

        <div v-if="pieSegments.length > 0" class="pie-wrap">
          <svg class="pie-svg" viewBox="0 0 42 42">
            <circle
              cx="21"
              cy="21"
              r="15.9155"
              fill="none"
              stroke="var(--bg-tertiary)"
              stroke-width="5"
            />
            <circle
              v-for="seg in pieSegments"
              :key="seg.name"
              cx="21"
              cy="21"
              r="15.9155"
              fill="transparent"
              :stroke="seg.color"
              stroke-width="5"
              :stroke-dasharray="seg.dash"
              :stroke-dashoffset="seg.offset"
            >
              <title>{{ seg.name }}：{{ seg.count }} 部 ({{ seg.percent }}%)</title>
            </circle>
            <text
              x="21"
              y="20.5"
              text-anchor="middle"
              fill="var(--text-primary)"
              font-size="4.2"
              font-weight="700"
            >
              {{ overview.works?.value || 0 }} 部
            </text>
            <text
              x="21"
              y="25"
              text-anchor="middle"
              fill="var(--text-muted)"
              font-size="2.6"
            >
              作品体裁
            </text>
          </svg>
          <div class="pie-legend">
            <div v-for="item in genreDist" :key="item.name" class="pie-leg-row">
              <span class="pl-dot" :style="{ background: item.color }"></span>
              <span>{{ item.name }}</span>
              <span class="pl-val">{{ item.percent }}% ({{ item.count }})</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-chart">暂无作品数据，创建作品后自动呈现体裁分布</div>
      </div>
    </div>

    <!-- 各作品完成率 -->
    <div class="progress-panel">
      <div class="panel-hd">
        <h3>各作品完成率</h3>
        <span class="ph-sub">word_count / target_words</span>
        <span class="ph-right">
          {{ worksProgress.length }} 部作品{{ isShowingAllSite ? '' : '（我的）' }}
        </span>
      </div>

      <div v-if="worksProgress.length > 0">
        <div v-for="w in worksProgress" :key="w.id" class="wp-row">
          <span class="wr-name" :title="w.title">{{ w.title }}</span>
          <span class="wr-genre">{{ w.genre }}</span>
          <span class="wr-track">
            <i :style="{ width: `${w.progress_pct}%` }"></i>
          </span>
          <span class="wr-words">
            {{ w.word_count.toLocaleString()
            }}{{ w.target_words > 0 ? ` / ${w.target_words.toLocaleString()}` : '' }} 字
          </span>
          <span class="wr-pct">{{ w.target_words > 0 ? `${w.progress_pct}%` : '—' }}</span>
        </div>
      </div>
      <div v-else class="empty-chart">暂无作品记录，前往「创作工作台」新建你的第一部作品吧</div>
    </div>

    <div class="dash-note">
      {{
        isShowingAllSite
          ? '💡 权限说明：管理员（admin）默认可见全站汇总数据并拥有「用户管理」入口；普通成员（member）登录后仅能查看自己名下的作品与看板数据，实现全表 user_id 隔离。'
          : '💡 当前为个人数据视角：概览卡、写作趋势、体裁分布与作品进度均已按当前账号 user_id 严格过滤，不会暴露其他用户的创作内容。'
      }}
    </div>
  </section>
</template>

<style scoped>
.admin-page {
  padding: 24px 28px 40px;
  max-width: 1280px;
  margin: 0 auto;
}

.ap-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.ap-head .aph-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-gradient);
  font-size: 19px;
  flex: none;
}

.ap-head h1 {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.25;
  margin: 0;
}

.ap-head p {
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.ap-head .aph-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.seg {
  display: flex;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 3px;
}

.seg button {
  font-size: 11.5px;
  color: var(--text-secondary);
  padding: 5px 12px;
  border-radius: 6px;
  font-weight: 600;
  border: none;
  background: transparent;
  cursor: pointer;
}

.seg button.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.refresh-btn {
  font-size: 11.5px;
  color: var(--text-secondary);
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  color: var(--accent-color);
  border-color: rgba(59, 130, 246, 0.45);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 15px 16px;
  position: relative;
  overflow: hidden;
}

.stat-card::after {
  content: '';
  position: absolute;
  right: -14px;
  top: -14px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--accent-color);
  opacity: 0.06;
}

.stat-card .sc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-card .sc-label {
  font-size: 11.5px;
  color: var(--text-secondary);
}

.stat-card .sc-ic {
  font-size: 16px;
  opacity: 0.85;
}

.stat-card .sc-val {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
  margin-top: 8px;
  line-height: 1;
}

.stat-card .sc-trend {
  font-size: 10.5px;
  margin-top: 7px;
  color: var(--text-muted);
}

.stat-card .sc-trend.up {
  color: var(--success-color, #10b981);
}

.chart-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
  margin-bottom: 18px;
}

@media (max-width: 1000px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

.panel,
.progress-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
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
  color: var(--text-primary);
  margin: 0;
}

.panel-hd .ph-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 2px;
}

.panel-hd .ph-right {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.trend-svg {
  width: 100%;
  height: 190px;
  display: block;
  overflow: visible;
}

.trend-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 12px;
  font-size: 11px;
  color: var(--text-muted);
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

.pie-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}

.pie-svg {
  width: 150px;
  height: 150px;
  flex: none;
}

.pie-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pie-leg-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--text-secondary);
}

.pie-leg-row .pl-dot {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  flex: none;
}

.pie-leg-row .pl-val {
  margin-left: auto;
  color: var(--text-primary);
  font-weight: 600;
}

.wp-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border-color);
}

.wp-row:last-child {
  border-bottom: none;
}

.wp-row .wr-name {
  width: 180px;
  flex: none;
  font-size: 12.5px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wp-row .wr-genre {
  width: 78px;
  flex: none;
  font-size: 10.5px;
  color: var(--accent-color);
}

.wp-row .wr-track {
  flex: 1;
  height: 8px;
  border-radius: 99px;
  background: var(--bg-tertiary);
  overflow: hidden;
}

.wp-row .wr-track i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: var(--accent-gradient);
  transition: width 0.4s ease;
}

.wp-row .wr-words {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.wp-row .wr-pct {
  width: 40px;
  text-align: right;
  font-size: 11.5px;
  color: var(--text-primary);
  font-weight: 700;
}

.empty-chart {
  padding: 36px 12px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
}

.dash-note {
  margin-top: 16px;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--accent-color);
  border-radius: 8px;
  padding: 10px 14px;
}
</style>

