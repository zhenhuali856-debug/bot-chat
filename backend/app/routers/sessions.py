from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from app.core.auth import get_current_user
from app.core.memory import memory_manager
from app.core.title import generate_smart_title
from app.models import (
    CreateSessionRequest,
    ImportSessionRequest,
    UpdateSessionRequest,
)
from app.utils.formatters import format_session_to_markdown, parse_markdown_to_messages

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions")
async def get_all_sessions(current_user=Depends(get_current_user)):
    """获取当前用户的所有历史会话列表"""
    return {"sessions": memory_manager.list_sessions(user_id=current_user["id"])}


@router.post("/sessions")
async def create_new_session(
    req: CreateSessionRequest, current_user=Depends(get_current_user)
):
    """主动新建一个独立会话/章节"""
    uid = current_user["id"]
    session = memory_manager.create_session(
        title=req.title or "新建对话",
        system_prompt=req.system_prompt,
        work_id=req.work_id,
        user_id=uid,
    )
    prev_chapter = memory_manager.get_previous_chapter_for_session(session.id)
    return {
        "session": session.model_dump(),
        "prev_chapter": prev_chapter,
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str, current_user=Depends(get_current_user)
):
    """获取指定会话的完整历史消息列表及上一章无缝承接信息"""
    uid = current_user["id"]
    session = memory_manager.get_or_create_session(session_id, user_id=uid)
    messages = memory_manager.get_messages(session.id, user_id=uid)
    prev_chapter = memory_manager.get_previous_chapter_for_session(session.id)
    return {
        "session": session.model_dump(),
        "messages": messages,
        "prev_chapter": prev_chapter,
    }


@router.get("/sessions/{session_id}/continuity")
async def get_session_continuity(
    session_id: str, current_user=Depends(get_current_user)
):
    """获取当前会话跨章节承接状态及上一章正文片段"""
    if not memory_manager.get_session(session_id, user_id=current_user["id"]):
        raise HTTPException(status_code=404, detail="会话不存在")
    prev_chapter = memory_manager.get_previous_chapter_for_session(session_id)
    return {"prev_chapter": prev_chapter}


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str, req: UpdateSessionRequest, current_user=Depends(get_current_user)
):
    """更新会话的昵称标题、人设 System Prompt、归属作品或指定承接章节"""
    uid = current_user["id"]
    session = memory_manager.update_session(
        session_id=session_id,
        title=req.title,
        system_prompt=req.system_prompt,
        work_id=req.work_id,
        target_chapter_id=req.target_chapter_id,
        user_id=uid,
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    prev_chapter = memory_manager.get_previous_chapter_for_session(session_id)
    return {
        "session": session.model_dump(),
        "prev_chapter": prev_chapter,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user=Depends(get_current_user)):
    """删除指定会话及所有消息记忆"""
    memory_manager.delete_session(session_id, user_id=current_user["id"])
    return {"success": True, "message": "会话已删除"}


@router.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str, current_user=Depends(get_current_user)):
    """清空指定会话的全部消息记忆"""
    memory_manager.clear_session_messages(session_id, user_id=current_user["id"])
    return {"success": True, "message": "会话记忆已清空"}


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_single_message(
    session_id: str,
    message_id: int,
    truncate_after: Optional[bool] = False,
    current_user=Depends(get_current_user),
):
    """删除指定会话中的单条消息 (若 truncate_after=true 则删除该消息及之后的所有消息)"""
    memory_manager.delete_message(
        message_id=message_id,
        session_id=session_id,
        truncate_after=bool(truncate_after),
        user_id=current_user["id"],
    )
    return {"success": True, "message": "消息已删除"}


@router.get("/sessions/{session_id}/export")
async def export_session_endpoint(
    session_id: str,
    format: Optional[str] = "json",
    current_user=Depends(get_current_user),
):
    """导出单个会话 (支持 format=json 或 format=markdown)"""
    uid = current_user["id"]
    data = memory_manager.export_session(session_id, user_id=uid)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")

    if format == "markdown":
        bot_settings = memory_manager.get_bot_settings(user_id=uid)
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
async def export_all_sessions_endpoint(current_user=Depends(get_current_user)):
    """导出当前用户所有会话及其对话消息"""
    return memory_manager.export_all_sessions(user_id=current_user["id"])


@router.post("/sessions/import")
async def import_session_endpoint(
    req: ImportSessionRequest, current_user=Depends(get_current_user)
):
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
        title=title,
        system_prompt=system_prompt,
        messages=messages,
        user_id=current_user["id"],
    )
    return {
        "success": True,
        "session": new_session.model_dump(),
        "message_count": len(messages),
    }


@router.get("/search")
async def search_history_endpoint(
    q: str = Query("", description="搜索关键词"),
    current_user=Depends(get_current_user),
):
    """搜索历史会话标题与消息正文（向后兼容，带 user_id 隔离）"""
    keyword = (q or "").strip()
    if not keyword:
        return {"query": "", "total_matches": 0, "results": []}
    results = memory_manager.search_history(keyword, user_id=current_user["id"])
    return {"query": keyword, "total_matches": len(results), "results": results}


@router.get("/search/global")
async def search_global_endpoint(
    q: str = Query("", description="全局搜索关键词"),
    limit: int = Query(50, ge=1, le=100, description="每类结果上限"),
    current_user=Depends(get_current_user),
):
    """M4b + D2: 全局搜索覆盖会话、消息、角色卡、素材库、章节正文（严格按 user_id 隔离）"""
    keyword = (q or "").strip()
    return memory_manager.search_global(keyword, limit=limit, user_id=current_user["id"])


@router.post("/sessions/{session_id}/auto-title")
async def auto_title_session_endpoint(
    session_id: str, current_user=Depends(get_current_user)
):
    """M4a: 基于会话首条消息智能生成概括性短标题"""
    uid = current_user["id"]
    session = memory_manager.get_session(session_id, user_id=uid)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = memory_manager.get_messages(session_id, user_id=uid)
    user_msgs = [m for m in messages if m.get("role") == "user"]
    if not user_msgs:
        return {"success": False, "message": "暂无用户提问消息，无法生成标题", "title": session.title}

    first_msg = user_msgs[0].get("content") or ""
    work_title = None
    if session.work_id:
        work = memory_manager.get_work(session.work_id, user_id=uid)
        if work:
            work_title = work.get("title")

    smart_title = await generate_smart_title(first_msg, work_title=work_title, timeout=5.0)
    if smart_title:
        memory_manager.update_session_title(session_id, smart_title, user_id=uid)
        return {"success": True, "title": smart_title, "updated": True}

    fallback_title = first_msg[:16].strip() + ("..." if len(first_msg) > 16 else "")
    if session.title in ("新建对话", ""):
        memory_manager.update_session_title(session_id, fallback_title, user_id=uid)
    return {"success": True, "title": session.title if session.title != "新建对话" else fallback_title, "updated": False}

