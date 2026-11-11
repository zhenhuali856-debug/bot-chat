from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.core.memory import memory_manager
from app.core.sync import local_sync_manager
from app.models import CreateChapterRequest, UpdateChapterRequest

router = APIRouter(prefix="/api", tags=["chapters"])


@router.get("/chapters")
async def list_all_chapters(
    work_id: Optional[str] = Query(None, description="按作品 ID 过滤章节")
):
    """获取作品正文章节列表"""
    chapters = memory_manager.list_chapters(work_id=work_id)
    return {"chapters": chapters}


@router.get("/works/{work_id}/chapters")
async def list_work_chapters(work_id: str):
    """获取指定作品下的所有正文章节"""
    if not memory_manager.get_work(work_id):
        raise HTTPException(status_code=404, detail="作品不存在")
    chapters = memory_manager.list_chapters(work_id=work_id)
    return {"chapters": chapters}


@router.post("/works/{work_id}/chapters")
async def create_work_chapter(work_id: str, req: CreateChapterRequest):
    """在指定作品下新建正文章节并写入内容"""
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="章节名称不能为空")
    chapter = memory_manager.create_chapter(work_id, req)
    if not chapter:
        raise HTTPException(status_code=404, detail="目标作品不存在")
    local_sync_manager.auto_sync_work_if_enabled(work_id)
    return {"chapter": chapter.model_dump()}


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: str):
    """获取单个正文章节详情"""
    chapter = memory_manager.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"chapter": chapter}


@router.put("/chapters/{chapter_id}")
async def update_chapter(chapter_id: str, req: UpdateChapterRequest):
    """更新章节名称/内容或追加对话内容到章节末尾"""
    chapter = memory_manager.update_chapter(chapter_id, req)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    local_sync_manager.auto_sync_work_if_enabled(chapter["work_id"])
    return {"chapter": chapter}


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(chapter_id: str):
    """删除指定正文章节"""
    existing = memory_manager.get_chapter(chapter_id)
    if not existing:
        raise HTTPException(status_code=404, detail="章节不存在")
    deleted = memory_manager.delete_chapter(chapter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="章节不存在")
    local_sync_manager.auto_sync_work_if_enabled(existing["work_id"])
    return {"success": True, "message": "章节已删除"}

