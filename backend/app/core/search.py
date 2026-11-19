from typing import Any, Dict, List, Optional


def extract_snippet(text: str, keyword: str, context_len: int = 40) -> str:
    """提取关键词前后一定长度的文本摘要"""
    if not text:
        return ""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return text[: context_len * 2] + ("..." if len(text) > context_len * 2 else "")

    start = max(0, idx - context_len)
    end = min(len(text), idx + len(keyword) + context_len)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


class SearchService:
    """全局多表多维度聚合搜索服务 (会话/消息/角色卡/素材/正文章节)"""

    @staticmethod
    def search_history(
        manager: Any, keyword: str, limit: int = 50, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """在历史会话标题和消息内容中搜索关键词，返回匹配的会话及消息上下文片段"""
        keyword = keyword.strip()
        if not keyword:
            return []

        pattern = f"%{keyword}%"
        and_user_s = "AND user_id = ?" if user_id else ""
        and_user_m = "AND m.user_id = ?" if user_id else ""
        with manager._get_connection() as conn:
            cursor = conn.cursor()

            # 1. 查找标题匹配的会话
            p1 = (pattern, user_id, limit) if user_id else (pattern, limit)
            cursor.execute(
                f"""
                SELECT id, title, system_prompt, created_at, updated_at
                FROM sessions
                WHERE title LIKE ? {and_user_s}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                p1,
            )
            title_matched_sessions = {row["id"]: dict(row) for row in cursor.fetchall()}

            # 2. 查找消息正文匹配的消息
            p2 = (pattern, pattern, user_id, limit * 2) if user_id else (pattern, pattern, limit * 2)
            cursor.execute(
                f"""
                SELECT m.id, m.session_id, m.role, m.content, m.created_at, s.title as session_title
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE (m.content LIKE ? OR m.reasoning_content LIKE ?) {and_user_m}
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                p2,
            )
            matched_messages = cursor.fetchall()

            results_by_session: Dict[str, Dict[str, Any]] = {}

            # 先把标题匹配的会话加入结果集
            for sid, s_data in title_matched_sessions.items():
                results_by_session[sid] = {
                    "session_id": sid,
                    "session_title": s_data["title"],
                    "updated_at": s_data["updated_at"],
                    "title_matched": True,
                    "snippets": [],
                }

            # 再把消息内容匹配的片段加入
            for row in matched_messages:
                sid = row["session_id"]
                if sid not in results_by_session:
                    results_by_session[sid] = {
                        "session_id": sid,
                        "session_title": row["session_title"],
                        "updated_at": row["created_at"],
                        "title_matched": False,
                        "snippets": [],
                    }

                if len(results_by_session[sid]["snippets"]) < 3:
                    snippet = extract_snippet(row["content"], keyword)
                    results_by_session[sid]["snippets"].append({
                        "message_id": row["id"],
                        "role": row["role"],
                        "snippet": snippet,
                        "created_at": row["created_at"],
                    })

            sorted_results = sorted(
                results_by_session.values(),
                key=lambda x: x.get("updated_at", 0),
                reverse=True,
            )
            return sorted_results[:limit]

    @staticmethod
    def search_global(
        manager: Any, keyword: str, limit: int = 50, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        M4b + D2: 全局搜索扩展（带 user_id 隔离），覆盖 5 类数据源：
        1. 会话 (sessions)
        2. 消息 (messages)
        3. 角色卡 (characters)
        4. 素材库 (materials)
        5. 章节正文 (chapters)
        """
        keyword = keyword.strip()
        empty_res = {
            "query": keyword,
            "total": 0,
            "groups": {
                "sessions": [],
                "messages": [],
                "characters": [],
                "materials": [],
                "chapters": [],
            },
        }
        if not keyword:
            return empty_res

        pattern = f"%{keyword}%"
        with manager._get_connection() as conn:
            cursor = conn.cursor()

            # 1. 会话 (sessions)
            u_s = "AND s.user_id = ?" if user_id else ""
            p_s = (pattern, user_id, limit) if user_id else (pattern, limit)
            cursor.execute(
                f"""
                SELECT s.id, s.title, s.work_id, s.updated_at, w.title AS work_title
                FROM sessions s
                LEFT JOIN works w ON s.work_id = w.id
                WHERE s.title LIKE ? {u_s}
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                p_s,
            )
            session_rows = cursor.fetchall()
            sessions_list = []
            for r in session_rows:
                sessions_list.append({
                    "id": r["id"],
                    "session_id": r["id"],
                    "title": r["title"],
                    "snippet": extract_snippet(r["title"], keyword, 30),
                    "work_id": r["work_id"],
                    "work_title": r["work_title"] or "未归类",
                    "updated_at": r["updated_at"],
                })

            # 2. 消息 (messages)
            u_m = "AND m.user_id = ?" if user_id else ""
            p_m = (pattern, pattern, user_id, limit) if user_id else (pattern, pattern, limit)
            cursor.execute(
                f"""
                SELECT m.id, m.session_id, m.role, m.content, m.reasoning_content, m.created_at,
                       s.title AS session_title, s.work_id, w.title AS work_title
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                LEFT JOIN works w ON s.work_id = w.id
                WHERE (m.content LIKE ? OR m.reasoning_content LIKE ?) {u_m}
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                p_m,
            )
            msg_rows = cursor.fetchall()
            messages_list = []
            for r in msg_rows:
                target_text = r["content"] if keyword.lower() in (r["content"] or "").lower() else (r["reasoning_content"] or "")
                messages_list.append({
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "role": r["role"],
                    "title": r["session_title"] or "未命名会话",
                    "snippet": extract_snippet(target_text, keyword, 30),
                    "work_id": r["work_id"],
                    "work_title": r["work_title"] or "未归类",
                    "created_at": r["created_at"],
                })

            # 3. 角色卡 (characters)
            u_c = "AND c.user_id = ?" if user_id else ""
            p_c = (
                (pattern, pattern, pattern, pattern, pattern, user_id, limit)
                if user_id
                else (pattern, pattern, pattern, pattern, pattern, limit)
            )
            cursor.execute(
                f"""
                SELECT c.id, c.work_id, c.name, c.traits, c.speech_style, c.background, c.notes,
                       c.updated_at, w.title AS work_title
                FROM characters c
                LEFT JOIN works w ON c.work_id = w.id
                WHERE (c.name LIKE ? OR c.traits LIKE ? OR c.speech_style LIKE ? OR c.background LIKE ? OR c.notes LIKE ?) {u_c}
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                p_c,
            )
            char_rows = cursor.fetchall()
            characters_list = []
            for r in char_rows:
                field_snippet = ""
                for fname, val in [("性格", r["traits"]), ("说话风格", r["speech_style"]), ("背景", r["background"]), ("备注", r["notes"]), ("姓名", r["name"])]:
                    if val and keyword.lower() in val.lower():
                        field_snippet = f"{fname}：{extract_snippet(val, keyword, 25)}"
                        break
                if not field_snippet:
                    field_snippet = f"性格：{r['traits'] or '暂无'}"

                characters_list.append({
                    "id": r["id"],
                    "work_id": r["work_id"],
                    "title": r["name"],
                    "name": r["name"],
                    "snippet": field_snippet,
                    "work_title": r["work_title"] or "未归类",
                    "updated_at": r["updated_at"],
                })

            # 4. 素材库 (materials)
            u_mat = "AND m.user_id = ?" if user_id else ""
            p_mat = (pattern, pattern, pattern, user_id, limit) if user_id else (pattern, pattern, pattern, limit)
            cursor.execute(
                f"""
                SELECT m.id, m.work_id, m.title, m.content, m.tags, m.type,
                       m.updated_at, w.title AS work_title
                FROM materials m
                LEFT JOIN works w ON m.work_id = w.id
                WHERE (m.title LIKE ? OR m.content LIKE ? OR m.tags LIKE ?) {u_mat}
                ORDER BY m.updated_at DESC
                LIMIT ?
                """,
                p_mat,
            )
            mat_rows = cursor.fetchall()
            materials_list = []
            for r in mat_rows:
                materials_list.append({
                    "id": r["id"],
                    "work_id": r["work_id"],
                    "title": r["title"],
                    "snippet": extract_snippet(r["content"] or r["tags"] or "", keyword, 30),
                    "tags": r["tags"] or "",
                    "type": r["type"] or "灵感",
                    "work_title": r["work_title"] or "未归类",
                    "updated_at": r["updated_at"],
                })

            # 5. 章节正文 (chapters)
            u_ch = "AND ch.user_id = ?" if user_id else ""
            p_ch = (pattern, pattern, user_id, limit) if user_id else (pattern, pattern, limit)
            cursor.execute(
                f"""
                SELECT ch.id, ch.work_id, ch.title, ch.content, ch.word_count,
                       ch.updated_at, w.title AS work_title
                FROM chapters ch
                LEFT JOIN works w ON ch.work_id = w.id
                WHERE (ch.title LIKE ? OR ch.content LIKE ?) {u_ch}
                ORDER BY ch.sort_order ASC, ch.updated_at DESC
                LIMIT ?
                """,
                p_ch,
            )
            chap_rows = cursor.fetchall()
            chapters_list = []
            for r in chap_rows:
                chapters_list.append({
                    "id": r["id"],
                    "work_id": r["work_id"],
                    "title": r["title"],
                    "snippet": extract_snippet(r["content"] or "", keyword, 30),
                    "word_count": r["word_count"] or 0,
                    "work_title": r["work_title"] or "未归类",
                    "updated_at": r["updated_at"],
                })

        total = len(sessions_list) + len(messages_list) + len(characters_list) + len(materials_list) + len(chapters_list)
        return {
            "query": keyword,
            "total": total,
            "groups": {
                "sessions": sessions_list,
                "messages": messages_list,
                "characters": characters_list,
                "materials": materials_list,
                "chapters": chapters_list,
            },
        }

