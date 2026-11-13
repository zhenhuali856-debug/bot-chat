# Rabbit AI 创作工作台与多模型对话系统

基于 **Vue 3 + Element Plus + Tailwind CSS v4** 前端与 **Python FastAPI + SQLite** 后端构建的 AI 创作工作台与流式对话系统，支持接入 **DeepSeek**、**智谱 GLM** 与 **Google Gemini** 多款大模型，并内置作品章节管理、Markdown 提示词注入、本地目录同步与多主题切换能力。

---

## 核心功能特性

### 1. 多模型流式对话与深度思考
- **多模型自由切换**：内置 7 个可选模型，后端自动按模型标识分流至对应 OpenAI 兼容接口：
  - **DeepSeek**：`deepseek-chat`（DeepSeek V3 通用对话）、`deepseek-reasoner`（DeepSeek R1 深度思考推理）
  - **智谱 AI**：`glm-4-flash`（极速轻量）、`glm-4-plus`（高阶旗舰）
  - **Google Gemini**：`gemini-3.8-flash`（1M 超长上下文）、`gemini-3.1-pro-preview`（深度推理旗舰）、`gemini-3.5-flash-lite`（极速轻量）
- **SSE 实时流式响应**：支持打字机流式输出、随时中止生成、重新生成回复、单条或截断删除消息。
- **思维链与富文本渲染**：支持推理过程（`reasoning_content`）折叠展示，以及基于 `markdown-it` + `highlight.js` 的 Markdown 排版、代码高亮与一键复制。

### 2. 创作工作台（作品 / 章节 / 会话三级管理）
- **作品管理（Works）**：支持创建、编辑与删除作品，配置作品名称、体裁、简介、故事大纲、目标字数与状态；删除作品时所属对话会自动移回「未归类灵感」而保留内容。
- **作品正文章节（Chapters）**：
  - 支持在消息操作栏一键点击添加到章节，通过弹窗新建章节或追加/覆盖到已有章节；
  - 支持章节正文弹窗阅读与编辑、自动字数统计，以及在侧边栏对「📄 作品章节」与「💬 创作对话」分组进行折叠/展开。
- **多轮记忆与历史管理**：基于 SQLite（`backend/chat_memory.db`）持久化会话与消息，支持滑动窗口上下文（默认保留最近 10 轮 + 置顶人设），支持会话新建、重命名、绑定作品、清空记忆及 `.md` / `.json` 导入导出。

### 3. Markdown 提示词文件（`.md`）读取与注入
- 支持在输入框工具栏点击选择或拖拽上传 `.md` / `.markdown` / `.txt` 提示词文件，前端读取解析后保存至后端。
- 支持提示词作用域管理（全局 `global` / 作品 `work` / 本会话 `session`）、独立启停开关、内容预览与在线编辑；开启状态的提示词会在发送对话时自动注入模型上下文。

### 4. 本地电脑目录同步
- 支持自定义本地同步文件夹路径（支持调起系统原生文件夹选择框），默认目录为用户文档下的 `RabbitWorks`。
- 支持导出格式选择（`.md` / `.txt`），可按作品目录结构同步作品设定与各章节正文，支持手动立即同步、章节/作品变更后自动同步，以及一键在资源管理器中打开同步目录。

### 5. 个性化主题与助手设定
- **自由调节界面配色**：内置 6 套预设主题（深邃暗黑、清新素白、星际深蓝、极光墨绿、赛博霓紫、日落暖橙）、8 种推荐强调色以及自定义取色器，支持明暗模式自适应与持久化保存。
- **全局助手配置**：支持自定义助手昵称（默认「灵感兔」）与全局默认人设 Prompt。

---

## 项目目录结构

```text
rabbit/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── config.py                 # 环境变量、模型列表与数据库路径配置
│   │   ├── models.py                 # Pydantic 请求与响应数据模型
│   │   ├── core/
│   │   │   ├── llm.py                # DeepSeek / 智谱 / Gemini 异步客户端分流
│   │   │   ├── memory.py             # SQLite 持久化与上下文窗口管理
│   │   │   └── sync.py               # 作品与章节本地文件夹同步管理器
│   │   ├── routers/
│   │   │   ├── system.py             # 健康检查、模型列表与全局助手设置 (/api/health, /api/models, /api/settings)
│   │   │   ├── works.py              # 作品 CRUD 与作品关联会话 (/api/works)
│   │   │   ├── chapters.py           # 正文章节 CRUD (/api/chapters, /api/works/{id}/chapters)
│   │   │   ├── sessions.py           # 会话、消息管理与导入导出 (/api/sessions)
│   │   │   ├── prompt_files.py       # Markdown 提示词文件管理 (/api/prompt-files)
│   │   │   ├── sync.py               # 本地同步配置、浏览目录与执行同步 (/api/sync)
│   │   │   └── chat.py               # SSE 流式对话核心接口 (/api/chat)
│   │   └── utils/
│   │       └── formatters.py         # 会话 Markdown / JSON 格式化与解析工具
│   ├── main.py                       # FastAPI 应用入口
│   ├── requirements.txt              # 后端依赖 (fastapi, uvicorn, openai, python-dotenv, pydantic)
│   ├── test_api.py                   # DeepSeek API 连通性测试脚本
│   ├── .env                          # 本地环境变量配置 (需自行配置 API Key)
│   └── .env.example                  # 环境变量配置示例
├── frontend/                         # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── api/index.js              # 模块化后端 HTTP 请求封装
│   │   ├── components/
│   │   │   ├── AppHeader.vue         # 顶部栏 (模型选择、导入导出、主题调节、清空对话)
│   │   │   ├── AppSidebar.vue        # 左侧边栏 (作品/章节/对话树、未归类灵感、本地同步入口)
│   │   │   ├── ChatMessageItem.vue   # 单条消息卡片 (思维链折叠、代码高亮、添加到章节、复制/重试)
│   │   │   ├── ChatInput.vue         # 底部输入区 (.md 提示词上传与快速启停、流式发送/中止)
│   │   │   ├── PromptFileModal.vue   # Markdown 提示词文件预览、编辑与作用域设置弹窗
│   │   │   ├── AddToChapterModal.vue # 对话内容添加到作品章节弹窗
│   │   │   ├── ChapterEditorModal.vue# 章节正文阅读与编辑弹窗
│   │   │   ├── LocalSyncModal.vue    # 本地电脑同步目录与自动同步配置弹窗
│   │   │   └── ThemeSettingsPopover.vue # 主题预设与自定义配色面板
│   │   ├── composables/useTheme.js   # 主题状态管理与 CSS 变量注入
│   │   ├── plugins/element.js        # Element Plus 与图标按需注册
│   │   ├── utils/
│   │   │   ├── fileReader.js         # 本地 .md / .markdown / .txt 文件读取工具
│   │   │   └── markdown.js           # markdown-it 与 highlight.js 渲染工具
│   │   ├── App.vue                   # 主工作台布局与状态编排
│   │   ├── main.js
│   │   └── style.css
│   ├── vite.config.js                # Vite 配置 (端口 5173，代理 /api -> http://127.0.0.1:8000)
│   └── package.json
├── docs/                             # 设计文档与界面原型草图
├── dev_dashboard.html                # 网页版开发控制台前端页面
├── dev_dashboard.py                  # 开发控制台轻量调度服务 (端口 3000 + SSE 日志流)
├── 开发助手_网页版.bat               # 一键启动网页版开发控制台
├── run_backend.bat                   # 后端直接启动脚本 (端口 8000)
├── run_frontend.bat                  # 前端直接启动脚本 (端口 5173)
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

### 2. 配置模型 API Key
参考 [backend/.env.example](file:///d:/python/my_ai_project/rabbit/backend/.env.example)，在 `backend/.env` 中配置你需要使用的模型厂商 Key（至少配置其中任意一组即可使用对应模型）：

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

# 后端服务端口
PORT=8000
```

> 程序也会读取系统环境变量中的对应 Key。

### 3. 可选：测试 DeepSeek API 连通性
在项目根目录下运行测试脚本：
```bash
backend\.venv\Scripts\python backend/test_api.py
```

### 4. 启动服务

- **方式一：网页版开发控制台（推荐）**
  双击根目录下的 **`开发助手_网页版.bat`**：
  - 自动启动 `dev_dashboard.py` 并在浏览器打开 **`http://localhost:3000`**；
  - 支持在网页中一键启停前端与后端服务，并通过 SSE 实时查看日志流与日志分类过滤。

- **方式二：使用独立批处理脚本**
  - 启动后端：双击 **`run_backend.bat`**（默认监听 `http://localhost:8000`，Swagger 接口文档位于 `http://localhost:8000/docs`）
  - 启动前端：双击 **`run_frontend.bat`**（默认访问 `http://localhost:5173`，Vite 已配置 `/api` 代理至 `http://127.0.0.1:8000`）

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
