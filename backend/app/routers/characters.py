from fastapi import APIRouter, HTTPException
from app.core.memory import memory_manager
from app.models import CreateCharacterRequest, UpdateCharacterRequest

router = APIRouter(prefix="/api", tags=["characters"])


@router.get("/works/{work_id}/characters")
async def list_work_characters(work_id: str):
    """获取指定作品下的全部角色卡"""
    if not memory_manager.get_work(work_id):
        raise HTTPException(status_code=404, detail="作品不存在")
    characters = memory_manager.list_characters(work_id=work_id)
    return {"characters": characters}


@router.post("/works/{work_id}/characters")
async def create_work_character(work_id: str, req: CreateCharacterRequest):
    """在指定作品下新建一个角色卡"""
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="角色名不能为空")
    character = memory_manager.create_character(work_id, req)
    if not character:
        raise HTTPException(status_code=404, detail="目标作品不存在")
    return {"character": character.model_dump()}


@router.get("/characters/{char_id}")
async def get_character(char_id: str):
    """获取单个角色卡详情"""
    character = memory_manager.get_character(char_id)
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"character": character}


@router.put("/characters/{char_id}")
async def update_character(char_id: str, req: UpdateCharacterRequest):
    """更新角色卡信息（含启停状态切换）"""
    if req.name is not None and not req.name.strip():
        raise HTTPException(status_code=400, detail="角色名不能为空")
    character = memory_manager.update_character(char_id, req)
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"character": character}


@router.delete("/characters/{char_id}")
async def delete_character(char_id: str):
    """删除单个角色卡"""
    deleted = memory_manager.delete_character(char_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"success": True, "message": "角色已删除"}

