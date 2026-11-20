<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '../../plugins/element'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  work: {
    type: Object,
    default: null
  },
  chapters: {
    type: Array,
    default: () => []
  },
  trend: {
    type: Object,
    default: () => ({ points: [], total_words: 0 })
  },
  overview: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: [Boolean, String],
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'refresh'])
const router = useRouter()

const close = () => {
  emit('update:modelValue', false)
}

const handleKeyDown = (e) => {
  if (e.key === 'Escape' && props.modelValue) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

// Block A: 作品已写字数与进度本地计算
const doneWords = computed(() => {
  if (!props.work) return 0
  const workChapters = props.chapters.filter((c) => c.work_id === props.work.id)
  if (workChapters.length > 0) {
    return workChapters.reduce((sum, c) => sum + (c.word_count || 0), 0)
  }
  return Number(props.work.word_count || 0)
})

const hasTarget = computed(() => {
  return Number(props.work?.target_words || 0) > 0
})

const progressPct = computed(() => {
  if (!hasTarget.value) return 0
  const target = Number(props.work.target_words)
  return Math.min(100, Math.round((doneWords.value / target) * 100))
})

// Block B: 近 7 日写作趋势折线图 SVG 计算
const trendSvg = computed(() => {
  const points = props.trend?.points || []
  const W = 320
  const H = 110
  const padL = 10
  const padB = 18
  const padT = 12
  const padR = 10

  if (!points.length) {
    return { hasData: false, grid: [], area: '', line: '', dots: [], xLabels: [], totalWords: 0 }
  }

  const data = points.map((p) => Number(p.words || 0))
  const max = Math.max(10, ...data) * 1.15
  const stepX = points.length > 1 ? (W - padL - padR) / (points.length - 1) : 0

  const pts = points.map((p, i) => {
    const x = padL + i * stepX
    const y = padT + (H - padT - padB) * (1 - Number(p.words || 0) / max)
    return { x, y, label: p.label, words: Number(p.words || 0) }
  })

  const line = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = `M${pts[0].x.toFixed(1)},${H - padB} L${pts
    .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(' L')} L${pts[pts.length - 1].x.toFixed(1)},${H - padB} Z`

  const gy = 3
  const grid = Array.from({ length: gy }, (_, i) => {
    const y = padT + ((H - padT - padB) * i) / (gy - 1)
    return { y: Number(y.toFixed(1)), x1: padL, x2: W - padR }
  })

  const xLabels = points.map((d, i) => {
    const shouldShow = i % 2 === 0 || i === points.length - 1
    return {
      x: Number((padL + i * stepX).toFixed(1)),
      y: H - 4,
      text: d.label,
      show: shouldShow
    }
  })

  const totalWords = data.reduce((a, b) => a + b, 0)

  return {
    hasData: true,
    grid,
    area,
    line,
    dots: pts,
    xLabels,
    totalWords: Number(props.trend?.total_words ?? totalWords)
  }
})

// 判断是否为空状态（无作品且概览全为 0）
const isEmptyState = computed(() => {
  if (props.loading || props.error) return false
  if (!props.overview) return false
  const ch = Number(props.overview?.chapters?.value || 0)
  const tw = Number(props.overview?.total_words?.value || 0)
  const cr = Number(props.overview?.characters?.value || 0)
  return ch === 0 && tw === 0 && cr === 0 && !props.work
})

// 跳转完整看板
const gotoFullDashboard = () => {
  close()
  router.push('/admin/dashboard')
  ElMessage.success('已跳转到 /admin/dashboard · 写作状态由 keep-alive 保留')
}
</script>

<template>
  <div class="insight-wrapper">
    <!-- 遮罩：仅小屏 (<=900px) 覆盖式出现 -->
    <div
      class="insight-scrim"
      :class="{ show: modelValue }"
      @click="close"
    />

    <!-- 抽屉本体：绝对定位于工作台右侧，大屏挤压 chat-main -->
    <aside
      class="insight-drawer"
      :class="{ open: modelValue }"
      aria-label="创作洞察抽屉"
      :aria-hidden="!modelValue"
    >
      <!-- 头部 -->
      <div class="id-head">
        <div class="id-head-top">
          <div class="id-title">
            <span class="id-title-ic">📊</span>
            <span>创作洞察</span>
          </div>
          <button
            class="id-close"
            title="关闭（Esc）"
            aria-label="关闭洞察抽屉"
            @click="close"
          >
            ×
          </button>
        </div>
        <div class="id-sub">
          <span class="id-scope" title="写作场景固定读取当前登录用户自己的数据">
            🔒 仅个人数据 · mine
          </span>
          <span class="id-updated">刚刚更新</span>
          <button
            class="id-refresh"
            :class="{ spinning: loading }"
            title="重新读取数据"
            :disabled="loading"
            @click="emit('refresh')"
          >
            <span>⟳</span> 刷新
          </button>
        </div>
      </div>

      <!-- 抽屉滚动内容区（四态设计：加载中 / 错误 / 无数据 / 有数据） -->
      <div class="id-body">
        <!-- 1. 加载中态：三块骨架屏 -->
        <div v-if="loading" class="id-view-loading" aria-busy="true">
          <div class="id-sk-card">
            <div class="id-sk id-sk-line" style="width: 62%" />
            <div class="id-sk id-sk-line" style="width: 40%" />
            <div class="id-sk id-sk-line" style="width: 88%; height: 8px; margin-top: 14px" />
          </div>
          <div class="id-sk-card">
            <div class="id-sk id-sk-line" style="width: 50%" />
            <div class="id-sk id-sk-block" />
          </div>
          <div class="id-sk-card">
            <div class="id-sk id-sk-line" style="width: 46%" />
            <div style="display: flex; gap: 8px; margin-top: 12px">
              <div class="id-sk" style="flex: 1; height: 52px" />
              <div class="id-sk" style="flex: 1; height: 52px" />
              <div class="id-sk" style="flex: 1; height: 52px" />
            </div>
          </div>
        </div>

        <!-- 2. 错误态 -->
        <div v-else-if="error" class="id-view-error">
          <div class="id-full-error">
            <div class="id-state-ic">⚠️</div>
            <div class="id-state-t">
              数据暂时不可用
              <br>
              <span class="id-state-sub">
                接口请求异常或登录凭据过期（401），不影响当前继续写作
              </span>
            </div>
            <button class="id-retry" @click="emit('refresh')">
              ↻ 重试
            </button>
          </div>
        </div>

        <!-- 3. 无数据空状态 -->
        <div v-else-if="isEmptyState" class="id-view-empty">
          <div class="id-state">
            <div class="id-state-ic">🌱</div>
            <div class="id-state-t">
              尚无写作记录
              <br>
              写下第一句话，趋势与进度就会出现在这里
            </div>
          </div>
          <div style="height: 14px" />
          <div class="id-state">
            <div class="id-state-ic">📭</div>
            <div class="id-state-t">还没有可展示的速览数据</div>
          </div>
        </div>

        <!-- 4. 正常数据态 -->
        <div v-else class="id-view-data">
          <!-- A · 当前作品进度 -->
          <section class="id-block">
            <div class="id-block-head">
              <span class="id-block-idx">A</span>
              <span class="id-block-title">当前作品进度</span>
              <span class="id-block-tag">本地计算 · 0 请求</span>
            </div>
            <div class="id-workcard">
              <template v-if="work">
                <div class="id-work-name" :title="work.title">
                  {{ work.title }}
                </div>
                <span class="id-work-genre">
                  {{ work.genre || '未分类' }}
                </span>
                <div class="id-work-count">
                  <span class="id-work-done">{{ doneWords.toLocaleString('en-US') }}</span>
                  <span class="id-work-sep">/</span>
                  <span class="id-work-target">
                    {{ hasTarget ? `${Number(work.target_words).toLocaleString('en-US')} 字` : '未设目标' }}
                  </span>
                  <span v-if="hasTarget" class="id-work-pct">{{ progressPct }}%</span>
                </div>
                <div v-if="hasTarget" class="id-track">
                  <i :style="{ width: `${progressPct}%` }" />
                </div>
                <div v-else class="id-work-empty" style="padding: 4px 0 0">
                  target_words = 0 · 仅显示总字数，不计算完成率
                </div>
              </template>
              <div v-else class="id-work-empty">
                当前不在任何作品中，去左侧选择一个作品
                <br>
                即可查看 <b>该作品的实时进度</b>（无需请求后端）。
              </div>
            </div>
          </section>

          <!-- B · 近 7 日写作趋势 -->
          <section class="id-block">
            <div class="id-block-head">
              <span class="id-block-idx">B</span>
              <span class="id-block-title">近 7 日写作趋势</span>
              <span class="id-block-tag">getStatsTrend('day','mine')</span>
            </div>
            <div class="id-trend">
              <svg
                class="id-trend-svg"
                viewBox="0 0 320 110"
                preserveAspectRatio="none"
                aria-label="近 7 日写作趋势折线图"
              >
                <defs>
                  <linearGradient id="idtgA" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.4" />
                    <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0" />
                  </linearGradient>
                  <linearGradient id="idtgL" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#3b82f6" />
                    <stop offset="100%" stop-color="#8b5cf6" />
                  </linearGradient>
                </defs>

                <!-- 网格线 -->
                <line
                  v-for="(g, idx) in trendSvg.grid"
                  :key="idx"
                  :x1="g.x1"
                  :y1="g.y"
                  :x2="g.x2"
                  :y2="g.y"
                  stroke="var(--border-color, rgba(255,255,255,.08))"
                  stroke-dasharray="2 4"
                />

                <!-- 渐变阴影填充面 -->
                <path v-if="trendSvg.hasData" :d="trendSvg.area" fill="url(#idtgA)" />

                <!-- 折线 -->
                <polyline
                  v-if="trendSvg.hasData"
                  :points="trendSvg.line"
                  fill="none"
                  stroke="url(#idtgL)"
                  stroke-width="2.4"
                  stroke-linejoin="round"
                  stroke-linecap="round"
                />

                <!-- 数据圆点 -->
                <circle
                  v-for="(dot, i) in trendSvg.dots"
                  :key="i"
                  :cx="dot.x.toFixed(1)"
                  :cy="dot.y.toFixed(1)"
                  :r="i === trendSvg.dots.length - 1 ? 3.6 : 2.6"
                  fill="var(--bg-secondary, #1e293b)"
                  stroke="#8b5cf6"
                  stroke-width="1.8"
                />

                <!-- X 轴日期 -->
                <text
                  v-for="(lbl, idx) in trendSvg.xLabels"
                  v-show="lbl.show"
                  :key="idx"
                  :x="lbl.x"
                  :y="lbl.y"
                  fill="var(--text-muted, #64748b)"
                  font-size="8.5"
                  text-anchor="middle"
                >
                  {{ lbl.text }}
                </text>
              </svg>

              <div class="id-trend-foot">
                <span>近 7 日共 <b>{{ trendSvg.totalWords.toLocaleString('en-US') }}</b> 字</span>
                <span class="id-legend"><i />每日新增</span>
              </div>
            </div>
          </section>

          <!-- C · 三项速览 -->
          <section class="id-block">
            <div class="id-block-head">
              <span class="id-block-idx">C</span>
              <span class="id-block-title">三项速览</span>
              <span class="id-block-tag">getStatsOverview('mine')</span>
            </div>
            <div class="id-quick">
              <div class="id-qcard">
                <div class="id-qval">+{{ overview?.chapters?.delta_month || 0 }}</div>
                <div class="id-qlabel">本月新增章节</div>
                <div class="id-qdelta">共 {{ overview?.chapters?.value || 0 }} 章</div>
              </div>

              <div class="id-qcard">
                <div class="id-qval">
                  +{{ (((overview?.total_words?.delta_7d || 0)) / 1000).toFixed(1) }}<small>k</small>
                </div>
                <div class="id-qlabel">近 7 日新增字数</div>
                <div class="id-qdelta">
                  共 {{ (((overview?.total_words?.value || 0)) / 1000).toFixed(1) }}k 字
                </div>
              </div>

              <div class="id-qcard">
                <div class="id-qval">{{ overview?.characters?.value || 0 }}</div>
                <div class="id-qlabel">角色卡数量</div>
                <div class="id-qdelta">本月持平</div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- 底部：跳转完整看板 -->
      <div class="id-foot">
        <button class="id-goto" @click="gotoFullDashboard">
          <span>查看完整看板</span>
          <span>→</span>
        </button>
        <div class="id-foot-hint">
          跳转 /admin/dashboard · 写作状态由 keep-alive 保留
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* 抽屉宽度变量：大屏 min(360px, 32vw)；小屏覆盖式 */
:root {
  --drawer-w: 360px;
}
@media (max-width: 1120px) {
  :root {
    --drawer-w: 32vw;
  }
}
@media (max-width: 900px) {
  :root {
    --drawer-w: min(360px, 86vw);
  }
}

/* 遮罩：仅小屏 (<=900px) 覆盖式出现 */
.insight-scrim {
  position: absolute;
  inset: 0;
  z-index: 55;
  background: rgba(2, 6, 23, 0.5);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.25s ease, visibility 0.25s ease;
}
.insight-scrim.show {
  opacity: 1;
  visibility: visible;
}
@media (min-width: 901px) {
  .insight-scrim {
    display: none;
  }
}

/* 抽屉本体：绝对定位于工作台右侧，挤压 chat-main */
.insight-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--drawer-w, 360px);
  z-index: 60;
  background: var(--bg-secondary, #1e293b);
  border-left: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  box-shadow: -18px 0 44px rgba(0, 0, 0, 0.34);
  display: flex;
  flex-direction: column;
  transform: translateX(102%);
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  visibility: hidden;
}
.insight-drawer.open {
  transform: translateX(0);
  visibility: visible;
}

/* 抽屉头部 */
.id-head {
  flex: none;
  padding: 16px 16px 13px;
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}
.id-head-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.id-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  display: flex;
  align-items: center;
  gap: 8px;
}
.id-title .id-title-ic {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  font-size: 14px;
}
.id-close {
  margin-left: auto;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  background: var(--bg-primary, #0f172a);
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.id-close:hover {
  color: var(--text-primary, #f8fafc);
  border-color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.12);
}
.id-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 9px;
}
.id-scope {
  font-size: 10.5px;
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(139, 92, 246, 0.28);
  padding: 2px 8px;
  border-radius: 99px;
  font-weight: 600;
  letter-spacing: 0.2px;
}
.id-updated {
  font-size: 10.5px;
  color: var(--text-muted, #64748b);
}
.id-refresh {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 7px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  background: transparent;
  transition: all 0.15s;
}
.id-refresh:hover:not(:disabled) {
  color: var(--accent-color, #3b82f6);
  border-color: var(--accent-color, #3b82f6);
}
.id-refresh.spinning span {
  display: inline-block;
  animation: idspin 0.7s linear infinite;
}
@keyframes idspin {
  to {
    transform: rotate(360deg);
  }
}

/* 抽屉滚动内容 */
.id-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 14px 8px;
}
.id-body::-webkit-scrollbar {
  width: 6px;
}
.id-body::-webkit-scrollbar-thumb {
  background: var(--bg-tertiary, #334155);
  border-radius: 99px;
}
.id-block {
  margin-bottom: 14px;
}
.id-block-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 9px;
}
.id-block-idx {
  width: 17px;
  height: 17px;
  border-radius: 5px;
  background: rgba(59, 130, 246, 0.16);
  color: var(--accent-color, #3b82f6);
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.id-block-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
}
.id-block-tag {
  margin-left: auto;
  font-size: 10px;
  color: var(--text-muted, #64748b);
}

/* Block A 作品进度卡 */
.id-workcard {
  padding: 13px;
  border-radius: 12px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}
.id-work-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.id-work-genre {
  display: inline-block;
  margin-top: 6px;
  font-size: 10.5px;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.13);
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 2px 8px;
  border-radius: 99px;
}
.id-work-count {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin: 13px 0 7px;
}
.id-work-done {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary, #f8fafc);
  font-variant-numeric: tabular-nums;
}
.id-work-sep {
  font-size: 12px;
  color: var(--text-muted, #64748b);
}
.id-work-target {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  font-variant-numeric: tabular-nums;
}
.id-work-pct {
  margin-left: auto;
  font-size: 13px;
  font-weight: 700;
  color: #a78bfa;
}
.id-track {
  height: 8px;
  border-radius: 99px;
  background: var(--bg-tertiary, #334155);
  overflow: hidden;
}
.id-track i {
  display: block;
  height: 100%;
  width: 0;
  border-radius: 99px;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  transition: width 0.5s ease;
}
.id-work-empty {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  padding: 6px 0;
}
.id-work-empty b {
  color: var(--accent-color, #3b82f6);
}

/* Block B 迷你折线 */
.id-trend {
  padding: 12px 10px 8px;
  border-radius: 12px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}
.id-trend-svg {
  width: 100%;
  height: 96px;
  display: block;
}
.id-trend-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 0 2px;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}
.id-trend-foot b {
  color: var(--text-primary, #f8fafc);
  font-variant-numeric: tabular-nums;
}
.id-trend-foot .id-legend {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted, #64748b);
  font-size: 10px;
}
.id-legend i {
  width: 12px;
  height: 3px;
  border-radius: 2px;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  display: inline-block;
}

/* Block C 三项速览 */
.id-quick {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.id-qcard {
  padding: 11px 8px;
  border-radius: 11px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  text-align: center;
}
.id-qval {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary, #f8fafc);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.id-qval small {
  font-size: 11px;
  font-weight: 600;
  margin-left: 1px;
}
.id-qlabel {
  font-size: 10.5px;
  color: var(--text-muted, #64748b);
  margin-top: 5px;
  white-space: nowrap;
}
.id-qdelta {
  font-size: 10px;
  color: var(--success-color, #10b981);
  margin-top: 3px;
}

/* 空态 / 错误态 */
.id-state {
  padding: 16px 14px;
  border-radius: 12px;
  background: var(--bg-primary, #0f172a);
  border: 1px dashed var(--border-color, rgba(255, 255, 255, 0.12));
  text-align: center;
  color: var(--text-secondary, #94a3b8);
}
.id-state .id-state-ic {
  font-size: 26px;
  opacity: 0.7;
}
.id-state .id-state-t {
  font-size: 12.5px;
  line-height: 1.6;
  margin-top: 8px;
}
.id-full-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
  text-align: center;
}
.id-state-sub {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  display: inline-block;
  margin-top: 4px;
}
.id-retry {
  margin-top: 12px;
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.id-retry:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* 骨架屏 */
.id-sk {
  background: linear-gradient(
    90deg,
    var(--bg-tertiary, #334155) 25%,
    rgba(51, 65, 85, 0.55) 50%,
    var(--bg-tertiary, #334155) 75%
  );
  background-size: 200% 100%;
  animation: idshimmer 1.4s infinite;
  border-radius: 7px;
}
@keyframes idshimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.id-sk-card {
  padding: 13px;
  border-radius: 12px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  margin-bottom: 14px;
}
.id-sk-line {
  height: 11px;
  margin-bottom: 9px;
}
.id-sk-block {
  height: 96px;
  margin-top: 4px;
}

/* 抽屉底部 */
.id-foot {
  flex: none;
  padding: 12px 14px 14px;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  background: var(--bg-secondary, #1e293b);
}
.id-goto {
  width: 100%;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: var(--accent-gradient, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%));
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: filter 0.15s, transform 0.15s;
}
.id-goto:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}
.id-foot-hint {
  font-size: 10px;
  color: var(--text-muted, #64748b);
  text-align: center;
  margin-top: 8px;
}
</style>

