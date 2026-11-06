import os
from fastapi import APIRouter
from app.config import (
    AVAILABLE_MODELS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    ZHIPU_API_KEY,
)
from app.core.memory import memory_manager
from app.models import BotSettingsRequest

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    """检查后端服务状态与 API Key 就绪状态"""
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY).strip()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", ZHIPU_API_KEY).strip()
    has_api_key = bool(deepseek_key or zhipu_key)
    return {
        "status": "ok",
        "has_api_key": has_api_key,
        "has_deepseek_key": bool(deepseek_key),
        "has_zhipu_key": bool(zhipu_key),
        "default_model": os.environ.get("DEEPSEEK_DEFAULT_MODEL", DEEPSEEK_DEFAULT_MODEL),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL),
    }


@router.get("/models")
async def list_models():
    """返回当前系统支持的大模型列表"""
    return {"models": AVAILABLE_MODELS}


@router.get("/settings")
async def get_settings():
    """获取开发助手全局配置 (昵称与默认人设)"""
    return memory_manager.get_bot_settings()


@router.put("/settings")
async def update_settings(req: BotSettingsRequest):
    """更新开发助手全局配置 (昵称与默认人设)"""
    settings = memory_manager.update_bot_settings(
        bot_nickname=req.bot_nickname, bot_persona=req.bot_persona
    )
    return {"success": True, "settings": settings}

