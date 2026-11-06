import json
import os
import re
import sys
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from memory import (
    memory_manager,
    format_session_to_markdown,
    parse_markdown_to_messages,
)

# Ensure stdout uses utf-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_file)
load_dotenv()

app = FastAPI(
    title="Rabbit DeepSeek Chat API",
    description="Python FastAPI backend with server-side session memory for DeepSeek Chatbot",
    version="1.1.0",
)

# Enable CORS for local Vue 3 development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm_client(model: Optional[str] = None) -> tuple[AsyncOpenAI, str]:
    model_name = (model or os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")).strip()

    # 如果是智谱 GLM 模型
    if model_name.startswith("glm-"):
        api_key = os.environ.get("ZHIPU_API_KEY", "").strip()
        base_url = os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/").strip()
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="ZHIPU_API_KEY 未配置，请在 backend/.env 中填入有效的智谱 API Key",
            )
        return AsyncOpenAI(api_key=api_key, base_url=base_url), model_name

    # 默认 DeepSeek 模型
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="DEEPSEEK_API_KEY 未配置，请在 backend/.env 中填入有效的 API Key",
        )
    return AsyncOpenAI(api_key=api_key, base_url=base_url), model_name


def get_openai_client() -> AsyncOpenAI:
    client, _ = get_llm_client()
    return client


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息文本内容")


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "新建对话"
    system_prompt: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class BotSettingsRequest(BaseModel):
    bot_nickname: Optional[str] = None
    bot_persona: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        None, description="后端会话ID，如果不传将自动创建新会话"
    )
    message: Optional[str] = Field(None, description="用户本次发送的提问内容")
    messages: Optional[List[ChatMessage]] = Field(
        None, description="兼容旧版：直接传递全量消息列表"
    )
    model: Optional[str] = "deepseek-chat"
    temperature: Optional[float] = 0.7
    max_history_rounds: Optional[int] = Field(
        10, description="滑动窗口：传递给大模型的最大历史轮次"
    )
    stream: Optional[bool] = True
    regenerate: Optional[bool] = Field(
        False, description="是否重新生成回答 (若为True则不将message再次存入数据库)"
    )


@app.get("/api/settings")
async def get_settings():
    """获取开发助手全局配置 (昵称与默认人设)"""
    return memory_manager.get_bot_settings()


@app.put("/api/settings")
async def update_settings(req: BotSettingsRequest):
    """更新开发助手全局配置 (昵称与默认人设)"""
    settings = memory_manager.update_bot_settings(
        bot_nickname=req.bot_nickname,
        bot_persona=req.bot_persona
    )
    return {"success": True, "settings": settings}


@app.get("/api/health")
async def health_check():
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", "").strip()
    has_api_key = bool(deepseek_key or zhipu_key)
    return {
        "status": "ok",
        "has_api_key": has_api_key,
        "has_deepseek_key": bool(deepseek_key),
        "has_zhipu_key": bool(zhipu_key),
        "default_model": os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    }


@app.get("/api/models")
async def list_models():
    return {
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek V3 (通用对话)",
                "description": "适合多轮日常对话、编码与通用文本创作，响应敏捷",
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek R1 (深度思考 / 推理)",
                "description": "具备慢思考能力，展示完整思维链推理过程，擅长数学与复杂逻辑",
            },
            {
                "id": "glm-4-flash",
                "name": "智谱 GLM-4-Flash (免费开源/极速)",
                "description": "智谱官方永久免费大模型，毫秒级响应，适合日常聊天、快速问答与代码辅助",
            },
            {
                "id": "glm-4-plus",
                "name": "智谱 GLM-4-Plus (旗舰模型)",
                "description": "智谱新一代高智能旗舰模型，擅长复杂推理、长文本理解与高阶任务",
            },
        ]
    }


# ==========================================
# 会话记忆与管理 API (Server-Side Session Memory)
# ==========================================


@app.get("/api/sessions")
async def get_all_sessions():
    """获取所有历史会话列表"""
    return {"sessions": memory_manager.list_sessions()}


@app.post("/api/sessions")
async def create_new_session(req: CreateSessionRequest):
    """主动新建一个独立会话"""
    session = memory_manager.create_session(
        title=req.title or "新建对话", system_prompt=req.system_prompt
    )
    return {"session": session.model_dump()}


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取指定会话的完整历史消息列表 (供前端重现会话)"""
    session = memory_manager.get_or_create_session(session_id)
    messages = memory_manager.get_messages(session_id)
    return {
        "session": session.model_dump(),
        "messages": messages,
    }


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest):
    """更新会话的昵称标题或人设 System Prompt"""
    session = memory_manager.update_session(
        session_id=session_id,
        title=req.title,
        system_prompt=req.system_prompt
    )
    return {"session": session.model_dump()}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话及所有消息记忆"""
    memory_manager.delete_session(session_id)
    return {"success": True, "message": "会话已删除"}


@app.post("/api/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """清空指定会话的全部消息记忆"""
    memory_manager.clear_session_messages(session_id)
    return {"success": True, "message": "会话记忆已清空"}


@app.delete("/api/sessions/{session_id}/messages/{message_id}")
async def delete_single_message(
    session_id: str, message_id: int, truncate_after: Optional[bool] = False
):
    """删除指定会话中的单条消息 (若 truncate_after=true 则删除该消息及之后的所有消息)"""
    memory_manager.delete_message(
        message_id=message_id, session_id=session_id, truncate_after=truncate_after
    )
    return {"success": True, "message": "消息已删除"}


class ImportSessionRequest(BaseModel):
    format: Optional[str] = "json"  # "json" 或 "markdown"
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    session: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    markdown_content: Optional[str] = None


@app.get("/api/sessions/{session_id}/export")
async def export_session_endpoint(session_id: str, format: Optional[str] = "json"):
    """导出单个会话 (支持 format=json 或 format=markdown)"""
    data = memory_manager.export_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")

    if format == "markdown":
        bot_settings = memory_manager.get_bot_settings()
        bot_name = bot_settings.get("bot_nickname", "Rabbit AI")
        md_text = format_session_to_markdown(
            session_title=data["session"]["title"],
            system_prompt=data["session"]["system_prompt"],
            messages=data["messages"],
            bot_name=bot_name,
        )
        return Response(content=md_text, media_type="text/markdown; charset=utf-8")

    return data


@app.get("/api/sessions/export/all")
async def export_all_sessions_endpoint():
    """导出所有会话及其对话消息 (全量数据备份)"""
    return memory_manager.export_all_sessions()


@app.post("/api/sessions/import")
async def import_session_endpoint(req: ImportSessionRequest):
    """导入会话与对话记录 (支持 JSON 数据或 Markdown 格式)"""
    if req.format == "markdown" or req.markdown_content:
        if not req.markdown_content or not req.markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown 内容不能为空")

        parsed_title, parsed_prompt, parsed_msgs = parse_markdown_to_messages(
            req.markdown_content
        )
        title = req.title or parsed_title
        system_prompt = req.system_prompt or parsed_prompt
        messages = parsed_msgs
    else:
        title = req.title
        system_prompt = req.system_prompt
        messages = req.messages or []

        if req.session:
            if not title:
                title = req.session.get("title")
            if not system_prompt:
                system_prompt = req.session.get("system_prompt")
            if not messages and "messages" in req.session:
                messages = req.session.get("messages")

    if not messages:
        raise HTTPException(status_code=400, detail="未解析到有效的对话消息记录")

    new_session = memory_manager.import_session_data(
        title=title,
        system_prompt=system_prompt,
        messages=messages,
    )

    return {
        "success": True,
        "session": new_session.model_dump(),
        "message_count": len(messages),
    }


@app.get("/api/search")
async def search_history_endpoint(q: str = Query("", description="搜索关键词")):
    """搜索历史会话标题与消息正文"""
    keyword = (q or "").strip()
    if not keyword:
        return {"query": "", "total_matches": 0, "results": []}
    results = memory_manager.search_history(keyword)
    return {"query": keyword, "total_matches": len(results), "results": results}


# ==========================================
# 核心对话流式接口 (集成记忆自动存储与滑动窗口)
# ==========================================


@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    client, target_model = get_llm_client(request.model)

    session_id = request.session_id
    current_message = (request.message or "").strip()
    is_regenerate = bool(request.regenerate)

    # 1. 如果传了 session_id 或单独的 message 或要求重新生成，启用后端记忆机制
    if session_id or current_message or is_regenerate:
        session = memory_manager.get_or_create_session(session_id)
        session_id = session.id

        # 仅在非重新生成且有新内容时，将用户问题存入后端持久化数据库
        if current_message and not is_regenerate:
            memory_manager.add_message(session_id, "user", current_message)

        # 通过滑动窗口机制自动截取上下文 (默认最近 10 轮 + 置顶 System Prompt)
        formatted_messages = memory_manager.get_model_context(
            session_id, max_rounds=request.max_history_rounds or 10
        )

        # 防御兜底：若上下文最后一条不是 user，且传入了当前提问内容，则追加 user 消息给大模型
        if current_message and (
            not formatted_messages or formatted_messages[-1].get("role") != "user"
        ):
            formatted_messages.append({"role": "user", "content": current_message})
    elif request.messages:
        # 兼容传统方式：直接接收全量消息数组
        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]
    else:
        raise HTTPException(
            status_code=400, detail="请提供 message 提问内容或 messages 列表"
        )

    async def event_generator():
        full_content = ""
        full_reasoning = ""

        try:
            # 优先向前端告知当前使用的 session_id
            if session_id:
                meta_payload = json.dumps(
                    {"session_id": session_id}, ensure_ascii=False
                )
                yield f"data: {meta_payload}\n\n"

            response = await client.chat.completions.create(
                model=target_model,
                messages=formatted_messages,
                temperature=request.temperature or 0.7,
                stream=True,
            )

            async for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None) or ""
                reasoning = getattr(delta, "reasoning_content", None) or ""

                if content:
                    full_content += content
                if reasoning:
                    full_reasoning += reasoning

                if content or reasoning:
                    payload = json.dumps(
                        {"content": content, "reasoning_content": reasoning},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"

            # 流式传输结束：将大模型生成的完整回复存入后端数据库记忆
            if session_id and (full_content or full_reasoning):
                memory_manager.add_message(
                    session_id,
                    "assistant",
                    full_content,
                    reasoning_content=full_reasoning,
                )

            # 结束标志
            yield "data: [DONE]\n\n"

        except Exception as e:
            err_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FastAPI server on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
