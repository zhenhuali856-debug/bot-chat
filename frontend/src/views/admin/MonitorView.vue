<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  getMonitorCalls,
  getMonitorModelDistribution,
  getMonitorOverview
} from '../../api/monitor'
import MonitorCallTable from '../../components/admin/MonitorCallTable.vue'
import MonitorModelDistribution from '../../components/admin/MonitorModelDistribution.vue'
import MonitorStatCards from '../../components/admin/MonitorStatCards.vue'
import MonitorTrendChart from '../../components/admin/MonitorTrendChart.vue'
import { ElMessage } from '../../plugins/element'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  currentUser: {
    type: Object,
    default: () => ({})
  }
})

const { isAdmin } = useAuthStore()

// 状态筛选与控制
const rangeType = ref('7d') // '7d' | '30d'
const scopeType = ref(isAdmin.value ? 'all' : 'mine') // 'all' | 'mine'
const filterStatus = ref('all')
const filterModel = ref('all')
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const refreshing = ref(false)

// 数据源
const overviewData = ref({
  total_calls: 0,
  success_calls: 0,
  error_calls: 0,
  failure_rate: 0,
  total_tokens: 0,
  avg_duration_ms: 0,
  trend: { labels: [], calls: [], success: [], tokens: [] }
})

const modelDistribution = ref([])
const callLogs = ref({
  total: 0,
  page: 1,
  size: 10,
  total_pages: 1,
  items: []
})

const availableModels = ref(['deepseek-chat', 'glm-4-flash', 'gemini-2.5'])

// 计算属性
const monTitle = computed(() =>
  scopeType.value === 'all' ? '运营监控 · 全站汇总' : '运营监控 · 我的调用'
)

const trendRangeLabel = computed(() =>
  rangeType.value === '7d' ? '近 7 日' : '近 30 日'
)

const modelScopeLabel = computed(() =>
  (scopeType.value === 'all' ? '全站' : '我的') + '调用次数占比'
)

const statCards = computed(() => {
  const ov = overviewData.value
  const callsFormatted = (ov.total_calls || 0).toLocaleString('en-US')
  const successFormatted = (ov.success_calls || 0).toLocaleString('en-US')
  const tokensVal =
    ov.total_tokens >= 1000
      ? (ov.total_tokens / 1000).toFixed(0) + 'k'
      : String(ov.total_tokens || 0)
  const durationVal = ((ov.avg_duration_ms || 0) / 1000).toFixed(1) + 's'

  return [
    {
      label: '调用总数',
      val: callsFormatted,
      ic: '📞',
      trend: trendRangeLabel.value,
      isSuccess: false,
      isFail: false
    },
    {
      label: '成功 / 失败',
      val: `${successFormatted} / ${ov.error_calls || 0}`,
      ic: '✅',
      trend: `失败率 ${ov.failure_rate || 0}%`,
      isSuccess: true,
      isFail: (ov.error_calls || 0) > 0
    },
    {
      label: '总 Token',
      val: tokensVal,
      ic: '🔤',
      trend: '输入 + 输出',
      isSuccess: false,
      isFail: false
    },
    {
      label: '平均耗时',
      val: durationVal,
      ic: '⏱️',
      trend: '每次调用',
      isSuccess: false,
      isFail: false
    }
  ]
})

// 数据加载方法
const loadOverview = async () => {
  try {
    const res = await getMonitorOverview(rangeType.value, scopeType.value)
    if (res) overviewData.value = res
  } catch (err) {
    console.error('获取运营监控概览失败:', err)
  }
}

const loadModelDistribution = async () => {
  try {
    const res = await getMonitorModelDistribution(rangeType.value, scopeType.value)
    if (res?.models) {
      modelDistribution.value = res.models
      res.models.forEach(m => {
        if (m.model && !availableModels.value.includes(m.model)) {
          availableModels.value.push(m.model)
        }
      })
    }
  } catch (err) {
    console.error('获取模型分布失败:', err)
  }
}

const loadCalls = async () => {
  loading.value = true
  try {
    const res = await getMonitorCalls({
      page: currentPage.value,
      size: pageSize.value,
      status: filterStatus.value,
      model: filterModel.value,
      scope: scopeType.value
    })
    if (res) callLogs.value = res
  } catch (err) {
    console.error('获取调用流水失败:', err)
  } finally {
    loading.value = false
  }
}

const fetchAll = async () => {
  await Promise.allSettled([loadOverview(), loadModelDistribution(), loadCalls()])
}

const refreshMonitor = async () => {
  refreshing.value = true
  await fetchAll()
  refreshing.value = false
  ElMessage.success(`监控数据已刷新（${trendRangeLabel.value} · ${scopeType.value === 'all' ? '全站' : '仅我'}）`)
}

const setRange = (range) => {
  if (rangeType.value === range) return
  rangeType.value = range
  fetchAll()
}

const setScope = (scope) => {
  if (scopeType.value === scope) return
  if (scope === 'all' && !isAdmin.value) {
    ElMessage.warning('普通成员仅可查看个人调用数据')
    return
  }
  scopeType.value = scope
  currentPage.value = 1
  fetchAll()
}

const onFilterChange = () => {
  currentPage.value = 1
  loadCalls()
}

const onPageChange = (page) => {
  currentPage.value = page
  loadCalls()
}

watch(isAdmin, (newVal) => {
  if (!newVal && scopeType.value === 'all') {
    scopeType.value = 'mine'
    currentPage.value = 1
    fetchAll()
  }
})

onMounted(() => {
  fetchAll()
})
</script>

<template>
  <section class="admin-page monitor-view">
    <!-- 顶部状态栏 -->
    <div class="ap-head">
      <span class="aph-icon">🩺</span>
      <div>
        <h1 id="monTitle">{{ monTitle }}</h1>
        <p>看系统健康：调用量 / Token / 错误率 / 平均耗时 · ECharts + Element Plus 架构</p>
      </div>
      <div class="aph-right">
        <!-- 时间范围切换 (7d / 30d) -->
        <div class="seg" id="monRangeSeg">
          <button
            :class="{ active: rangeType === '7d' }"
            @click="setRange('7d')"
          >
            近 7 日
          </button>
          <button
            :class="{ active: rangeType === '30d' }"
            @click="setRange('30d')"
          >
            近 30 日
          </button>
        </div>

        <!-- 权限范围切换 (仅管理员可见「全站」) -->
        <div class="seg" id="monScopeSeg" title="仅管理员可切换数据范围">
          <button
            v-if="isAdmin"
            :class="{ active: scopeType === 'all' }"
            @click="setScope('all')"
          >
            全站
          </button>
          <button
            :class="{ active: scopeType === 'mine' }"
            @click="setScope('mine')"
          >
            仅我
          </button>
        </div>

        <!-- 刷新按钮 -->
        <button
          class="btn-primary-sm mon-refresh-btn"
          :class="{ spinning: refreshing }"
          :disabled="refreshing"
          @click="refreshMonitor"
        >
          <span class="refresh-icon">↻</span>
          <span>{{ refreshing ? '刷新中' : '刷新' }}</span>
        </button>
      </div>
    </div>

    <!-- 1. 概览指标卡组件 -->
    <MonitorStatCards :cards="statCards" />

    <!-- 2. 中部图表区：趋势折线图 (ECharts) + 模型分布条 -->
    <div class="mon-chart-grid">
      <MonitorTrendChart
        :trend-data="overviewData.trend"
        :range-label="trendRangeLabel"
        :loading="refreshing"
      />
      <MonitorModelDistribution
        :models="modelDistribution"
        :scope-label="modelScopeLabel"
      />
    </div>

    <!-- 3. 底部流水表格组件 (Element Plus el-table + el-pagination) -->
    <MonitorCallTable
      v-model:status-filter="filterStatus"
      v-model:model-filter="filterModel"
      :call-logs="callLogs"
      :available-models="availableModels"
      :loading="loading"
      @filter-change="onFilterChange"
      @page-change="onPageChange"
    />

    <!-- 4. 底部权限说明 -->
    <div class="dash-note" id="monNote">
      <template v-if="scopeType === 'all'">
        💡 当前全站视角（仅 admin 可选）：所有查询按 scope=all 聚合；member 打开此页会被强制为个人视角，看不到全站数据与「全站」切换。对应验收 AC-1 / AC-2。
      </template>
      <template v-else>
        💡 当前个人视角：概览、趋势、模型分布、明细均按 user_id 过滤为当前登录用户自己的调用数据（scope=mine），符合写作/监控场景的数据隔离要求。
      </template>
    </div>
  </section>
</template>

<style scoped>
.monitor-view {
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
  border-radius: 9px;
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
  transition: all 0.2s ease;
}

.seg button.active {
  background: var(--bg-tertiary, rgba(255, 255, 255, 0.08));
  color: var(--accent-color, #3b82f6);
  font-weight: 600;
}

.btn-primary-sm {
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6, #6366f1));
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
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
  transition: all 0.2s;
}

.btn-primary-sm:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-primary-sm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-icon {
  display: inline-block;
  font-size: 13px;
}

.spinning .refresh-icon {
  animation: idspin 0.7s linear infinite;
}

@keyframes idspin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.mon-chart-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
}

@media (max-width: 1000px) {
  .mon-chart-grid {
    grid-template-columns: 1fr;
  }
}

.dash-note {
  margin-top: 4px;
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

