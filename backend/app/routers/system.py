import os
from fastapi import APIRouter, Depends
from app.config import (
    AVAILABLE_MODELS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    GEMINI_API_KEY,
    GENRE_TEMPLATES,
    ZHIPU_API_KEY,
)
from app.core.auth import get_current_user
from app.core.memory import memory_manager
from app.models import BotSettingsRequest

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    """检查后端服务状态与 API Key 就绪状态（公开接口，无需鉴权）"""
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY).strip()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", ZHIPU_API_KEY).strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    has_api_key = bool(deepseek_key or zhipu_key or gemini_key)
    return {
        "status": "ok",
        "has_api_key": has_api_key,
        "has_deepseek_key": bool(deepseek_key),
        "has_zhipu_key": bool(zhipu_key),
        "has_gemini_key": bool(gemini_key),
        "default_model": os.environ.get("DEEPSEEK_DEFAULT_MODEL", DEEPSEEK_DEFAULT_MODEL),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL),
        "multi_user_mode": memory_manager.is_multi_user_mode(),
    }


@router.get("/models")
async def list_models():
    """返回当前系统支持的大模型列表"""
    return {"models": AVAILABLE_MODELS}


@router.get("/genre-templates")
async def list_genre_templates():
    """M3a-2 返回内置体裁大纲模板字典"""
    return {"templates": GENRE_TEMPLATES}


@router.get("/settings")
async def get_settings(current_user=Depends(get_current_user)):
    """获取当前用户的创作教练配置 (昵称与默认人设)"""
    return memory_manager.get_bot_settings(user_id=current_user["id"])


@router.put("/settings")
async def update_settings(
    req: BotSettingsRequest, current_user=Depends(get_current_user)
):
    """更新当前用户的创作教练配置 (昵称与默认人设)"""
    settings = memory_manager.update_bot_settings(
        bot_nickname=req.bot_nickname,
        bot_persona=req.bot_persona,
        user_id=current_user["id"],
    )
    return {"success": True, "settings": settings}

