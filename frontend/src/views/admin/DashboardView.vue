<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import * as api from '../../api'
import DashboardGenreChart from '../../components/admin/DashboardGenreChart.vue'
import DashboardStatCards from '../../components/admin/DashboardStatCards.vue'
import DashboardTrendChart from '../../components/admin/DashboardTrendChart.vue'
import DashboardWorkProgress from '../../components/admin/DashboardWorkProgress.vue'
import { ElMessage } from '../../plugins/element'

const props = defineProps({
  currentUser: {
    type: Object,
    default: () => ({ username: 'admin', display_name: '系统管理员', role: 'admin' })
  }
})

const isAdmin = computed(() => props.currentUser?.role === 'admin')
const viewScope = ref('auto')
const trendRange = ref('day')
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

const fetchOverview = async () => {
  try {
    const data = await api.getStatsOverview(viewScope.value)
    if (data) overview.value = data
  } catch (err) {
    console.error('加载概览统计失败:', err)
  }
}

const fetchTrend = async () => {
  try {
    const data = await api.getStatsTrend(trendRange.value, viewScope.value)
    if (data) trendData.value = data
  } catch (err) {
    console.error('加载写作趋势失败:', err)
  }
}

const fetchWorksProgress = async () => {
  try {
    const data = await api.getStatsWorksProgress(viewScope.value)
    if (data?.works) worksProgress.value = data.works
  } catch (err) {
    console.error('加载作品进度失败:', err)
  }
}

const fetchGenreDist = async () => {
  try {
    const data = await api.getStatsGenreDistribution(viewScope.value)
    if (data?.genres) genreDist.value = data.genres
  } catch (err) {
    console.error('加载体裁分布失败:', err)
  }
}

const refreshAll = async () => {
  isLoading.value = true
  try {
    await Promise.allSettled([
      fetchOverview(),
      fetchTrend(),
      fetchWorksProgress(),
      fetchGenreDist()
    ])
  } finally {
    isLoading.value = false
  }
}

const switchScope = (scope) => {
  if (!isAdmin.value && scope === 'all') {
    ElMessage.warning('普通成员仅可查看个人数据')
    return
  }
  viewScope.value = scope
  refreshAll()
}

const onTrendRangeChange = (range) => {
  trendRange.value = range
  fetchTrend()
}

watch(
  () => props.currentUser?.role,
  () => {
    if (!isAdmin.value) viewScope.value = 'mine'
    refreshAll()
  }
)

onMounted(() => {
  if (!isAdmin.value) viewScope.value = 'mine'
  refreshAll()
})
</script>

<template>
  <section class="admin-page dashboard-view">
    <!-- 头部工具栏 -->
    <div class="ap-head">
      <span class="aph-icon">📊</span>
      <div>
        <h1>{{ viewScope === 'mine' ? '个人创作数据看板' : '创作数据总看板' }}</h1>
        <p>全景洞察作品体量、创作趋势与结构化设定积累 · ECharts 数据驱动</p>
      </div>

      <div class="aph-right">
        <!-- 范围切换器（仅管理员可见全站） -->
        <div class="seg" title="切换统计数据范围">
          <button
            v-if="isAdmin"
            :class="{ active: viewScope !== 'mine' }"
            @click="switchScope('all')"
          >
            全站汇总
          </button>
          <button
            :class="{ active: viewScope === 'mine' }"
            @click="switchScope('mine')"
          >
            仅我的数据
          </button>
        </div>

        <button
          class="btn-primary-sm"
          :class="{ spinning: isLoading }"
          :disabled="isLoading"
          @click="refreshAll"
        >
          <span class="refresh-icon">↻</span>
          <span>{{ isLoading ? '刷新中' : '刷新' }}</span>
        </button>
      </div>
    </div>

    <!-- 1. 概览卡片区 -->
    <DashboardStatCards :cards="statCards" />

    <!-- 2. 中间图表区：写作趋势 (ECharts) + 体裁分布 (ECharts) -->
    <div class="chart-grid">
      <DashboardTrendChart
        :trend-data="trendData"
        :trend-range="trendRange"
        :loading="isLoading"
        @range-change="onTrendRangeChange"
      />
      <DashboardGenreChart
        :genre-dist="genreDist"
        :loading="isLoading"
      />
    </div>

    <!-- 3. 下部：作品进度看板 -->
    <DashboardWorkProgress :works-progress="worksProgress" />

    <!-- 4. 权限与隔离说明 -->
    <div class="dash-note">
      💡 数据范围说明：当前以
      <b>{{ viewScope === 'mine' ? '个人数据' : '全站汇总' }}</b>
      展示。多用户环境下，管理员可通过上方切换查看全站或个人数据；普通成员仅展示个人创作资产，确保数据安全隔离。
    </div>
  </section>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ap-head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
}

.aph-icon {
  font-size: 28px;
  line-height: 1;
}

.ap-head h1 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  margin: 0 0 4px 0;
}

.ap-head p {
  font-size: 11.5px;
  color: var(--text-muted, #64748b);
  margin: 0;
}

.aph-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
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
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.seg button.active {
  background: var(--bg-tertiary, rgba(255, 255, 255, 0.08));
  color: var(--accent-color, #3b82f6);
  font-weight: 600;
}

.btn-primary-sm {
  background: var(--accent-gradient, linear-gradient(135deg, #0ea5e9, #6366f1));
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 7px 13px;
  border-radius: 8px;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.25);
}

.refresh-icon {
  display: inline-block;
  font-size: 13px;
}

.spinning .refresh-icon {
  animation: idspin 0.7s linear infinite;
}

@keyframes idspin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chart-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
}

@media (max-width: 1000px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

.dash-note {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  line-height: 1.6;
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-left: 3px solid var(--accent-color, #3b82f6);
  border-radius: 8px;
  padding: 10px 14px;
}
</style>

