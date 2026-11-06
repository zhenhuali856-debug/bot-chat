from fastapi import APIRouter, HTTPException
from app.core.memory import memory_manager
from app.models import CreateWorkRequest, UpdateWorkRequest

router = APIRouter(prefix="/api/works", tags=["works"])


@router.post("")
async def create_work(req: CreateWorkRequest):
    """创建新作品 (小说/剧本/文案/企划)"""
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="作品名称不能为空")
    work = memory_manager.create_work(req)
    return {"work": work.model_dump()}


@router.get("")
async def list_works():
    """获取所有作品列表 (按更新时间倒序排列)"""
    works = memory_manager.list_works()
    return {"works": works}


@router.get("/{work_id}")
async def get_work(work_id: str):
    """获取单个作品详情 (包含体裁、大纲、简介、目标字数等设定)"""
    work = memory_manager.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    return {"work": work}


@router.put("/{work_id}")
async def update_work(work_id: str, req: UpdateWorkRequest):
    """更新作品设定"""
    work = memory_manager.update_work(work_id, req)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    return {"work": work}


@router.delete("/{work_id}")
async def delete_work(work_id: str):
    """删除作品：将该作品下章节的 work_id 置空（移入未归类），不删除章节内容"""
    memory_manager.delete_work(work_id)
    return {"success": True, "message": "作品已删除，所属章节已移回未归类列表"}


@router.get("/{work_id}/sessions")
async def get_work_sessions(work_id: str):
    """获取指定作品下的所有章节会话列表"""
    sessions = memory_manager.get_sessions_by_work(work_id)
    return {"sessions": sessions}

