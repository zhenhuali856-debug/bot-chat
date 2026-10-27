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
    description="Python FastAPI backend for Vue 3 DeepSeek Chatbot",
    version="1.0.0",
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


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "deepseek-chat"
    temperature: Optional[float] = 0.7
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


@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    client = get_openai_client()

    # Format messages for OpenAI client
    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in request.messages
    ]

    async def event_generator():
        try:
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
                # DeepSeek-Reasoner (R1) thinking / reasoning content
                reasoning = getattr(delta, "reasoning_content", None) or ""

                if content or reasoning:
                    payload = json.dumps(
                        {"content": content, "reasoning_content": reasoning},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"

            # End of stream indicator
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
