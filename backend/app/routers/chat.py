import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.auth import get_current_user
from app.core.llm import get_llm_client
from app.core.memory import memory_manager
from app.core.title import generate_smart_title
from app.models import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


async def _async_generate_and_update_title(session_id: str, first_msg: str, work_id: str = None):
    """M4a 后台异步生成概括性短标题，不阻塞流式对话体验"""
    try:
        work_title = None
        if work_id:
            w = memory_manager.get_work(work_id)
            if w:
                work_title = w.get("title")
        st = await generate_smart_title(first_msg, work_title=work_title, timeout=5.0)
        if st:
            memory_manager.update_session_title(session_id, st)
    except Exception as e:
        print(f"[SmartTitle Async] 标题异步生成任务失败: {e}")


@router.post("/chat")
async def chat_stream(request: ChatRequest, current_user=Depends(get_current_user)):
    client, target_model = get_llm_client(request.model)
    uid = current_user["id"]

    session_id = request.session_id
    current_message = (request.message or "").strip()
    is_regenerate = bool(request.regenerate)

    # 1. 如果传了 session_id、单独的 message 或要求重新生成，启用后端记忆机制
    if session_id or current_message or is_regenerate:
        session = memory_manager.get_or_create_session(session_id, user_id=uid)
        session_id = session.id
        should_gen_title = (session.title in ("新建对话", "") or session.title.startswith("新建对话")) and bool(current_message) and not is_regenerate

        # 仅在非重新生成且有新内容时，将用户问题存入后端持久化数据库
        if current_message and not is_regenerate:
            memory_manager.add_message(session_id, "user", current_message, user_id=uid)
            # M4a: 若为首轮消息且是默认标题，在后台异步启动智能概括标题生成
            if should_gen_title:
                asyncio.create_task(
                    _async_generate_and_update_title(session_id, current_message, session.work_id)
                )

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

