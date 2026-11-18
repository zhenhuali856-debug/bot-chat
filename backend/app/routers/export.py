from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Query, Response
from app.core.memory import memory_manager
from app.utils.book_export import format_work_to_markdown, sanitize_book_filename

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/works/{work_id}/export")
async def export_work_book(
    work_id: str,
    format: str = Query("md", description="导出格式：md"),
):
    """
    M3a-1 整书单文件导出：
    按 封面标题 -> 作品设定 -> 人物表（启用角色） -> 章节正文（按 sort_order 升序） 输出单文件
    """
    work = memory_manager.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")

    fmt = (format or "md").lower().strip()
    if fmt != "md":
        raise HTTPException(status_code=400, detail="本期仅支持导出 Markdown (.md) 格式")

    chapters = memory_manager.list_chapters(work_id=work_id)
    characters = memory_manager.list_characters(work_id=work_id)

    md_text = format_work_to_markdown(work=work, chapters=chapters, characters=characters)
    safe_title = sanitize_book_filename(work.get("title") or "未命名作品")
    filename = f"《{safe_title}》-全书.md"
    encoded_filename = quote(filename)

    return Response(
        content=md_text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"book.md\"; filename*=UTF-8''{encoded_filename}"
        },
    )

