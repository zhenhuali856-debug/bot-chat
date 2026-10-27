import json
import os
import sys
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from memory import memory_manager

# Ensure stdout uses utf-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
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


def get_openai_client() -> AsyncOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="DEEPSEEK_API_KEY 未配置，请在 backend/.env 中填入有效的 API Key",
        )
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息文本内容")


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "新建对话"
    system_prompt: Optional[str] = None


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


@app.get("/api/health")
async def health_check():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    return {
        "status": "ok",
        "has_api_key": bool(api_key),
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


# ==========================================
# 核心对话流式接口 (集成记忆自动存储与滑动窗口)
# ==========================================


@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    client = get_openai_client()

    session_id = request.session_id
    current_message = request.message

    # 1. 如果传了 session_id 或单独的 message，启用后端记忆机制
    if session_id or current_message:
        session = memory_manager.get_or_create_session(session_id)
        session_id = session.id

        # 将用户问题存入后端持久化数据库
        if current_message:
            memory_manager.add_message(session_id, "user", current_message)

        # 通过滑动窗口机制自动截取上下文 (默认最近 10 轮 + 置顶 System Prompt)
        formatted_messages = memory_manager.get_model_context(
            session_id, max_rounds=request.max_history_rounds or 10
        )
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
                model=request.model or "deepseek-chat",
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
