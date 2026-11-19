from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.core.memory import memory_manager
from app.models import CreateMaterialRequest, UpdateMaterialRequest

router = APIRouter(prefix="/api", tags=["materials"])


@router.get("/works/{work_id}/materials")
async def list_work_materials(
    work_id: str,
    type: Optional[str] = Query(None, description="按素材类型过滤：灵感/金句/参考/设定片段"),
    current_user=Depends(get_current_user),
):
    """获取指定作品下的素材列表（支持按类型过滤）"""
    uid = current_user["id"]
    if not memory_manager.get_work(work_id, user_id=uid):
        raise HTTPException(status_code=404, detail="作品不存在")
    materials = memory_manager.list_materials(work_id=work_id, mat_type=type, user_id=uid)
    return {"materials": materials}


@router.post("/works/{work_id}/materials")
async def create_work_material(
    work_id: str, req: CreateMaterialRequest, current_user=Depends(get_current_user)
):
    """在指定作品下新建一条素材"""
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="素材内容不能为空")
    material = memory_manager.create_material(work_id, req, user_id=current_user["id"])
    if not material:
        raise HTTPException(status_code=404, detail="目标作品不存在")
    return {"material": material.model_dump()}


@router.get("/materials/{mat_id}")
async def get_material(mat_id: str, current_user=Depends(get_current_user)):
    """获取单条素材详情"""
    material = memory_manager.get_material(mat_id, user_id=current_user["id"])
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"material": material}


@router.put("/materials/{mat_id}")
async def update_material(
    mat_id: str, req: UpdateMaterialRequest, current_user=Depends(get_current_user)
):
    """更新单条素材信息"""
    if req.content is not None and not req.content.strip():
        raise HTTPException(status_code=400, detail="素材内容不能为空")
    material = memory_manager.update_material(mat_id, req, user_id=current_user["id"])
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"material": material}


@router.delete("/materials/{mat_id}")
async def delete_material(mat_id: str, current_user=Depends(get_current_user)):
    """删除单条素材"""
    deleted = memory_manager.delete_material(mat_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"success": True, "message": "素材已删除"}

