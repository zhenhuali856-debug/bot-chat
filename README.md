# Rabbit AI 对话机器人 (Vue 3 + Python FastAPI + DeepSeek)

基于 **Vue 3** 前端与 **Python FastAPI** 后端开发的流式大模型 AI 对话系统，支持接入 **DeepSeek V3 (通用对话)** 与 **DeepSeek R1 (深度思考思维链)**。

---

## 项目目录结构

```text
rabbit/
├── backend/                  # Python 后端
│   ├── .venv/                # Python 独立虚拟环境 (已配置)
│   ├── .env                  # 环境变量文件 (填写 DEEPSEEK_API_KEY)
│   ├── .env.example          # 环境变量示例
│   ├── requirements.txt      # 后端依赖库 (FastAPI, uvicorn, openai 等)
│   ├── main.py               # FastAPI 服务入口 (SSE 流式输出与思维链支持)
│   └── test_api.py           # API Key 与模型连通性快速测试脚本
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── App.vue           # 完整对话界面 (Markdown 渲染、代码高亮、流式打字效果、R1思维链折叠)
│   │   ├── style.css         # 现代暗色玻璃质感样式
│   │   └── main.js
│   ├── vite.config.js        # Vite 配置 (集成后端反向代理 /api)
│   └── package.json
├── run_backend.bat           # 后端一键启动脚本
├── run_frontend.bat          # 前端一键启动脚本
└── README.md
```

---

## 快速配置与运行

### 1. 配置 DeepSeek API Key
打开 [backend/.env](file:///d:/python/my_ai_project/rabbit/backend/.env)，填入您的 API Key：
```env
DEEPSEEK_API_KEY=sk-您的实际Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-chat
PORT=8000
```

> 也可以在系统环境变量中设置 `DEEPSEEK_API_KEY`，程序会自动读取。

### 2. 测试 API 连通性
在项目根目录下运行测试脚本：
```bash
backend\.venv\Scripts\python backend/test_api.py
```
若密钥正确，控制台将收到 DeepSeek 的实时打招呼流式响应。

### 3. 启动服务
- **启动后端**：双击运行 `run_backend.bat` 或在终端执行：
  ```bash
  cd backend
  .venv\Scripts\python main.py
  ```
  后端运行于：`http://localhost:8000` (API 文档位于 `http://localhost:8000/docs`)

- **启动前端**：双击运行 `run_frontend.bat` 或在终端执行：
  ```bash
  cd frontend
  npm run dev
  ```
  前端页面访问：`http://localhost:5173`
