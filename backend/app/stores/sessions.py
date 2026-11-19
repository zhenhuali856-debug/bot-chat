import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import SessionItem
from app.stores.base import BaseStore


class SessionsStore(BaseStore):
    """会话 (章节对话) & 消息历史 & 创作教练人设 Store"""

    def create_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = "新建对话",
        system_prompt: Optional[str] = None,
        work_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionItem:
        """创建新会话/章节"""
        sid = session_id or str(uuid.uuid4())
        prompt = system_prompt
        now = time.time()
        uid = self._resolve_user_id(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO sessions (id, title, system_prompt, created_at, updated_at, work_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, title, prompt, now, now, work_id, uid),
            )
            conn.commit()
        return SessionItem(
            id=sid,
            title=title,
            system_prompt=prompt,
            created_at=now,
            updated_at=now,
            message_count=0,
            work_id=work_id,
        )

    def get_session(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Optional[SessionItem]:
        """按 ID（及可选 user_id 隔离）获取单个会话"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT id, title, system_prompt, created_at, updated_at, work_id, target_chapter_id FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                )
            else:
                cursor.execute(
                    "SELECT id, title, system_prompt, created_at, updated_at, work_id, target_chapter_id FROM sessions WHERE id = ?",
                    (session_id,),
                )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (session_id,),
            )
            count = cursor.fetchone()[0]
            return SessionItem(
                id=row["id"],
                title=row["title"],
                system_prompt=row["system_prompt"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=count,
                work_id=row["work_id"],
                target_chapter_id=row["target_chapter_id"],
            )

    def get_or_create_session(
        self,
        session_id: Optional[str],
        work_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionItem:
        """获取或创建指定 session_id（带 user_id 隔离校验）"""
        if not session_id:
            return self.create_session(work_id=work_id, user_id=user_id)
        existing = self.get_session(session_id, user_id=user_id)
        if existing:
            return existing
        # 若该 session_id 属于他人，避免越权覆写，创建全新会话
        if user_id and self.get_session(session_id, user_id=None) is not None:
            return self.create_session(work_id=work_id, user_id=user_id)
        return self.create_session(session_id=session_id, work_id=work_id, user_id=user_id)

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取会话列表 (按更新时间倒序，支持 user_id 隔离)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clause = "WHERE s.user_id = ?" if user_id else ""
            params = (user_id,) if user_id else ()
            cursor.execute(
                f"""
                SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id, s.target_chapter_id,
                       COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                {where_clause}
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                """,
                params,
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "system_prompt": row["system_prompt"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "work_id": row["work_id"],
                    "target_chapter_id": row["target_chapter_id"],
                    "message_count": row["message_count"],
                }
                for row in rows
            ]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        reasoning_content: Optional[str] = "",
        user_id: Optional[str] = None,
    ) -> int:
        """记录单条对话消息，并刷新会话时间与首条标题"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            uid = user_id
            if not uid:
                s_row = cursor.execute(
                    "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
                ).fetchone()
                uid = s_row["user_id"] if s_row else self._resolve_user_id(None)
            cursor.execute(
                """
                INSERT INTO messages (session_id, role, content, reasoning_content, created_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, reasoning_content or "", now, uid),
            )
            msg_id = cursor.lastrowid

            # 如果是用户的首条消息，且当前会话是默认标题，则将会话标题自动命名为首条内容前 20 字
            if role == "user":
                cursor.execute(
                    "SELECT title FROM sessions WHERE id = ?", (session_id,)
                )
                row = cursor.fetchone()
                if row and row["title"] == "新建对话":
                    new_title = (
                        content[:20].strip() + ("..." if len(content) > 20 else "")
                    )
                    cursor.execute(
                        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                        (new_title, now, session_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE sessions SET updated_at = ? WHERE id = ?",
                        (now, session_id),
                    )
            else:
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id),
                )

            conn.commit()
            return msg_id

    def update_session_title(
        self, session_id: str, new_title: str, user_id: Optional[str] = None
    ) -> bool:
        """更新指定会话的标题"""
        new_title = (new_title or "").strip()
        if not new_title:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            if user_id:
                cursor.execute(
                    "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (new_title, now, session_id, user_id),
                )
            else:
                cursor.execute(
                    "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                    (new_title, now, session_id),
                )
            conn.commit()
            return cursor.rowcount > 0

    def get_messages(
        self, session_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取某个会话的所有完整消息（供前端展示，支持 user_id 隔离）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    """
                    SELECT id, role, content, reasoning_content, created_at
                    FROM messages
                    WHERE session_id = ? AND user_id = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (session_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, role, content, reasoning_content, created_at
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (session_id,),
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "reasoning_content": row["reasoning_content"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        work_id: Optional[str] = None,
        target_chapter_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionItem]:
        """更新会话标题、人设 Prompt、归属作品或指定承接章节"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params: List[Any] = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if system_prompt is not None:
                updates.append("system_prompt = ?")
                params.append(system_prompt)
            if work_id is not None:
                actual_work_id = work_id.strip() if isinstance(work_id, str) and work_id.strip() else None
                updates.append("work_id = ?")
                params.append(actual_work_id)
            if target_chapter_id is not None:
                actual_target = target_chapter_id.strip() if isinstance(target_chapter_id, str) and target_chapter_id.strip() else None
                updates.append("target_chapter_id = ?")
                params.append(actual_target)

            if not updates:
                return self.get_session(session_id, user_id=user_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(session_id)
            if user_id:
                params.append(user_id)
                sql = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            else:
                sql = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_session(session_id, user_id=user_id)

    def delete_session(self, session_id: str, user_id: Optional[str] = None):
        """删除指定会话及其全部记忆与会话级 MD 提示词"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                row = cursor.execute(
                    "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
                if not row:
                    return
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute(
                "DELETE FROM prompt_files WHERE scope = 'session' AND session_id = ?",
                (session_id,),
            )
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    def clear_session_messages(self, session_id: str, user_id: Optional[str] = None):
        """清空某个会话的消息记录，保留会话本身"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                row = cursor.execute(
                    "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
                if not row:
                    return
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (time.time(), session_id),
            )
            conn.commit()

    def delete_message(
        self,
        message_id: int,
        session_id: Optional[str] = None,
        truncate_after: bool = False,
        user_id: Optional[str] = None,
    ):
        """删除指定单条消息 (若 truncate_after 为 True 则同时删除该消息及之后的所有消息)"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            and_user = "AND user_id = ?" if user_id else ""
            if session_id:
                if truncate_after:
                    params = (session_id, message_id, user_id) if user_id else (session_id, message_id)
                    cursor.execute(
                        f"DELETE FROM messages WHERE session_id = ? AND id >= ? {and_user}",
                        params,
                    )
                else:
                    params = (message_id, session_id, user_id) if user_id else (message_id, session_id)
                    cursor.execute(
                        f"DELETE FROM messages WHERE id = ? AND session_id = ? {and_user}",
                        params,
                    )
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id),
                )
            else:
                if truncate_after:
                    params = (message_id, user_id) if user_id else (message_id,)
                    cursor.execute(f"DELETE FROM messages WHERE id >= ? {and_user}", params)
                else:
                    params = (message_id, user_id) if user_id else (message_id,)
                    cursor.execute(f"DELETE FROM messages WHERE id = ? {and_user}", params)
            conn.commit()

    def export_session(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """导出单个会话及其全部对话消息 (标准 JSON 数据)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT id, title, system_prompt, created_at, updated_at FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                )
            else:
                cursor.execute(
                    "SELECT id, title, system_prompt, created_at, updated_at FROM sessions WHERE id = ?",
                    (session_id,),
                )
            s_row = cursor.fetchone()
            if not s_row:
                return None

            cursor.execute(
                """
                SELECT id, role, content, reasoning_content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            )
            m_rows = cursor.fetchall()

            return {
                "session": {
                    "id": s_row["id"],
                    "title": s_row["title"],
                    "system_prompt": s_row["system_prompt"],
                    "created_at": s_row["created_at"],
                    "updated_at": s_row["updated_at"],
                },
                "messages": [
                    {
                        "id": m["id"],
                        "role": m["role"],
                        "content": m["content"],
                        "reasoning_content": m["reasoning_content"],
                        "created_at": m["created_at"],
                    }
                    for m in m_rows
                ],
            }

    def export_all_sessions(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """导出会话及其所有历史消息 (支持按用户隔离备份)"""
        sessions_list = self.list_sessions(user_id=user_id)
        all_data = []
        for s in sessions_list:
            s_detail = self.export_session(s["id"], user_id=user_id)
            if s_detail:
                all_data.append(s_detail)

        return {
            "version": "1.0",
            "exported_at": time.time(),
            "total_sessions": len(all_data),
            "sessions": all_data,
        }

    def import_session_data(
        self,
        title: Optional[str],
        system_prompt: Optional[str],
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> SessionItem:
        """导入单条会话及其消息记录"""
        now = time.time()
        uid = self._resolve_user_id(user_id)
        final_title = title or "导入的对话"
        new_session = self.create_session(title=final_title, system_prompt=system_prompt, user_id=uid)
        sid = new_session.id

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for idx, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "") or ""
                m_time = msg.get("created_at") or (now + idx * 0.01)

                cursor.execute(
                    """
                    INSERT INTO messages (session_id, role, content, reasoning_content, created_at, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sid, role, content, reasoning, m_time, uid),
                )

            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, sid),
            )
            conn.commit()

        return self.get_or_create_session(sid, user_id=uid)

    def get_bot_settings(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """获取创作教练昵称与人设（按用户独立隔离）"""
        uid = self._resolve_user_id(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM bot_settings WHERE user_id = ?",
                (uid,),
            )
            rows = cursor.fetchall()
            settings = {
                "bot_nickname": "灵感兔",
                "bot_persona": "你是一位专业、富有灵气的创作教练与编辑，擅长为小说、剧本、文案提供构思、润色与结构建议，始终尊重作者的创作意图与独特声音。",
            }
            for row in rows:
                settings[row["key"]] = row["value"]
            return settings

    def update_bot_settings(
        self,
        bot_nickname: Optional[str] = None,
        bot_persona: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """更新创作教练昵称与人设（按用户独立隔离）"""
        uid = self._resolve_user_id(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_nickname is not None:
                cursor.execute(
                    """
                    INSERT INTO bot_settings (user_id, key, value) VALUES (?, 'bot_nickname', ?)
                    ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
                    """,
                    (uid, bot_nickname),
                )
            if bot_persona is not None:
                cursor.execute(
                    """
                    INSERT INTO bot_settings (user_id, key, value) VALUES (?, 'bot_persona', ?)
                    ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
                    """,
                    (uid, bot_persona),
                )
            conn.commit()
        return self.get_bot_settings(user_id=uid)

