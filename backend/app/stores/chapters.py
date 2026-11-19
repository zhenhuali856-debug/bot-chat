import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import (
    ChapterItem,
    ChapterPlanItem,
    ChapterVersionItem,
    CreateChapterRequest,
    CreateChapterVersionRequest,
    UpdateChapterRequest,
)
from app.stores.base import BaseStore


class ChaptersStore(BaseStore):
    """章节管理、批量拆章与版本历史快照 Store"""

    @staticmethod
    def _count_words(text: str) -> int:
        """统计章节正文字数 (去除空白字符)"""
        if not text:
            return 0
        return len("".join(text.split()))

    @staticmethod
    def _row_to_chapter(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "work_id": row["work_id"],
            "title": row["title"],
            "content": row["content"] or "",
            "word_count": row["word_count"],
            "sort_order": row["sort_order"],
            "source_session_id": row["source_session_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_chapter(
        self, work_id: str, req: CreateChapterRequest, user_id: Optional[str] = None
    ) -> Optional[ChapterItem]:
        """在指定作品下新建一个正文章节"""
        if hasattr(self, "get_work") and not getattr(self, "get_work")(work_id, user_id=user_id):
            return None

        chapter_id = str(uuid.uuid4())
        now = time.time()
        uid = self._resolve_user_id(user_id)
        content = req.content or ""
        word_count = self._count_words(content)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM chapters WHERE work_id = ?",
                (work_id,),
            )
            next_order = cursor.fetchone()[0] + 1
            cursor.execute(
                """
                INSERT INTO chapters (id, work_id, title, content, word_count, sort_order, source_session_id, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter_id,
                    work_id,
                    req.title.strip(),
                    content,
                    word_count,
                    next_order,
                    req.source_session_id,
                    now,
                    now,
                    uid,
                ),
            )
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, work_id),
            )
            conn.commit()

        return ChapterItem(
            id=chapter_id,
            work_id=work_id,
            title=req.title.strip(),
            content=content,
            word_count=word_count,
            sort_order=next_order,
            source_session_id=req.source_session_id,
            created_at=now,
            updated_at=now,
        )

    def list_chapters(
        self, work_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指定作品下的正文章节列表，或全部作品的章节（支持 user_id 隔离）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if work_id and user_id:
                cursor.execute(
                    """
                    SELECT * FROM chapters
                    WHERE work_id = ? AND user_id = ?
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    (work_id, user_id),
                )
            elif work_id:
                cursor.execute(
                    """
                    SELECT * FROM chapters
                    WHERE work_id = ?
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    (work_id,),
                )
            elif user_id:
                cursor.execute(
                    """
                    SELECT * FROM chapters
                    WHERE user_id = ?
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    (user_id,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM chapters ORDER BY sort_order ASC, created_at ASC"
                )
            rows = cursor.fetchall()
            return [self._row_to_chapter(r) for r in rows]

    def get_chapter(
        self, chapter_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取单个章节详情（支持 user_id 隔离）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM chapters WHERE id = ? AND user_id = ?",
                    (chapter_id, user_id),
                )
            else:
                cursor.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
            row = cursor.fetchone()
            return self._row_to_chapter(row) if row else None

    def update_chapter(
        self,
        chapter_id: str,
        req: UpdateChapterRequest,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新章节标题、覆盖内容或向章节末尾追加内容"""
        existing = self.get_chapter(chapter_id, user_id=user_id)
        if not existing:
            return None

        now = time.time()
        new_content = existing["content"]
        content_changed = False

        if req.content is not None:
            new_content = req.content
            content_changed = True
        elif req.append_content is not None and req.append_content.strip():
            prev = (existing["content"] or "").rstrip()
            addition = req.append_content.strip()
            new_content = f"{prev}\n\n{addition}" if prev else addition
            content_changed = True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params: List[Any] = []
            if req.title is not None:
                updates.append("title = ?")
                params.append(req.title.strip())
            if content_changed:
                updates.append("content = ?")
                params.append(new_content)
                updates.append("word_count = ?")
                params.append(self._count_words(new_content))
            if req.sort_order is not None:
                updates.append("sort_order = ?")
                params.append(req.sort_order)
            if req.source_session_id is not None:
                updates.append("source_session_id = ?")
                params.append(req.source_session_id)

            if not updates:
                return existing

            updates.append("updated_at = ?")
            params.append(now)
            params.append(chapter_id)
            if user_id:
                params.append(user_id)
                sql = f"UPDATE chapters SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            else:
                sql = f"UPDATE chapters SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_chapter(chapter_id, user_id=user_id)

    def delete_chapter(
        self, chapter_id: str, user_id: Optional[str] = None
    ) -> bool:
        """删除指定作品正文章节及其历史版本快照"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                row = cursor.execute(
                    "SELECT id FROM chapters WHERE id = ? AND user_id = ?",
                    (chapter_id, user_id),
                ).fetchone()
                if not row:
                    return False
            cursor.execute(
                "DELETE FROM chapter_versions WHERE chapter_id = ?", (chapter_id,)
            )
            cursor.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def batch_create_chapters(
        self,
        work_id: str,
        plans: List[ChapterPlanItem],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        M3b 大纲拆章批量入库：
        幂等去重：按章节标题比对已有章节，绝不覆盖或重复创建已有章节
        """
        if hasattr(self, "get_work") and not getattr(self, "get_work")(work_id, user_id=user_id):
            return {"created": [], "skipped": 0}

        uid = self._resolve_user_id(user_id)
        existing_chapters = self.list_chapters(work_id=work_id, user_id=user_id)
        existing_titles = {
            (ch.get("title") or "").strip()
            for ch in existing_chapters
            if (ch.get("title") or "").strip()
        }

        created_items: List[Dict[str, Any]] = []
        skipped_count = 0
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM chapters WHERE work_id = ?",
                (work_id,),
            )
            current_max_order = cursor.fetchone()[0]

            for item in plans:
                title = (item.title or "").strip()
                if not title:
                    continue
                if title in existing_titles:
                    skipped_count += 1
                    continue

                existing_titles.add(title)
                current_max_order += 1
                chapter_id = str(uuid.uuid4())

                clean_points = [p.strip().lstrip("·-•* ") for p in (item.points or []) if p and p.strip()]
                if clean_points:
                    initial_content = "【本章规划要点】\n" + "\n".join(
                        f"· {pt}" for pt in clean_points
                    )
                else:
                    initial_content = ""

                word_count = self._count_words(initial_content)

                cursor.execute(
                    """
                    INSERT INTO chapters (id, work_id, title, content, word_count, sort_order, source_session_id, created_at, updated_at, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chapter_id,
                        work_id,
                        title,
                        initial_content,
                        word_count,
                        current_max_order,
                        None,
                        now,
                        now,
                        uid,
                    ),
                )
                created_items.append(
                    {
                        "id": chapter_id,
                        "work_id": work_id,
                        "title": title,
                        "content": initial_content,
                        "word_count": word_count,
                        "sort_order": current_max_order,
                        "source_session_id": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

            if created_items:
                cursor.execute(
                    "UPDATE works SET updated_at = ? WHERE id = ?",
                    (now, work_id),
                )
            conn.commit()

        return {"created": created_items, "skipped": skipped_count}

    @staticmethod
    def _row_to_chapter_version(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "chapter_id": row["chapter_id"],
            "title": row["title"] or "",
            "content": row["content"] or "",
            "version_no": row["version_no"],
            "note": row["note"] or "",
            "created_at": row["created_at"],
        }

    def list_chapter_versions(
        self, chapter_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指定章节的所有历史版本快照（若该章已有正文但尚无快照，自动初始化 v1 初稿快照）"""
        if user_id and not self.get_chapter(chapter_id, user_id=user_id):
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM chapter_versions
                WHERE chapter_id = ?
                ORDER BY version_no ASC, created_at ASC
                """,
                (chapter_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            chapter = self.get_chapter(chapter_id, user_id=user_id)
            if chapter and (chapter.get("content") or "").strip():
                seeded = self.create_chapter_version(
                    chapter_id,
                    CreateChapterVersionRequest(
                        title=chapter["title"],
                        content=chapter["content"],
                        note="v1 · 初稿",
                    ),
                    user_id=user_id,
                )
                return [seeded] if seeded else []
            return []

        return [self._row_to_chapter_version(r) for r in rows]

    def create_chapter_version(
        self,
        chapter_id: str,
        req: Optional[CreateChapterVersionRequest] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        为指定章节保存一个历史版本快照（单章最多保留 20 个版本，超出自动淘汰最旧版本）
        """
        chapter = self.get_chapter(chapter_id, user_id=user_id)
        if not chapter:
            return None

        uid = self._resolve_user_id(user_id)
        title = (
            req.title.strip()
            if (req and req.title and req.title.strip())
            else chapter["title"]
        )
        content = (
            req.content
            if (req and req.content is not None)
            else (chapter["content"] or "")
        )
        note = (req.note or "").strip() if req else ""
        now = time.time()
        ver_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(version_no), 0) FROM chapter_versions WHERE chapter_id = ?",
                (chapter_id,),
            )
            next_ver_no = cursor.fetchone()[0] + 1

            cursor.execute(
                """
                INSERT INTO chapter_versions (id, chapter_id, title, content, version_no, note, created_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ver_id, chapter_id, title, content, next_ver_no, note or f"v{next_ver_no} · 快照", now, uid),
            )

            cursor.execute(
                """
                SELECT id FROM chapter_versions
                WHERE chapter_id = ?
                ORDER BY version_no DESC, created_at DESC
                """,
                (chapter_id,),
            )
            all_ids = [r[0] for r in cursor.fetchall()]
            if len(all_ids) > 20:
                to_delete = all_ids[20:]
                placeholders = ",".join("?" for _ in to_delete)
                cursor.execute(
                    f"DELETE FROM chapter_versions WHERE id IN ({placeholders})",
                    tuple(to_delete),
                )

            conn.commit()

        return {
            "id": ver_id,
            "chapter_id": chapter_id,
            "title": title,
            "content": content,
            "version_no": next_ver_no,
            "note": note or f"v{next_ver_no} · 快照",
            "created_at": now,
        }

