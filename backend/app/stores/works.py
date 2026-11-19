import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import CreateWorkRequest, UpdateWorkRequest, WorkItem
from app.stores.base import BaseStore


class WorksStore(BaseStore):
    """作品管理与作品级会话关联 Store"""

    def create_work(
        self, req: CreateWorkRequest, user_id: Optional[str] = None
    ) -> WorkItem:
        """创建新作品"""
        wid = str(uuid.uuid4())
        now = time.time()
        uid = self._resolve_user_id(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO works (id, title, genre, summary, outline, target_words, status, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?)
                """,
                (
                    wid,
                    req.title.strip(),
                    req.genre.strip() if req.genre else None,
                    req.summary,
                    req.outline,
                    req.target_words or 0,
                    now,
                    now,
                    uid,
                ),
            )
            conn.commit()
        return WorkItem(
            id=wid,
            title=req.title.strip(),
            genre=req.genre,
            summary=req.summary,
            outline=req.outline,
            target_words=req.target_words or 0,
            status="draft",
            created_at=now,
            updated_at=now,
        )

    def list_works(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取作品列表 (按更新时间倒序，支持 user_id 隔离)"""
        where_clause = "WHERE w.user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT w.id, w.title, w.genre, w.summary, w.outline, w.target_words, w.status, w.created_at, w.updated_at,
                       COUNT(s.id) as session_count
                FROM works w
                LEFT JOIN sessions s ON w.id = s.work_id
                {where_clause}
                GROUP BY w.id
                ORDER BY w.updated_at DESC
                """,
                params,
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "genre": row["genre"],
                    "summary": row["summary"],
                    "outline": row["outline"],
                    "target_words": row["target_words"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "session_count": row["session_count"],
                }
                for row in rows
            ]

    def get_work(
        self, work_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取指定作品详情（支持 user_id 隔离）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    """
                    SELECT id, title, genre, summary, outline, target_words, status, created_at, updated_at
                    FROM works WHERE id = ? AND user_id = ?
                    """,
                    (work_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, title, genre, summary, outline, target_words, status, created_at, updated_at
                    FROM works WHERE id = ?
                    """,
                    (work_id,),
                )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def update_work(
        self, work_id: str, req: UpdateWorkRequest, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新作品属性 (标题、体裁、简介、大纲、目标字数、状态等)"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params: List[Any] = []
            if req.title is not None:
                updates.append("title = ?")
                params.append(req.title.strip())
            if req.genre is not None:
                updates.append("genre = ?")
                params.append(req.genre.strip())
            if req.summary is not None:
                updates.append("summary = ?")
                params.append(req.summary)
            if req.outline is not None:
                updates.append("outline = ?")
                params.append(req.outline)
            if req.target_words is not None:
                updates.append("target_words = ?")
                params.append(req.target_words)
            if req.status is not None:
                updates.append("status = ?")
                params.append(req.status)

            if not updates:
                return self.get_work(work_id, user_id=user_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(work_id)
            if user_id:
                params.append(user_id)
                sql = f"UPDATE works SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            else:
                sql = f"UPDATE works SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_work(work_id, user_id=user_id)

    def delete_work(self, work_id: str, user_id: Optional[str] = None):
        """删除作品：将该作品下章节的 work_id 置空（移回未归类），保留作品级 MD 提示词为停用全局项"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                row = cursor.execute(
                    "SELECT id FROM works WHERE id = ? AND user_id = ?",
                    (work_id, user_id),
                ).fetchone()
                if not row:
                    return
            cursor.execute(
                "UPDATE sessions SET work_id = NULL, updated_at = ? WHERE work_id = ?",
                (now, work_id),
            )
            cursor.execute(
                "UPDATE prompt_files SET work_id = NULL, scope = 'global', enabled = 0, updated_at = ? WHERE scope = 'work' AND work_id = ?",
                (now, work_id),
            )
            cursor.execute(
                "DELETE FROM chapter_versions WHERE chapter_id IN (SELECT id FROM chapters WHERE work_id = ?)",
                (work_id,),
            )
            cursor.execute("DELETE FROM chapters WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM characters WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM materials WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
            conn.commit()

    def get_sessions_by_work(
        self, work_id: Optional[str], user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指定作品下的所有章节列表 (若 work_id 为空则返回未归类章节，支持 user_id 隔离)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            and_user = "AND s.user_id = ?" if user_id else ""
            if work_id:
                params = (work_id, user_id) if user_id else (work_id,)
                cursor.execute(
                    f"""
                    SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id,
                           COUNT(m.id) as message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.work_id = ? {and_user}
                    GROUP BY s.id
                    ORDER BY s.updated_at DESC
                    """,
                    params,
                )
            else:
                params = (user_id,) if user_id else ()
                cursor.execute(
                    f"""
                    SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id,
                           COUNT(m.id) as message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE (s.work_id IS NULL OR s.work_id = '') {and_user}
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
                    "message_count": row["message_count"],
                }
                for row in rows
            ]

    def get_session_work(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取某个章节会话所属的作品信息 (供大模型创作上下文注入)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.id, w.title, w.genre, w.summary, w.outline, w.target_words, w.status
                FROM works w
                JOIN sessions s ON s.work_id = w.id
                WHERE s.id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def get_previous_chapter_for_session(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取当前章节会话在所属作品中的【上一章节】信息及正文末尾片段
        用于跨章节创作时自动提取上一章末尾进行无缝承接
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. 查询当前会话的 work_id 与标题
            cursor.execute(
                "SELECT id, title, work_id, target_chapter_id FROM sessions WHERE id = ?",
                (session_id,),
            )
            s_row = cursor.fetchone()
            if not s_row or not s_row["work_id"]:
                return None

            work_id = s_row["work_id"]
            session_title = (s_row["title"] or "").strip()
            target_chapter_id = s_row["target_chapter_id"]

            # 2. 查询该作品下的所有正文章节，按排序和创建时间升序排列
            cursor.execute(
                """
                SELECT id, work_id, title, content, word_count, sort_order, source_session_id, created_at
                FROM chapters
                WHERE work_id = ?
                ORDER BY sort_order ASC, created_at ASC
                """,
                (work_id,),
            )
            chapter_rows = cursor.fetchall()
            if not chapter_rows:
                return None

            chapters = [dict(r) for r in chapter_rows]
            available_chapters = [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "sort_order": c.get("sort_order", 0),
                    "word_count": c.get("word_count", 0),
                }
                for c in chapters
            ]

            # 3. 如果用户手动指定了承接章节
            prev_chapter = None
            if target_chapter_id:
                if target_chapter_id == "none":
                    return {
                        "id": "none",
                        "work_id": work_id,
                        "title": "不承接前文",
                        "sort_order": 0,
                        "tail_content": "",
                        "tail_chars": 0,
                        "word_count": 0,
                        "available_chapters": available_chapters,
                        "is_manual": True,
                    }
                for ch in chapters:
                    if ch["id"] == target_chapter_id:
                        prev_chapter = ch
                        break

            # 4. 自动跟踪识别逻辑：
            if not prev_chapter:
                session_chapters = [
                    ch for ch in chapters if ch.get("source_session_id") == session_id
                ]

                if session_chapters:
                    prev_chapter = session_chapters[-1]
                else:
                    matched_idx = None
                    if session_title:
                        for idx, ch in enumerate(chapters):
                            if ch.get("title") and ch["title"].strip() == session_title:
                                matched_idx = idx
                                break

                    if matched_idx is not None:
                        if matched_idx > 0:
                            prev_chapter = chapters[matched_idx - 1]
                        else:
                            prev_chapter = None
                    else:
                        written_chapters = [
                            ch
                            for ch in chapters
                            if (ch.get("content") or "").strip()
                            and not (ch.get("content") or "").strip().startswith("【本章规划要点】")
                        ]
                        prev_chapter = written_chapters[-1] if written_chapters else chapters[-1]

            if not prev_chapter:
                return {
                    "id": None,
                    "work_id": work_id,
                    "title": "",
                    "sort_order": 0,
                    "tail_content": "",
                    "tail_chars": 0,
                    "word_count": 0,
                    "available_chapters": available_chapters,
                    "is_manual": bool(target_chapter_id),
                }

            content = (prev_chapter.get("content") or "").strip()
            tail_limit = 800
            tail_content = content[-tail_limit:] if len(content) > tail_limit else content

            return {
                "id": prev_chapter["id"],
                "work_id": prev_chapter["work_id"],
                "title": prev_chapter["title"],
                "sort_order": prev_chapter.get("sort_order", 0),
                "tail_content": tail_content,
                "tail_chars": len(tail_content),
                "word_count": prev_chapter.get("word_count", len(content)),
                "available_chapters": available_chapters,
                "is_manual": bool(target_chapter_id),
            }

