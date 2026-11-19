import asyncio
import re
from typing import Dict, List, Optional
from app.core.llm import generate_chat_completion


def build_title_prompt(first_msg: str, work_title: Optional[str] = None) -> List[Dict[str, str]]:
    """
    构建用于生成简短、概括性会话标题的 System + User Prompt
    """
    clean_msg = (first_msg or "").strip()[:200]
    work_context = f"所属作品：《{work_title}》。\n" if work_title else ""

    system_prompt = (
        "你是一个小说与剧本创作助手的标题生成专家。你的任务是根据用户的首条创作提问，"
        "提炼一个能够高度概括其意图、短小精炼的中文会话标题。\n"
        "【严格要求】：\n"
        "1. 标题长度必须在 4 到 12 个汉字以内；\n"
        "2. 仅输出标题文本本身，绝对不要添加书名号《》、引号\"\"、句号、感叹号或任何前后缀说明；\n"
        "3. 概括要精准（例如：'设计雨夜开篇'、'主角身世小传'、'第三章冲突转折'、'星舰设定梳理'）；\n"
        "4. 切勿直接抄录用户的长句开头。"
    )

    user_prompt = f"{work_context}用户首条创作提问内容如下：\n\"\"\"\n{clean_msg}\n\"\"\"\n请输出概括标题："

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def sanitize_title(raw_title: str) -> Optional[str]:
    """
    清洗大模型返回的标题内容，去除引号、标点及冗余说明
    """
    if not raw_title:
        return None
    # 去除常见包装符号
    text = raw_title.strip()
    text = re.sub(r"^(标题|建议标题|会话标题)[：:]\s*", "", text)
    text = re.sub(r'^[《“"\'「（\[【]+|[》”"\'」）\]】]+$', "", text)
    text = re.sub(r"[\r\n\t]+", " ", text).strip()
    text = re.sub(r"[。！？.!?,，]+$", "", text).strip()

    if 2 <= len(text) <= 20:
        return text[:16]
    return None


async def generate_smart_title(
    first_msg: str,
    work_title: Optional[str] = None,
    timeout: float = 5.0,
) -> Optional[str]:
    """
    M4a: 异步调用大模型轻量生成短标题，超时或异常时返回 None 以走降级逻辑
    """
    if not first_msg or not first_msg.strip():
        return None

    messages = build_title_prompt(first_msg, work_title)
    try:
        raw_result = await generate_chat_completion(
            messages=messages,
            temperature=0.3,
            timeout=timeout,
        )
        return sanitize_title(raw_result)
    except Exception as e:
        # 超时或模型错误不阻塞主流程，直接降级
        print(f"[SmartTitle] AI 自动标题生成降级: {e}")
        return None

