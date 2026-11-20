# 灵感兔（Rabbit AI）创作工作台与后台管理系统

基于 **Vue 3 + Vue Router 4 + Element Plus + Tailwind CSS v4** 前端与 **Python FastAPI + SQLite** 后端构建的本地优先多角色 AI 创作工作台与后台管理系统。支持接入 **DeepSeek**、**智谱 GLM** 与 **Google Gemini** 多款大模型，内置作品章节管理、角色卡/素材库防 OOC 注入、大纲 AI 拆章、整书导出、章节版本对比、全局分组搜索、字数进度看板，以及 **多用户全表权限隔离 + 创作数据可视化看板**。

---

## 核心功能特性

### 1. 多模型流式对话与深度思考
- **多模型自由切换**：内置 7 个可选模型，后端自动按模型标识分流至对应 OpenAI 兼容接口：
  - **DeepSeek**：`deepseek-chat`（DeepSeek V3 通用对话）、`deepseek-reasoner`（DeepSeek R1 深度思考推理）
  - **智谱 AI**：`glm-4-flash`（极速轻量）、`glm-4-plus`（高阶旗舰）
  - **Google Gemini**：`gemini-3.8-flash`（1M 超长上下文）、`gemini-3.1-pro-preview`（深度推理旗舰）、`gemini-3.5-flash-lite`（极速轻量）
- **SSE 实时流式响应**：支持打字机流式输出、随时中止生成、重新生成回复、单条/截断删除消息，以及首轮对话后台异步 **AI 智能自动标题**（M4a）。
- **思维链与富文本渲染**：支持推理过程（`reasoning_content`）折叠展示，以及基于 `markdown-it` + `highlight.js` 的 Markdown 排版、代码高亮与一键复制。

### 2. 创作工作台（作品 / 章节 / 角色卡 / 素材库 / 版本对比）
- **作品与正文章节管理（M1）**：支持作品设定（体裁、简介、大纲、目标字数）与章节正文 CRUD、跨章节无缝承接（自动提取上一章末尾 800 字注入上下文）及 **字数进度看板**（M4c，支持展开各章字数分布柱状条）。
- **角色卡与素材库（M2）**：按作品归属管理角色卡（启用角色自动注入上下文防 OOC）与分类素材库（灵感/金句/参考/设定片段），支持一键插入聊天输入框。
- **创作专用工具（M3）**：
  - **内置 5 套体裁大纲模板**（三幕式小说、章节剧、悬疑推理、散文随笔、营销文案）；
  - **AI 一键拆章**：基于大纲与启用角色生成可编辑章节规划，审核后幂等批量入库；
  - **整书单文件导出**：按封面 → 设定 → 启用人物表 → 章节正文顺序导出 Markdown 全书；
  - **章节多版本历史与并排 Diff 对比**：单章自动保留最近 20 个快照，支持随时回滚。
- **全局分组搜索（M4b）**：单次搜索覆盖 **会话 / 消息 / 角色卡 / 素材库 / 章节正文** 5 类数据，关键词高亮、分组折叠并支持点击一键跳转。
- **Markdown 提示词文件（`.md`）与本地目录同步**：支持全局/作品/会话三级作用域 `.md` 提示词注入，以及作品与章节自动同步至本地文件夹（默认 `Documents/RabbitWorks`）。

### 3. 后台管理系统（D 用户权限隔离 + C 创作数据看板）
- **双 Tab 路由架构**：顶栏提供 **✍️ 创作工作台（`/workspace`）** 与 **📊 后台管理（`/admin/dashboard`、`/admin/monitor`、`/admin/users`）** 一键切换，工作台状态通过 `<keep-alive>` 无损保留。
- **C 创作数据看板**：
  - 6 张核心指标概览卡（作品数 / 章节数 / 总字数 / 角色卡 / 素材数 / 会话数 + 近期增量）；
  - 写作趋势 SVG 渐变折线面积图（支持「按日 / 按周」切换与悬停明细）；
  - 体裁分布 SVG 环形图 + 各作品完成率进度条；
  - 管理员默认查看全站汇总（可切「仅我的」），普通成员强制仅查看个人数据。
- **🩺 运营监控中心（Token 管理与调用健康度）**：
  - **4 核心概览卡**：调用总数、成功/失败量与失败率、总 Token 消耗量（输入 + 输出）、单次平均耗时；
  - **调用趋势双线图**：SVG 动态双线折线图（总调用次数 + 成功线），支持近 7 日与近 30 日切换；
  - **模型分布占比**：展示各大模型调用占比进度条与消耗统计；
  - **调用明细流水**：支持按调用状态（success/error/aborted）与模型筛选、分页、状态色标及错误原因悬浮提示；
  - **双重视角安全隔离**：管理员支持「全站 / 仅我」视角无缝切换，普通成员强制隔离仅查个人流水（AC-1 / AC-2）。
- **D 用户与权限全表隔离**：
  - **单人免登录兼容**：默认单人本地免登录（自动以默认管理员 `admin` 进入，初始密码 `admin123`），不降低单人使用体验；管理员可随时开启「多用户鉴权模式」。
  - **全表 `user_id` 隔离**：8 张业务表（`works / sessions / messages / prompt_files / chapters / characters / materials / chapter_versions`）全表加 `user_id` 与索引，`bot_settings` 按用户独立隔离。
  - **完整账号管控**：PBKDF2-HMAC-SHA256 随机加盐哈希 + HMAC-SHA256 签名 Token（7 天有效 + 登出黑名单），支持新建用户、改角色、禁用/启用、重置密码、修改自己密码，以及删除用户二次确认（支持数据「转移给管理员」或「一并删除」，删除前自动备份数据库）。

### 4. 安全加固与个性化主题
- **P0 安全加固**：零硬编码 API Key、CORS 白名单限制、服务启动自动创建 `chat_memory.db.bak` 备份。
- **自由调节界面配色**：内置 6 套预设主题、8 种推荐强调色与自定义取色器，持久化保存。

---

## 项目目录结构

```text
rabbit/
├── backend/                              # Python FastAPI 模块化后端
│   ├── app/
│   │   ├── config.py                     # 环境变量、模型列表、体裁模板与数据库路径配置
│   │   ├── models.py                     # Pydantic 请求与响应数据模型（含鉴权/用户模型）
│   │   ├── core/                         # 核心基础设施与通用服务
│   │   │   ├── database.py               # SQLite 连接管理、全套 DDL 表结构、自动备份与迁移
│   │   │   ├── auth.py                   # PBKDF2 密码哈希、HMAC 签名 Token 与 FastAPI 鉴权依赖
│   │   │   ├── llm.py                    # DeepSeek / 智谱 / Gemini 异步客户端分流
│   │   │   ├── context.py                # 上下文组装服务 (滑动窗口、提示词拼接、角色卡与前情承接注入)
│   │   │   ├── search.py                 # 全局多表聚合搜索服务 (覆盖作品/章节/角色/素材/会话)
│   │   │   ├── outline.py                # M3b AI 拆章 Prompt 与三级兜底解析器
│   │   │   ├── title.py                  # M4a 异步智能短标题生成器
│   │   │   ├── sync.py                   # 作品与章节本地文件夹同步管理器
│   │   │   └── memory.py                 # 统一门面 (Facade: memory_manager)，聚合所有 Store
│   │   ├── stores/                       # 领域数据存储层（单一职责，按业务实体独立解耦）
│   │   │   ├── base.py                   # 基础 Store（连接池管理、Row 映射、多租户 user_id 解析）
│   │   │   ├── works.py                  # 作品管理 (Works CRUD, 会话-作品关联, 跨章无缝承接计算)
│   │   │   ├── chapters.py               # 章节与版本快照 (Chapters CRUD, 批量拆章, 差异快照)
│   │   │   ├── characters.py             # 角色卡设定库 (Characters CRUD, 结构化人设防 OOC)
│   │   │   ├── materials.py              # 素材与灵感库 (Materials CRUD, 按类型/标签检索)
│   │   │   ├── prompts.py                # Markdown 提示词文件 (PromptFiles CRUD, 全局/作品/章节作用域)
│   │   │   ├── sessions.py               # 对话与消息存储 (Sessions, Messages, 助手人设, 导入导出)
│   │   │   ├── users.py                  # 用户与系统设置 (Users CRUD, 多用户开关, 归属转移)
│   │   │   ├── stats.py                  # 数据看板聚合统计 (概览卡/7日趋势/完成率/体裁分布)
│   │   │   └── monitor.py                # 运营监控与 Token 流水 (调用日志/4卡指标/双线趋势/模型占比)
│   │   ├── routers/                      # 模块化 API 路由
│   │   │   ├── auth.py                   # 登录/登出/改密、多用户开关与管理员用户 CRUD (/api/auth, /api/admin)
│   │   │   ├── stats.py                  # 创作数据看板统计接口 (/api/stats/*)
│   │   │   ├── monitor.py                # 运营监控与 Token 管理接口 (/api/monitor/*)
│   │   │   ├── system.py                 # 健康检查、模型列表、体裁模板与个人人设 (/api/health, /api/settings)
│   │   │   ├── works.py                  # 作品 CRUD 与作品会话 (/api/works)
│   │   │   ├── chapters.py               # 正文章节与历史版本 CRUD (/api/chapters)
│   │   │   ├── characters.py             # 角色卡 CRUD (/api/works/{id}/characters)
│   │   │   ├── materials.py              # 素材库 CRUD (/api/works/{id}/materials)
│   │   │   ├── export.py                 # 整书单文件 Markdown 导出 (/api/works/{id}/export)
│   │   │   ├── outline.py                # AI 一键拆章与批量入库 (/api/works/{id}/split-outline)
│   │   │   ├── sessions.py               # 会话/消息管理、导入导出、全局搜索与自动标题 (/api/sessions, /api/search/global)
│   │   │   ├── prompt_files.py           # Markdown 提示词文件管理 (/api/prompt-files)
│   │   │   ├── sync.py                   # 本地目录同步接口 (/api/sync)
│   │   │   └── chat.py                   # SSE 流式对话核心接口 (/api/chat)
│   │   └── utils/
│   │       ├── formatters.py             # 会话 Markdown / JSON 格式化与解析工具
│   │       └── book_export.py            # 整书 Markdown 组装与文件名安全清洗工具
│   ├── main.py                           # FastAPI 应用入口（lifespan 自动备份 + CORS 白名单 + 路由挂载）
│   ├── requirements.txt                  # 后端依赖
│   ├── test_api.py                       # DeepSeek API 连通性测试脚本
│   ├── .env                              # 本地环境变量配置 (不入库)
│   └── .env.example                      # 环境变量配置示例
├── frontend/                             # Vue 3 + Vue Router 4 + Vite 模块化前端
│   ├── src/
│   │   ├── router/
│   │   │   └── index.js                  # 前端路由定义（/workspace, /admin/dashboard, /admin/monitor, /admin/users）
│   │   ├── stores/
│   │   │   └── auth.js                   # 全局鉴权状态 Store（用户信息、多用户开关、登录/登出状态同步）
│   │   ├── utils/
│   │   │   ├── request.js                # 统一 HTTP 客户端（请求拦截器/响应拦截器/超时控制/401 自动拦截）
│   │   │   ├── fileReader.js             # 本地 .md / .markdown / .txt 文件读取工具
│   │   │   └── markdown.js               # markdown-it 与 highlight.js 渲染工具
│   │   ├── api/                          # 按领域拆分的接口层（统一基于 utils/request.js）
│   │   │   ├── index.js                  # 聚合导出入口
│   │   │   ├── auth.js                   # 认证与用户管理 API
│   │   │   ├── stats.js                  # 创作数据看板 API
│   │   │   ├── monitor.js                # 运营监控中心 API
│   │   │   ├── system.js                 # 健康检查、模型、人设与同步 API
│   │   │   ├── works.js                  # 作品、章节、版本、角色、素材、拆章与导出 API
│   │   │   └── chat.js                   # 会话、消息、全局搜索、提示词与 SSE 流式对话 API
│   │   ├── views/                        # 路由级页面视图（按业务领域文件夹划分）
│   │   │   ├── admin/                    # 后台管理页面集
│   │   │   │   ├── AdminLayout.vue       # 后台左侧二级子导航与路由出口
│   │   │   │   ├── DashboardView.vue     # 创作数据看板页面
│   │   │   │   ├── MonitorView.vue       # 运营监控中心页面
│   │   │   │   └── UserAdminView.vue     # 用户管理与权限隔离页面
│   │   │   └── workspace/                # 创作工作台页面集
│   │   │       └── WorkspaceView.vue     # 创作工作台主页面（双栏写作、对话与抽屉）
│   │   ├── components/                   # 可复用组件（按类型分层规整）
│   │   │   ├── common/                   # 全局跨模块基础组件
│   │   │   │   ├── BaseChart.vue         # ECharts 响应式图表基类（统一管理 init/resize/dispose）
│   │   │   │   ├── GlobalTopbar.vue      # 全局一级顶栏（双 Tab 路由切换 + 身份菜单）
│   │   │   │   ├── ThemeSettingsPopover.vue # 主题配色面板浮窗
│   │   │   │   └── LoginView.vue         # 登录与认证弹窗
│   │   │   ├── workspace/                # 创作工作台专用组件
│   │   │   │   ├── AppHeader.vue         # 工作台二级工具栏（模型选择、导入导出、主题调节）
│   │   │   │   ├── AppSidebar.vue        # 左侧作品/章节/对话树与全局分组搜索
│   │   │   │   ├── CreativeModeBar.vue   # 创作模式提示条（跨章无缝承接浮窗 + 快捷入口）
│   │   │   │   ├── WordProgressBar.vue   # 作品字数进度看板与章节分布抽屉
│   │   │   │   ├── ChatMessageItem.vue   # 单条消息卡片（思维链折叠、代码高亮、添加到章节）
│   │   │   │   ├── ChatInput.vue         # 底部输入区（.md 提示词上传与快速启停、流式发送）
│   │   │   │   └── InsightDrawer.vue     # 灵感兔工作台洞察抽屉
│   │   │   ├── admin/                    # 后台各页面拆离的细粒度单职责组件
│   │   │   │   ├── MonitorStatCards.vue  # 运营监控 4 核心指标概览卡
│   │   │   │   ├── MonitorTrendChart.vue # 运营监控双线趋势图（基于 ECharts）
│   │   │   │   ├── MonitorModelDistribution.vue # 模型调用占比分布条
│   │   │   │   ├── MonitorCallTable.vue  # 调用流水表格与分页器（基于 Element Plus）
│   │   │   │   ├── DashboardStatCards.vue# 创作看板 6 指标卡
│   │   │   │   ├── DashboardTrendChart.vue# 写作趋势折线图（基于 ECharts）
│   │   │   │   ├── DashboardGenreChart.vue# 体裁分布环形图（基于 ECharts）
│   │   │   │   ├── DashboardWorkProgress.vue # 作品字数完成率看板
│   │   │   │   ├── UserFormDialog.vue    # 新建用户表单弹窗（基于 Element Plus）
│   │   │   │   ├── UserDeleteDialog.vue  # 删除用户二次确认与数据转移弹窗
│   │   │   │   └── UserResetPwdDialog.vue# 重置用户密码弹窗
│   │   │   └── modals/                   # 业务弹窗组件群
│   │   │       ├── CharacterPanel.vue    # M2a 角色卡管理弹窗
│   │   │       ├── MaterialPanel.vue     # M2b 素材库管理弹窗
│   │   │       ├── BookExportModal.vue   # M3a 整书导出预览弹窗
│   │   │       ├── OutlineSplitModal.vue # M3b AI 大纲一键拆章审核弹窗
│   │   │       ├── ChapterVersionModal.vue # M3c 章节版本历史与并排 Diff 弹窗
│   │   │       ├── PromptFileModal.vue   # Markdown 提示词预览、编辑与作用域弹窗
│   │   │       ├── AddToChapterModal.vue # 对话内容添加到作品章节弹窗
│   │   │       ├── ChapterEditorModal.vue# 章节正文阅读与编辑弹窗
│   │   │       ├── LocalSyncModal.vue    # 本地目录同步配置弹窗
│   │   │       └── ChangePasswordModal.vue # 修改自己密码弹窗
│   │   ├── composables/useTheme.js       # 主题状态管理与 CSS 变量注入
│   │   ├── plugins/element.js            # Element Plus 与图标按需注册
│   │   ├── App.vue                       # 极简根壳组件（顶栏 + router-view + 全局弹窗）
│   │   ├── main.js                       # 应用入口（注册 Element Plus 与 Vue Router）
│   │   └── style.css
│   ├── vite.config.js                    # Vite 配置 (端口 5173，代理 /api -> http://127.0.0.1:8000)
│   └── package.json
├── docs/                                 # 设计文档、交互原型与架构草图（按演进阶段分 8 模块规整）
│   ├── README.md                         # 文档导航总览与速查地图
│   ├── 00_全局规划与路线图/               # 全局需求分析与路线图复盘
│   ├── 01_M0-M1_基础创作工作台/          # 基础对话流式与作品章节树
│   ├── 02_M2_角色卡与素材库/             # 角色卡设定与素材灵感知识库
│   ├── 03_M3_创作专用功能/               # 整书导出、AI拆章与版本Diff
│   ├── 04_M4_体验打磨阶段/               # 智能标题、全局搜索与字数进度条
│   ├── 05_后台管理系统/                  # 用户权限隔离与创作数据看板
│   ├── 06_合一工作台_洞察抽屉/           # 右侧折叠洞察抽屉
│   └── 07_运营监控中心/                  # API调用统计与Token监控
├── dev_dashboard.html                    # 网页版开发控制台前端页面
├── dev_dashboard.py                      # 开发控制台轻量调度服务 (端口 3000 + SSE 日志流)
├── 开发助手_网页版.bat                   # 一键启动网页版开发控制台
├── run_backend.bat                       # 后端直接启动脚本 (端口 8000)
├── run_frontend.bat                      # 前端直接启动脚本 (端口 5173)
└── README.md
```

---

## 快速配置与运行

### 1. 安装依赖（首次运行）

**后端环境：**
```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

**前端环境：**
```bash
cd frontend
npm install
```

### 2. 配置模型 API Key 与可选安全项
参考 [backend/.env.example](file:///d:/python/my_ai_project/rabbit/backend/.env.example)，在 `backend/.env` 中配置模型厂商 Key（至少配置其中任意一组即可使用对应模型）：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-chat

# 智谱 AI (GLM) API 配置
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Google Gemini API 配置 (OpenAI 兼容端点)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_DEFAULT_MODEL=gemini-3.8-flash

# 后端服务端口与可选鉴权配置
PORT=8000
# ADMIN_DEFAULT_PASSWORD=admin123
# AUTH_SECRET_KEY=your_random_hex_secret
# CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> 默认单人免登录模式会自动初始化管理员账号 `admin`（默认密码 `admin123`），存量创作数据会自动迁移归属该账号。开启多用户模式前建议通过右上角「修改我的密码」修改默认密码。

### 3. 启动服务

- **方式一：网页版开发控制台（推荐）**
  双击根目录下的 **`开发助手_网页版.bat`**，在浏览器打开 **`http://localhost:3000`** 一键启停前后端服务并查看实时日志。
- **方式二：使用独立批处理脚本**
  - 启动后端：双击 **`run_backend.bat`**（监听 `http://localhost:8000`，接口文档 `http://localhost:8000/docs`）
  - 启动前端：双击 **`run_frontend.bat`**（访问 `http://localhost:5173`）
- **方式三：手动命令行启动**
  ```bash
  # 终端 1：启动后端
  cd backend && .venv\Scripts\python.exe main.py

  # 终端 2：启动前端
  cd frontend && npm run dev
  ```

---

## 提交 Git 代码规范

- `feat:` 新的特性
- `fix:` 修复问题
- `docs:` 文档变更
- `style:` 代码格式（不影响代码运行的变动）
- `refactor:` 重构（既不是新增 feature，也不是修复 bug）
- `perf:` 性能优化
- `test:` 增加测试
- `chore:` 构建过程或辅助工具的变动
- `revert:` 回退
- `build:` 打包
- `conflict:` 修改冲突
- `stash:` 暂存文件
- `delete:` 删除文件
- `ci:` 对 CI 配置文件和脚本的更改
