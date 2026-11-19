import os
import sys
from contextlib import asynccontextmanager
import shutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import PORT, DB_PATH
from app.routers import (
    chapters,
    characters,
    chat,
    export,
    materials,
    outline,
    prompt_files,
    sessions,
    sync,
    system,
    works,
)

# Windows 终端强制 UTF-8 编码
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def auto_backup_database():
    """P0 安全加固：启动时自动备份数据库，防止误删或损坏导致记忆丢失"""
    try:
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
            backup_path = f"{DB_PATH}.bak"
            shutil.copy2(DB_PATH, backup_path)
            print(f"[DB Backup] 数据库自动备份完成: {backup_path}")
    except Exception as e:
        print(f"[DB Backup] 自动备份异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    auto_backup_database()
    yield


# 初始化 FastAPI 应用
app = FastAPI(
    title="Rabbit AI API",
    description="支持 DeepSeek 与 智谱大模型、服务端多轮记忆与思考链保留的开发助手后端",
    version="2.0.0",
    lifespan=lifespan,
)

# P0 安全加固：收紧 CORS 白名单，防止公网部署携带凭证裸奔
cors_origins_env = os.environ.get("CORS_ORIGINS", "").strip()
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载模块化路由
app.include_router(system.router)
app.include_router(works.router)
app.include_router(chapters.router)
app.include_router(characters.router)
app.include_router(materials.router)
app.include_router(export.router)
app.include_router(outline.router)
app.include_router(sessions.router)
app.include_router(prompt_files.router)
app.include_router(sync.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    print(f"Starting FastAPI server on http://localhost:{PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
