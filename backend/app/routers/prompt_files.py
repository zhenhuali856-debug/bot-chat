from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.core.memory import memory_manager
from app.models import CreatePromptFileRequest, UpdatePromptFileRequest

router = APIRouter(prefix="/api/prompt-files", tags=["prompt-files"])


@router.get("")
async def list_prompt_files(
    session_id: Optional[str] = Query(None, description="当前会话 ID"),
    work_id: Optional[str] = Query(None, description="当前作品 ID"),
    include_all: bool = Query(False, description="是否返回全部提示词文件"),
    current_user=Depends(get_current_user),
):
    """获取 Markdown 提示词文件列表 (全局 + 当前作品 + 当前会话，带 user_id 隔离)"""
    files = memory_manager.list_prompt_files(
        session_id=session_id,
        work_id=work_id,
        include_all=include_all,
        user_id=current_user["id"],
    )
    return {"prompt_files": files}


@router.post("")
async def create_prompt_file(
    req: CreatePromptFileRequest, current_user=Depends(get_current_user)
):
    """上传并读取保存一个 .md 提示词文件"""
    if not req.filename or not req.filename.strip():
        raise HTTPException(status_code=400, detail="提示词文件名不能为空")
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Markdown 提示词文件内容不能为空")

    prompt_file = memory_manager.create_prompt_file(req, user_id=current_user["id"])
    return {"prompt_file": prompt_file.model_dump()}


@router.get("/{file_id}")
async def get_prompt_file(file_id: str, current_user=Depends(get_current_user)):
    """读取单个 Markdown 提示词文件的完整内容"""
    prompt_file = memory_manager.get_prompt_file(file_id, user_id=current_user["id"])
    if not prompt_file:
        raise HTTPException(status_code=404, detail="提示词文件不存在")
    return {"prompt_file": prompt_file}


@router.put("/{file_id}")
async def update_prompt_file(
    file_id: str, req: UpdatePromptFileRequest, current_user=Depends(get_current_user)
):
    """更新 Markdown 提示词文件的内容、文件名、作用域或启停状态"""
    prompt_file = memory_manager.update_prompt_file(
        file_id, req, user_id=current_user["id"]
    )
    if not prompt_file:
        raise HTTPException(status_code=404, detail="提示词文件不存在")
    return {"prompt_file": prompt_file}


@router.delete("/{file_id}")
async def delete_prompt_file(file_id: str, current_user=Depends(get_current_user)):
    """删除指定 Markdown 提示词文件"""
    deleted = memory_manager.delete_prompt_file(file_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="提示词文件不存在")
    return {"success": True, "message": "提示词文件已移除"}

