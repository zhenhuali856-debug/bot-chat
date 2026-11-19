from typing import Any, Dict, List
from app.config import GENRE_TEMPLATES


def build_model_context(
    manager: Any, session_id: str, max_rounds: int = 10
) -> List[Dict[str, str]]:
    """
    构造传递给大模型的上下文消息数组 (滑动窗口截断机制 + 创作教练人设 + 作品大纲 + 角色卡 + 前情承接 + 提示词注入)
    """
    with manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT system_prompt, work_id, user_id FROM sessions WHERE id = ?",
            (session_id,),
        )
        s_row = cursor.fetchone()
        session_user_id = s_row["user_id"] if s_row else None
        bot_settings = manager.get_bot_settings(user_id=session_user_id)
        nickname = bot_settings.get("bot_nickname", "灵感兔")
        persona = bot_settings.get(
            "bot_persona", "你是一位专业、富有灵气的创作教练与编辑。"
        )

        system_prompt = (
            f"【核心设定与身份要求】\n"
            f"你的名字是：{nickname}。\n"
            f"你的性格与人设：{persona}。\n"
            f"【行为准则】：\n"
            f"1. 在任何时候被问及名字、身份或在聊天时，你都必须自称【{nickname}】，绝对不要说自己是 DeepSeek 或其他公司的 AI！\n"
            f"2. 你的说话语气、用词习惯必须完全符合上述性格与人设（如富有灵气、循循善诱、提供启发式构思与结构建议）。\n"
            f"3. 始终尊重作者的创作意图与独特表达，以作品故事和创作为核心展开交流。"
        )
        if s_row and s_row["system_prompt"] and s_row["system_prompt"] not in [
            "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。", ""
        ]:
            system_prompt += f"\n【当前章节特别补充设定】：{s_row['system_prompt']}"

        # M1 创作上下文注入：若当前章节绑定了作品，注入作品设定
        work = manager.get_session_work(session_id)
        if work:
            genre_name = (work.get("genre") or "").strip()
            tpl_hint = ""
            if genre_name in GENRE_TEMPLATES:
                tpl_hint = f"\n体裁结构要求：{GENRE_TEMPLATES[genre_name]['prompt_hint']}"
            work_block = (
                f"\n【作品设定（当前创作项目，仅供参考）】\n"
                f"作品名：《{work['title']}》\n"
                f"体裁：{genre_name or '未指定'}{tpl_hint}\n"
                f"简介：{work.get('summary') or '无'}\n"
                f"大纲：{work.get('outline') or '无'}\n"
                f"请在上述作品的世界观、人物与风格基调下与作者协作，不要偏离体裁与既定设定。"
            )
            system_prompt += work_block

            # M2：注入该作品已启用的角色卡（结构化，防 OOC，上限 8 个角色、单角色设定上限 400 字）
            chars = manager.list_characters(work["id"])
            active_chars = [c for c in chars if c.get("is_active")]
            if active_chars:
                role_priority = {"主角": 0, "配角": 1, "反派": 2, "路人": 3}
                active_chars.sort(
                    key=lambda x: (
                        role_priority.get(x.get("role_type") or "配角", 9),
                        x.get("created_at") or 0,
                    )
                )
                active_chars = active_chars[:8]
                char_blocks = []
                for c in active_chars:
                    header = f"【{c['name']}｜{c.get('role_type') or '角色'}】"
                    detail_lines = []
                    for label, key in [
                        ("身份背景", "background"),
                        ("性格", "traits"),
                        ("外貌", "appearance"),
                        ("说话风格/口头禅", "speech_style"),
                        ("人物关系", "relationships"),
                        ("备注", "notes"),
                    ]:
                        val = (c.get(key) or "").strip()
                        if val:
                            detail_lines.append(f"- {label}：{val}")
                    body_str = "\n".join(detail_lines)
                    if len(body_str) > 400:
                        body_str = body_str[:400] + "…"
                    char_blocks.append(f"{header}\n{body_str}" if body_str else header)
                system_prompt += (
                    "\n\n【本作品出场角色设定（创作对话时严格遵守，勿让人物OOC、"
                    "勿混淆说话风格与身份关系）】\n" + "\n\n".join(char_blocks)
                )

            # 跨章节无缝承接：自动提取上一章节末尾情节作为核心上下文注入
            prev_chapter = manager.get_previous_chapter_for_session(session_id)
            if prev_chapter and prev_chapter.get("tail_content"):
                tail_text = prev_chapter["tail_content"]
                if prev_chapter.get("word_count", 0) > len(tail_text):
                    tail_text = "……\n" + tail_text
                prev_chapter_block = (
                    f"\n\n【前情承接 / 上一章《{prev_chapter['title']}》结尾剧情（核心上下文）】\n"
                    f"以下是上一章节正文末尾的关键内容。在构思与创作本章时，请务必无缝承接上一章的情节、场景、人物动作、心理状态与未解悬念，保证全书剧情连贯流畅，严禁出现逻辑断层与人物割裂：\n"
                    f"```\n{tail_text}\n```\n"
                    f"【续写指引】：承接上述《{prev_chapter['title']}》结尾的情节走向，延续既有人物设定与情绪基调展开本章后续创作。"
                )
                system_prompt += prev_chapter_block

        # 外部 Markdown 提示词文件注入：读取已启用的 .md 提示词喂给模型
        active_prompts = manager.get_active_prompt_files_for_session(session_id)
        if active_prompts:
            scope_labels = {
                "global": "全局提示词",
                "work": "作品级提示词",
                "session": "当前章节提示词",
            }
            prompt_sections = [
                f"--- [{scope_labels.get(pf['scope'], '提示词')}] 文件：{pf['filename']} ---\n"
                f"{pf['content']}\n"
                f"--- 文件结束 ---"
                for pf in active_prompts
            ]
            system_prompt += (
                "\n\n【用户上传的 Markdown 提示词文件（必须完整读取并在对话中严格遵循其中的规则、设定与要求）】\n"
                + "\n\n".join(prompt_sections)
            )

        limit = max_rounds * 2
        cursor.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        recent_rows = cursor.fetchall()

    messages = [{"role": "system", "content": system_prompt}]
    for row in reversed(recent_rows):
        messages.append({"role": row["role"], "content": row["content"]})

    return messages

