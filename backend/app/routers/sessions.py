from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response
from app.core.memory import memory_manager
from app.models import (
    CreateSessionRequest,
    ImportSessionRequest,
    UpdateSessionRequest,
)
from app.utils.formatters import format_session_to_markdown, parse_markdown_to_messages

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions")
async def get_all_sessions():
    """获取所有历史会话列表"""
    return {"sessions": memory_manager.list_sessions()}


@router.post("/sessions")
async def create_new_session(req: CreateSessionRequest):
    """主动新建一个独立会话/章节"""
    session = memory_manager.create_session(
        title=req.title or "新建对话",
        system_prompt=req.system_prompt,
        work_id=req.work_id,
    )
    return {"session": session.model_dump()}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取指定会话的完整历史消息列表"""
    session = memory_manager.get_or_create_session(session_id)
    messages = memory_manager.get_messages(session_id)
    return {
        "session": session.model_dump(),
        "messages": messages,
    }


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest):
    """更新会话的昵称标题、人设 System Prompt 或归属作品"""
    session = memory_manager.update_session(
        session_id=session_id,
        title=req.title,
        system_prompt=req.system_prompt,
        work_id=req.work_id,
    )
    return {"session": session.model_dump()}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话及所有消息记忆"""
    memory_manager.delete_session(session_id)
    return {"success": True, "message": "会话已删除"}


@router.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """清空指定会话的全部消息记忆"""
    memory_manager.clear_session_messages(session_id)
    return {"success": True, "message": "会话记忆已清空"}


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_single_message(
    session_id: str, message_id: int, truncate_after: Optional[bool] = False
):
    """删除指定会话中的单条消息 (若 truncate_after=true 则删除该消息及之后的所有消息)"""
    memory_manager.delete_message(
        message_id=message_id, session_id=session_id, truncate_after=truncate_after
    )
    return {"success": True, "message": "消息已删除"}


@router.get("/sessions/{session_id}/export")
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


@router.get("/sessions/export/all")
async def export_all_sessions_endpoint():
    """导出所有会话及其对话消息 (全量数据备份)"""
    return memory_manager.export_all_sessions()


@router.post("/sessions/import")
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

    new_session = memory_manager.import_session_data(
        title=title, system_prompt=system_prompt, messages=messages
    )
    return {
        "success": True,
        "session": new_session.model_dump(),
        "message_count": len(messages),
    }


@router.get("/search")
async def search_history_endpoint(q: str = Query("", description="搜索关键词")):
    """搜索历史会话标题与消息正文"""
    keyword = (q or "").strip()
    if not keyword:
        return {"query": "", "total_matches": 0, "results": []}
    results = memory_manager.search_history(keyword)
    return {"query": keyword, "total_matches": len(results), "results": results}

