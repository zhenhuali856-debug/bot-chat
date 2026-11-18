import re
from datetime import datetime
from typing import Any, Dict, List


def sanitize_book_filename(title: str) -> str:
    """将作品名中的非法文件名字符替换为下划线"""
    clean = re.sub(r'[\\/:*?"<>|]+', "_", (title or "未命名作品").strip())
    return clean or "未命名作品"


def format_work_to_markdown(
    work: Dict[str, Any],
    chapters: List[Dict[str, Any]],
    characters: List[Dict[str, Any]],
) -> str:
    """
    M3a-1 整书单文件导出格式化：
    顺序：封面标题 -> 作品设定 -> 人物表（启用角色） -> 章节正文（按 sort_order 升序）
    """
    title = (work.get("title") or "未命名作品").strip()
    genre = (work.get("genre") or "未指定").strip()
    target_words = work.get("target_words") or 0
    summary = (work.get("summary") or "").strip()
    outline = (work.get("outline") or "").strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_written_words = sum((ch.get("word_count") or 0) for ch in chapters)
    active_chars = [c for c in characters if c.get("is_active", True)]

    lines: List[str] = []

    # 1. 封面标题
    lines.append(f"# 《{title}》")
    lines.append("")
    lines.append(
        f"> **体裁类型**：{genre} ｜ **目标字数**：{target_words:,} 字 ｜ **当前累计正文**：{total_written_words:,} 字（共 {len(chapters)} 章）"
    )
    lines.append(f"> **导出时间**：{now_str}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. 作品设定
    lines.append("## 一、作品设定")
    lines.append("")
    lines.append(f"- **作品名称**：《{title}》")
    lines.append(f"- **体裁类型**：{genre}")
    lines.append(f"- **目标字数**：{target_words:,} 字")
    lines.append("")
    lines.append("### 1.1 作品简介 / 世界观")
    lines.append("")
    lines.append(summary if summary else "（暂无作品简介）")
    lines.append("")
    lines.append("### 1.2 故事大纲 / 章节规划")
    lines.append("")
    lines.append(outline if outline else "（暂无故事大纲）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. 人物表（仅启用角色）
    lines.append("## 二、登场人物表")
    lines.append("")
    if not active_chars:
        lines.append("（暂无已启用的角色设定）")
        lines.append("")
    else:
        for idx, ch in enumerate(active_chars, start=1):
            c_name = ch.get("name") or f"角色{idx}"
            c_role = ch.get("role_type") or "配角"
            lines.append(f"### {idx}. {c_name}（{c_role}）")
            lines.append("")
            for label, key in [
                ("身份背景", "background"),
                ("性格特征", "traits"),
                ("外貌特征", "appearance"),
                ("说话风格 / 口头禅", "speech_style"),
                ("人物关系", "relationships"),
                ("备注", "notes"),
            ]:
                val = (ch.get(key) or "").strip()
                if val:
                    lines.append(f"- **{label}**：{val}")
            lines.append("")

    lines.append("---")
    lines.append("")

    # 4. 章节正文（按 sort_order 升序）
    lines.append("## 三、全书章节正文")
    lines.append("")
    if not chapters:
        lines.append("（当前作品尚未创建任何章节）")
        lines.append("")
    else:
        sorted_chapters = sorted(
            chapters,
            key=lambda x: (x.get("sort_order") or 0, x.get("created_at") or 0),
        )
        for idx, chapter in enumerate(sorted_chapters, start=1):
            ch_title = (chapter.get("title") or f"第 {idx} 章").strip()
            ch_content = (chapter.get("content") or "").strip()

            # 如果正文中第一行已经是同名的 Markdown 标题，避免重复打印两行标题
            lines.append(f"### {ch_title}")
            lines.append("")
            if ch_content:
                first_line = ch_content.splitlines()[0].strip()
                cleaned_first = re.sub(r"^[#>\s*`_]+", "", first_line).strip()
                if cleaned_first == ch_title:
                    rest_body = "\n".join(ch_content.splitlines()[1:]).strip()
                    lines.append(rest_body if rest_body else ch_content)
                else:
                    lines.append(ch_content)
            else:
                lines.append("（未写正文）")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"

