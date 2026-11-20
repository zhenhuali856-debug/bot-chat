# 灵感兔（Rabbit AI）前端工程规范与架构指南

本项目基于 **Vue 3（`<script setup>` Composition API）+ Vite + Vue Router 4 + Element Plus + ECharts + Tailwind CSS v4** 构建。为避免后期功能无序膨胀、巨石组件难以维护的问题，全体开发与维护工作必须严格遵循本规范。

---

## 一、 目录划分规范与职责边界

前端代码统一归置于 `frontend/src/`，按**关注点分离（Separation of Concerns）**与**业务领域模块化**组织，严禁在根目录下扁平堆砌文件。

```text
frontend/src/
├── api/                          # 【数据请求层】按业务领域拆分的 API 接口，统一复用 utils/request.js
│   ├── auth.js                   # 登录、登出、改密与管理员用户 CRUD
│   ├── chat.js                   # 会话、消息、全局搜索、提示词与 SSE 对话
│   ├── monitor.js                # 运营监控、Token 消耗统计与调用流水
│   ├── stats.js                  # 创作数据看板聚合接口
│   ├── system.js                 # 系统健康、模型、人设与同步接口
│   ├── works.js                  # 作品、正文章节、版本、角色卡与素材库
│   └── index.js                  # 统一聚合导出入口
│
├── views/                        # 【页面路由视图层】只放顶层页面组件，按业务模块划分子文件夹
│   ├── admin/                    # 后台管理模块页面
│   │   ├── AdminLayout.vue       # 后台左侧子导航布局壳与子路由出口
│   │   ├── DashboardView.vue     # 创作数据看板主页面（调度图表与卡片子组件）
│   │   ├── MonitorView.vue       # 运营监控中心主页面（调度 Token、趋势与流水子组件）
│   │   └── UserAdminView.vue     # 用户与权限管理主页面（调度用户表格与弹窗）
│   └── workspace/                # 创作工作台模块页面
│       └── WorkspaceView.vue     # 创作工作台主页面（双栏写作、对话与抽屉）
│
├── components/                   # 【组件库】可复用组件，禁止全部直接散落在根目录，按类型分目录
│   ├── common/                   # 全局通用跨模块组件
│   │   ├── BaseChart.vue         # ECharts 响应式封装基类（统一 init / resize / dispose）
│   │   ├── GlobalTopbar.vue      # 全局一级顶栏（Tab 路由切换 + 用户身份下拉）
│   │   ├── ThemeSettingsPopover.vue # 全局主题调节浮窗
│   │   └── LoginModal.vue        # 登录与认证弹窗
│   ├── workspace/                # 创作工作台专属功能组件
│   │   ├── AppHeader.vue         # 工作台二级工具栏（模型切换、导入导出）
│   │   ├── AppSidebar.vue        # 作品/章节树及全局分组搜索
│   │   ├── ChatInput.vue         # 底部提示词上传与流式对话输入框
│   │   ├── ChatMessageItem.vue   # 单条消息渲染卡片（思维链、Markdown 高亮）
│   │   ├── CreativeModeBar.vue   # 创作模式浮条（跨章无缝承接计算）
│   │   ├── WordProgressBar.vue   # 字数进度看板与章节字数分布抽屉
│   │   └── InsightDrawer.vue     # 灵感兔工作台洞察抽屉
│   ├── admin/                    # 后台管理细粒度解耦子组件（按视图内功能区拆解）
│   │   ├── MonitorStatCards.vue  # 运营监控 4 核心指标概览卡
│   │   ├── MonitorTrendChart.vue # 运营监控调用与成功双线趋势图（基于 ECharts）
│   │   ├── MonitorModelDistribution.vue # 模型调用占比分布条
│   │   ├── MonitorCallTable.vue  # 调用明细流水表格与分页器（基于 Element Plus）
│   │   ├── DashboardStatCards.vue # 创作看板 6 指标卡
│   │   ├── DashboardTrendChart.vue# 写作趋势折线图（基于 ECharts）
│   │   ├── DashboardGenreChart.vue# 体裁分布环形图（基于 ECharts）
│   │   ├── DashboardWorkProgress.vue # 作品字数完成率看板
│   │   ├── UserFormDialog.vue    # 新增用户表单弹窗（基于 el-dialog + el-form）
│   │   ├── UserDeleteDialog.vue  # 删除用户二次确认与数据转移弹窗
│   │   └── UserResetPwdDialog.vue# 重置用户密码弹窗
│   └── modals/                   # 业务独立弹窗组件群
│       ├── CharacterPanel.vue    # 角色卡设定弹窗
│       ├── MaterialPanel.vue     # 素材灵感库弹窗
│       ├── BookExportModal.vue   # 整书单文件导出预览弹窗
│       ├── OutlineSplitModal.vue # AI 一键大纲拆章弹窗
│       ├── ChapterVersionModal.vue # 章节版本历史与 Diff 对比弹窗
│       ├── ChapterEditorModal.vue# 章节快速阅读与编辑弹窗
│       ├── PromptFileModal.vue   # Markdown 提示词文件管理弹窗
│       ├── AddToChapterModal.vue # 对话提取入库章节弹窗
│       ├── LocalSyncModal.vue    # 本地文件目录同步弹窗
│       └── ChangePasswordModal.vue # 用户修改密码弹窗
│
├── composables/                  # 组合式函数（如 useTheme.js）
├── plugins/                      # 三方库接入配置（如 element.js）
├── router/                       # 路由定义与导航权限守卫（index.js）
├── stores/                       # Pinia / 响应式状态管理（如 auth.js）
├── utils/                        # 请求拦截器（request.js）、Markdown 渲染工具（markdown.js）
├── App.vue                       # 极简顶层应用壳（仅挂载顶栏、router-view 与全局弹窗）
└── main.js                       # Vue 应用初始化主入口
```

---

## 二、 组件拆解规范与单一职责原则

### 1. 杜绝巨石组件（Anti-Monolith）
- **单文件代码上限**：常规组件代码行数建议控制在 **300 行以内**，复杂综合页面不得超过 **500 行**。
- **页面视图（View）职责定位**：
  - 页面视图仅作为**指挥调度中心（Coordinator）**：负责监听路由参数、调度 API 获取数据、分发 Props 给子组件，并监听子组件 Emits 事件。
  - **禁止在 View 中直接书写长达数百行的复杂图表渲染、长表单校验、密集表格模板**。必须将其拆分为 `components/` 下对应模块的子组件。
- **子组件（Sub-Component）职责定位**：
  - 每个子组件专注于单一功能区域（例如：指标卡片 `StatCards`、趋势折线图 `TrendChart`、明细流水表 `CallTable`、表单弹窗 `FormDialog`）。
  - 通过 `defineProps` 接收数据，通过 `defineEmits` 向上传递变更，保持独立自闭环。

### 2. 弹窗（Dialog / Modal）抽取规范
- 所有的表单新建、编辑、详情确认弹窗，必须封装在独立的 `.vue` 文件中，通过 `v-model:visible` 控制显示。
- 严禁在主页面内直接嵌入多套模态弹窗的 HTML 骨架和样式，防止页面纵向膨胀。

---

## 三、 组件库与第三方依赖使用准则

**核心原则：Element Plus 与 ECharts 有的成熟能力，一律优先使用，坚决不重复造轮子，严禁手写繁琐无意义的原生 CSS 与原生 DOM 操作。**

### 1. Element Plus 使用规范
| 功能场景 | 推荐组件 | 严禁做法 |
| :--- | :--- | :--- |
| **数据列表展示** | `<el-table>`、`<el-table-column>` | ❌ 严禁手写原生 `<table>`、`<tr>`、`<td>` 与边框 hover 样式。 |
| **分页控制** | `<el-pagination background layout="prev, pager, next, total" />` | ❌ 严禁手写上一页/下一页按钮及页码计算器。 |
| **表单与输入框** | `<el-form>`、`<el-form-item>`、`<el-input>`、`<el-select>`、`<el-switch>` | ❌ 严禁手写原生 `<input>`、`<select>` 及繁重的聚焦边框伪类。 |
| **模态弹窗** | `<el-dialog>`、`<el-drawer>` | ❌ 严禁手写 fixed 遮罩蒙层 `inset: 0` 和原生浮层。 |
| **状态标签与悬浮提示** | `<el-tag>`、`<el-tooltip>` | ❌ 严禁手写带背景颜色的自定义圆角 span 及 tooltip 悬浮层。 |
| **全局交互反馈** | `ElMessage.success(...)`、`ElMessageBox.confirm(...)` | ❌ 严禁手写自定义 toast DOM 或使用浏览器原生 `alert()`。 |

### 2. ECharts 数据图表规范
- **禁止手算 SVG 路径**：严禁在业务组件中手写 `<svg>` 并通过三角函数、极坐标或数组遍历计算折线点、平滑曲线切线、多边形面积 `d="M ... L ... Z"` 或环形饼图角度。此类写法极易出错、无交互 tooltip、且不可维护。
- **统一使用 `BaseChart.vue` 基类**：
  - 所有图表统一引用 `import BaseChart from '@/components/common/BaseChart.vue'`。
  - `BaseChart` 自动封装了 `ResizeObserver`，窗口大小改变或左侧侧边栏折叠展开时自动调用 `chart.resize()`。
  - 组件销毁时自动调用 `dispose()`，杜绝内存泄漏。
  - 示例用法：
    ```vue
    <script setup>
    import { computed } from 'vue'
    import BaseChart from '@/components/common/BaseChart.vue'

    const chartOptions = computed(() => ({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['周一', '周二', '周三'] },
      yAxis: { type: 'value' },
      series: [{ type: 'line', smooth: true, data: [120, 200, 150] }]
    }))
    </script>

    <template>
      <BaseChart :options="chartOptions" height="240px" />
    </template>
    ```

---

## 四、 样式与主题管理规范

1. **项目设计变量优先**：
   - 颜色与边框一律使用设计变量，确保白天与暗色主题自动无缝切换：
     - 背景色：`var(--bg-primary)`、`var(--bg-secondary)`、`var(--bg-tertiary)`
     - 文本色：`var(--text-primary)`、`var(--text-secondary)`、`var(--text-muted)`
     - 强调色：`var(--accent-color)`、`var(--accent-gradient)`
     - 状态色：`var(--success-color)`、`var(--warning-color)`、`var(--danger-color)`
     - 边框色：`var(--border-color)`
   - 严禁在样式中硬编码 `#1e293b`、`#ffffff` 等绝对色彩。
2. **样式作用域（Scoped）**：
   - 所有组件中的 `<style>` 标签必须附带 `scoped` 属性，防止样式全局污染。
   - 需要覆盖 Element Plus 内置样式时，使用 `:deep(.el-table)` 等深度选择器。

---

## 五、 后续功能迭代 Checklist（自查清单）

在新增或重构任何功能前，开发者必须对照以下问题自检：
- [ ] **是否创建在正确的文件夹中？**（路由页面归入 `views/<模块>/`，公共组件归入 `components/<类型>/`）
- [ ] **是否单个文件过长？**（超过 300 行必须检视是否包含了图表、表格或弹窗，并将其抽离为子组件）
- [ ] **图表是否使用了 ECharts？**（严禁手算 SVG 几何坐标，一律使用 `BaseChart.vue`）
- [ ] **表格和表单是否使用了 Element Plus？**（列表用 `el-table`、分页用 `el-pagination`、表单用 `el-form`）
- [ ] **是否通过接口层调用后端？**（严禁在组件内直接写 `fetch` 或原生 `axios`，一律在 `src/api/<模块>.js` 中定义接口）
- [ ] **代码构建是否通过？**（修改完毕后，本地必须执行 `npm run build` 确保 0 报错、0 警告）
