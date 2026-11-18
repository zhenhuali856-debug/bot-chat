from fastapi import APIRouter, HTTPException
from app.core.llm import generate_chat_completion
from app.core.memory import memory_manager
from app.core.outline import build_split_prompt, parse_chapter_plan
from app.core.sync import local_sync_manager
from app.models import BatchCreateChaptersRequest, SplitOutlineRequest

router = APIRouter(prefix="/api", tags=["outline"])


@router.post("/works/{work_id}/split-outline")
async def split_work_outline(work_id: str, req: SplitOutlineRequest):
    """
    M3b AI 一键拆章：
    基于作品大纲、简介與启用角色卡，生成可编辑的章节规划列表（不直接入库）
    """
    work = memory_manager.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")

    raw_outline = (
        req.outline_override
        if req.outline_override is not None
        else (work.get("outline") or "")
    ).strip()
    if not raw_outline:
        raise HTTPException(
            status_code=400,
            detail="当前作品尚未填写大纲。请先填写故事大纲，再使用 AI 一键拆章。",
        )

    chapter_count = max(1, min(50, int(req.chapter_count or 5)))

    all_chars = memory_manager.list_characters(work_id=work_id)
    active_chars = [c for c in all_chars if c.get("is_active")]
    if req.character_names is not None:
        selected_names = set(req.character_names)
        active_chars = [c for c in active_chars if c.get("name") in selected_names]

    messages, warning = build_split_prompt(
        work=work,
        chars=active_chars,
        chapter_count=chapter_count,
        style_hint=req.style_hint,
        outline_override=raw_outline,
    )

    try:
        raw_reply = await generate_chat_completion(
            messages=messages,
            model_name=req.model,
            temperature=0.5,
            timeout=45.0,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"调用模型生成章节规划失败，请检查模型配置或稍后重试：{str(exc)}",
        )

    plans = parse_chapter_plan(raw_reply, expected_count=chapter_count)
    if not plans:
        raise HTTPException(
            status_code=500,
            detail="模型未能返回有效的章节规划结构，请重试或补充大纲细节。",
        )

    return {
        "chapters": plans,
        "warning": warning,
    }


@router.post("/works/{work_id}/chapters/batch")
async def batch_create_work_chapters(work_id: str, req: BatchCreateChaptersRequest):
    """
    M3b 拆章审核通过后批量创建章节（幂等：按章节标题去重，绝不覆盖已有章节）
    """
    work = memory_manager.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")

    if not req.chapters:
        raise HTTPException(status_code=400, detail="请至少勾选一个要创建的章节")

    result = memory_manager.batch_create_chapters(work_id=work_id, plans=req.chapters)
    if result["created"]:
        local_sync_manager.auto_sync_work_if_enabled(work_id)

    return {
        "created": result["created"],
        "skipped": result["skipped"],
        "created_count": len(result["created"]),
    }

