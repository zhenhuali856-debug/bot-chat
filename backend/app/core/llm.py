import os
from typing import Optional, Tuple
from openai import AsyncOpenAI
from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
    ZHIPU_DEFAULT_MODEL,
)


def get_llm_client(model_name: Optional[str] = None) -> Tuple[AsyncOpenAI, str]:
    """
    根据模型标识分流获取对应的异步大模型客户端与目标模型名称
    """
    selected = (model_name or DEEPSEEK_DEFAULT_MODEL).lower()

    # Google Gemini / Gemma 系列模型分流 (OpenAI 兼容接口)
    if "gemini" in selected or "gemma" in selected:
        api_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
        base_url = os.environ.get("GEMINI_BASE_URL", GEMINI_BASE_URL)
        target_model = model_name if model_name else GEMINI_DEFAULT_MODEL
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return client, target_model

    # 智谱系列模型分流
    if "glm" in selected:
        api_key = os.environ.get("ZHIPU_API_KEY", ZHIPU_API_KEY)
        base_url = os.environ.get("ZHIPU_BASE_URL", ZHIPU_BASE_URL)
        target_model = model_name if model_name else ZHIPU_DEFAULT_MODEL
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return client, target_model

    # 默认使用 DeepSeek 客户端
    api_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL)
    target_model = model_name if model_name else DEEPSEEK_DEFAULT_MODEL
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return client, target_model

