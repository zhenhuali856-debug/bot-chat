from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.core.memory import memory_manager
from app.core.sync import local_sync_manager
from app.models import (
    CreateChapterRequest,
    CreateChapterVersionRequest,
    UpdateChapterRequest,
)

router = APIRouter(prefix="/api", tags=["chapters"])


@router.get("/chapters")
async def list_all_chapters(
    work_id: Optional[str] = Query(None, description="按作品 ID 过滤章节"),
    current_user=Depends(get_current_user),
):
    """获取当前用户的作品正文章节列表"""
    chapters = memory_manager.list_chapters(work_id=work_id, user_id=current_user["id"])
    return {"chapters": chapters}


@router.get("/works/{work_id}/chapters")
async def list_work_chapters(work_id: str, current_user=Depends(get_current_user)):
    """获取指定作品下的所有正文章节"""
    uid = current_user["id"]
    if not memory_manager.get_work(work_id, user_id=uid):
        raise HTTPException(status_code=404, detail="作品不存在")
    chapters = memory_manager.list_chapters(work_id=work_id, user_id=uid)
    return {"chapters": chapters}


@router.post("/works/{work_id}/chapters")
async def create_work_chapter(
    work_id: str, req: CreateChapterRequest, current_user=Depends(get_current_user)
):
    """在指定作品下新建正文章节并写入内容"""
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="章节名称不能为空")
    chapter = memory_manager.create_chapter(work_id, req, user_id=current_user["id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="目标作品不存在")
    local_sync_manager.auto_sync_work_if_enabled(work_id)
    return {"chapter": chapter.model_dump()}


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: str, current_user=Depends(get_current_user)):
    """获取单个正文章节详情"""
    chapter = memory_manager.get_chapter(chapter_id, user_id=current_user["id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"chapter": chapter}


@router.put("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: str, req: UpdateChapterRequest, current_user=Depends(get_current_user)
):
    """更新章节名称/内容或追加对话内容到章节末尾"""
    chapter = memory_manager.update_chapter(chapter_id, req, user_id=current_user["id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    local_sync_manager.auto_sync_work_if_enabled(chapter["work_id"])
    return {"chapter": chapter}


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(chapter_id: str, current_user=Depends(get_current_user)):
    """删除指定正文章节"""
    uid = current_user["id"]
    existing = memory_manager.get_chapter(chapter_id, user_id=uid)
    if not existing:
        raise HTTPException(status_code=404, detail="章节不存在")
    deleted = memory_manager.delete_chapter(chapter_id, user_id=uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="章节不存在")
    local_sync_manager.auto_sync_work_if_enabled(existing["work_id"])
    return {"success": True, "message": "章节已删除"}


@router.get("/chapters/{chapter_id}/versions")
async def list_chapter_versions(chapter_id: str, current_user=Depends(get_current_user)):
    """M3c 获取指定章节的历史版本快照列表"""
    uid = current_user["id"]
    existing = memory_manager.get_chapter(chapter_id, user_id=uid)
    if not existing:
        raise HTTPException(status_code=404, detail="章节不存在")
    versions = memory_manager.list_chapter_versions(chapter_id, user_id=uid)
    return {"versions": versions, "chapter": existing}


@router.post("/chapters/{chapter_id}/versions")
async def create_chapter_version(
    chapter_id: str,
    req: Optional[CreateChapterVersionRequest] = None,
    current_user=Depends(get_current_user),
):
    """M3c 将指定章节当前内容保存为历史版本快照（单章最多保留 20 个版本）"""
    version = memory_manager.create_chapter_version(
        chapter_id, req, user_id=current_user["id"]
    )
    if not version:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"version": version}

