import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import PORT
from app.routers import chapters, chat, prompt_files, sessions, sync, system, works

# Windows 终端强制 UTF-8 编码
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 初始化 FastAPI 应用
app = FastAPI(
    title="Rabbit AI API",
    description="支持 DeepSeek 与 智谱大模型、服务端多轮记忆与思考链保留的开发助手后端",
    version="2.0.0",
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载模块化路由
app.include_router(system.router)
app.include_router(works.router)
app.include_router(chapters.router)
app.include_router(sessions.router)
app.include_router(prompt_files.router)
app.include_router(sync.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    print(f"Starting FastAPI server on http://localhost:{PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
