import asyncio
import os
import subprocess
import sys
from typing import Optional
from fastapi import APIRouter, Body, HTTPException
from app.core.sync import local_sync_manager
from app.models import SyncRunRequest, SyncSettingsRequest

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/settings")
async def get_sync_settings():
    """获取本地电脑同步目录与自动同步设置"""
    return local_sync_manager.get_sync_settings()


@router.put("/settings")
async def update_sync_settings(req: SyncSettingsRequest):
    """设置本地同步目录、格式与自动同步开关"""
    if not req.sync_dir or not req.sync_dir.strip():
        raise HTTPException(status_code=400, detail="请填写有效的本地同步文件夹路径")
    try:
        settings = local_sync_manager.update_sync_settings(
            sync_dir=req.sync_dir,
            auto_sync=req.auto_sync,
            file_format=req.file_format,
        )
        return {"success": True, "settings": settings}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法创建或访问该目录: {e}")


def _open_native_folder_dialog(initial_dir: str) -> str:
    script = (
        "import sys, tkinter as tk; from tkinter import filedialog; "
        "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
        "d = filedialog.askdirectory(title='选择作品同步保存的本地文件夹', initialdir=sys.argv[1] if len(sys.argv) > 1 else ''); "
        "print(d or '')"
    )
    init_arg = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
    result = subprocess.run(
        [sys.executable, "-c", script, init_arg],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "文件夹选择窗口启动失败")
    return (result.stdout or "").strip()


@router.post("/browse")
async def browse_local_folder(initial_dir: Optional[str] = Body(default="", embed=True)):
    """弹出系统原生文件夹选择框，供用户直观选择本地目录"""
    try:
        current = initial_dir or local_sync_manager.get_sync_settings().get("sync_dir", "")
        selected = await asyncio.to_thread(_open_native_folder_dialog, current)
        return {"path": selected, "cancelled": not bool(selected)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法打开文件夹选择框，请手动粘贴目录路径: {e}")


@router.post("/run")
async def run_local_sync(req: Optional[SyncRunRequest] = Body(default=None)):
    """立即将全部作品或指定作品同步到本地电脑目录"""
    try:
        if req and req.work_id:
            result = local_sync_manager.sync_work(req.work_id)
            return {"success": True, "mode": "work", **result}
        result = local_sync_manager.sync_all()
        return {"success": True, "mode": "all", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.post("/open-folder")
async def open_sync_folder():
    """在系统资源管理器中打开同步目录"""
    settings = local_sync_manager.get_sync_settings()
    target_dir = settings.get("sync_dir")
    if not target_dir:
        raise HTTPException(status_code=400, detail="尚未配置本地同步目录")
    try:
        os.makedirs(target_dir, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(target_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target_dir])
        else:
            subprocess.Popen(["xdg-open", target_dir])
        return {"success": True, "path": target_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开文件夹失败: {e}")

