import os
from typing import Any, Dict, List, Optional, Tuple
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


async def generate_chat_completion(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    temperature: float = 0.5,
    timeout: float = 35.0,
) -> str:
    """
    M3b 专用：非流式调用大模型，获取完整文本响应（用于大纲拆章等结构化 JSON 生成）
    """
    # 若未指定或当前无 DeepSeek key 而有智谱/Gemini key，智能选择可用模型
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY).strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", ZHIPU_API_KEY).strip()

    chosen_model = model_name
    if not chosen_model or (
        "deepseek" in chosen_model.lower() and not deepseek_key
    ):
        if deepseek_key:
            chosen_model = DEEPSEEK_DEFAULT_MODEL
        elif gemini_key:
            chosen_model = GEMINI_DEFAULT_MODEL
        elif zhipu_key:
            chosen_model = ZHIPU_DEFAULT_MODEL

    client, target_model = get_llm_client(chosen_model)
    response = await client.chat.completions.create(
        model=target_model,
        messages=messages,
        temperature=temperature,
        stream=False,
        timeout=timeout,
    )
    if response.choices and response.choices[0].message:
        return response.choices[0].message.content or ""
    return ""

