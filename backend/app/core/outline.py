import json
import re
from typing import Any, Dict, List, Optional, Tuple


MAX_OUTLINE_CHARS = 6000


def build_split_prompt(
    work: Dict[str, Any],
    chars: List[Dict[str, Any]],
    chapter_count: int = 5,
    style_hint: Optional[str] = None,
    outline_override: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """
    M3b 构造大纲拆章 Prompt，返回 (messages, warning)
    """
    raw_outline = (
        outline_override if outline_override is not None else (work.get("outline") or "")
    ).strip()
    warning: Optional[str] = None

    if len(raw_outline) < 80:
        warning = "大纲信息较少，规划仅供参考，建议补充大纲后重试。"

    truncated_note = ""
    if len(raw_outline) > MAX_OUTLINE_CHARS:
        raw_outline = raw_outline[:MAX_OUTLINE_CHARS]
        truncated_note = "\n（注：大纲超过 6000 字，此处已截断前 6000 字，请基于可见部分进行规划）"
        warning = "大纲超过 6000 字，已截取前 6000 字生成章节规划。"

    title = work.get("title") or "未命名作品"
    genre = work.get("genre") or "小说"
    summary = (work.get("summary") or "无").strip()

    char_lines = []
    for c in chars[:8]:
        c_name = c.get("name") or ""
        c_role = c.get("role_type") or "角色"
        c_traits = (c.get("traits") or "").strip()
        c_speech = (c.get("speech_style") or "").strip()
        c_rel = (c.get("relationships") or "").strip()
        desc = f"- {c_name}（{c_role}）"
        if c_traits:
            desc += f"｜性格：{c_traits}"
        if c_speech:
            desc += f"｜说话风格：{c_speech}"
        if c_rel:
            desc += f"｜关系：{c_rel}"
        char_lines.append(desc)

    char_block = "\n".join(char_lines) if char_lines else "（未指定特定角色）"
    style_block = (style_hint or "").strip() or "结构清晰、矛盾递进、每章末尾留有适度悬念钩子"

    system_msg = (
        "你是一位资深小说总编与剧本策划师。你的任务是根据作者提供的【作品设定】、【出场角色】与【故事大纲】，"
        "将其拆解为结构化的章节规划列表。\n"
        "【严格输出规范】：\n"
        "1. 必须且只能输出合法的纯 JSON 字符串，不要输出任何 Markdown 代码块标记（如 ```json）或解释性前缀后缀。\n"
        "2. JSON 结构必须严格为：\n"
        '{"chapters": [{"index": 1, "title": "第一章 · 章节标题", "points": ["核心情节点1", "核心情节点2", "本章钩子或收尾要点"]}]}\n'
        "3. 每章 `points` 为 2~5 条简明剧情要点，严禁直接撰写长篇小说正文，严禁凭空捏造与大纲相悖的支线。"
    )

    user_msg = (
        f"请为以下作品拆解并生成 **{chapter_count} 章** 的章节规划：\n\n"
        f"【作品名称】：《{title}》\n"
        f"【体裁类型】：{genre}\n"
        f"【作品简介】：{summary}\n"
        f"【参考出场角色】：\n{char_block}\n\n"
        f"【故事大纲】：\n{raw_outline}{truncated_note}\n\n"
        f"【风格与节奏要求】：{style_block}\n"
        f"【目标章节数】：严格规划 {chapter_count} 章（index 从 1 到 {chapter_count}）。\n"
        "请直接返回纯 JSON："
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ], warning


def _to_cn_chapter_num(n: int) -> str:
    cn_nums = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 1 <= n <= 10:
        return cn_nums[n]
    if 10 < n < 20:
        return "十" + (cn_nums[n % 10] if n % 10 > 0 else "")
    if 20 <= n < 100:
        return cn_nums[n // 10] + "十" + (cn_nums[n % 10] if n % 10 > 0 else "")
    return str(n)


def parse_chapter_plan(raw_text: str, expected_count: int = 5) -> List[Dict[str, Any]]:
    """
    解析模型返回的大纲拆章结果：
    优先解析 JSON -> 正则提取 JSON 块兜底 -> 纯文本行级解析兜底
    """
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return []

    # 剥离 ```json ... ``` 围栏
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    parsed_obj: Any = None
    try:
        parsed_obj = json.loads(cleaned)
    except Exception:
        # 正则兜底提取最外层 { ... } 或 [ ... ]
        brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if brace_match:
            try:
                parsed_obj = json.loads(brace_match.group(1))
            except Exception:
                parsed_obj = None

    raw_chapters: List[Any] = []
    if isinstance(parsed_obj, dict) and isinstance(parsed_obj.get("chapters"), list):
        raw_chapters = parsed_obj["chapters"]
    elif isinstance(parsed_obj, list):
        raw_chapters = parsed_obj

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_chapters, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            title = f"第{_to_cn_chapter_num(idx)}章 · 待定标题"

        raw_points = item.get("points")
        points: List[str] = []
        if isinstance(raw_points, list):
            points = [str(p).strip() for p in raw_points if str(p).strip()]
        elif isinstance(raw_points, str) and raw_points.strip():
            points = [
                line.lstrip("·-•*0123456789.、 ").strip()
                for line in raw_points.splitlines()
                if line.strip()
            ]

        if not points:
            points = ["依据大纲推进本章核心情节"]

        normalized.append(
            {
                "index": int(item.get("index") or idx),
                "title": title,
                "points": points[:5],
            }
        )

    if normalized:
        return normalized

    # 终极降级兜底：若模型返回的是纯文本分章草稿，按章节标题行切分
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    current_title = ""
    current_points: List[str] = []
    for line in lines:
        clean_line = re.sub(r"^[#*>\-\s]+", "", line).strip()
        if re.match(r"^(第\s*[\d零一二三四五六七八九十百]+\s*[章回节场])", clean_line):
            if current_title:
                normalized.append(
                    {
                        "index": len(normalized) + 1,
                        "title": current_title,
                        "points": current_points[:5] or ["依据大纲展开本章情节"],
                    }
                )
            current_title = clean_line[:40]
            current_points = []
        else:
            pt = clean_line.lstrip("·-•*0123456789.、 ").strip()
            if pt:
                current_points.append(pt)

    if current_title:
        normalized.append(
            {
                "index": len(normalized) + 1,
                "title": current_title,
                "points": current_points[:5] or ["依据大纲展开本章情节"],
            }
        )

    if not normalized and lines:
        # 哪怕没有标准章节头，也把文本分成首个草稿卡片返回，绝不静默丢失
        normalized.append(
            {
                "index": 1,
                "title": "第一章 · 规划草稿",
                "points": lines[:5],
            }
        )

    return normalized

