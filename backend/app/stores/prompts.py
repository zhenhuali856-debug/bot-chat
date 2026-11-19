import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import (
    CreatePromptFileRequest,
    PromptFileItem,
    UpdatePromptFileRequest,
)
from app.stores.base import BaseStore


class PromptsStore(BaseStore):
    """Markdown 提示词模板文件 Store (全局/作品级/章节级作用域)"""

    @staticmethod
    def _row_to_prompt_file(row: sqlite3.Row) -> Dict[str, Any]:
        content = row["content"] or ""
        return {
            "id": row["id"],
            "filename": row["filename"],
            "content": content,
            "scope": row["scope"],
            "session_id": row["session_id"],
            "work_id": row["work_id"],
            "enabled": bool(row["enabled"]),
            "char_count": len(content),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_prompt_file(
        self, req: CreatePromptFileRequest, user_id: Optional[str] = None
    ) -> PromptFileItem:
        """上传并保存一条 Markdown 提示词文件"""
        file_id = str(uuid.uuid4())
        now = time.time()
        uid = self._resolve_user_id(user_id)
        scope = req.scope if req.scope in ("session", "work", "global") else "session"
        session_id = req.session_id if scope == "session" else None
        work_id = req.work_id if scope == "work" else None
        enabled_int = 1 if req.enabled else 0
        content = req.content or ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO prompt_files (id, filename, content, scope, session_id, work_id, enabled, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    req.filename.strip(),
                    content,
                    scope,
                    session_id,
                    work_id,
                    enabled_int,
                    now,
                    now,
                    uid,
                ),
            )
            conn.commit()

        return PromptFileItem(
            id=file_id,
            filename=req.filename.strip(),
            content=content,
            scope=scope,
            session_id=session_id,
            work_id=work_id,
            enabled=bool(enabled_int),
            char_count=len(content),
            created_at=now,
            updated_at=now,
        )

    def list_prompt_files(
        self,
        session_id: Optional[str] = None,
        work_id: Optional[str] = None,
        include_all: bool = False,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取当前上下文可见的 Markdown 提示词文件列表 (含全局/作品级/会话级，支持 user_id 隔离)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if include_all:
                if user_id:
                    cursor.execute(
                        "SELECT * FROM prompt_files WHERE user_id = ? ORDER BY created_at ASC",
                        (user_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM prompt_files ORDER BY created_at ASC"
                    )
            else:
                conditions = ["scope = 'global'"]
                params: List[Any] = []
                if work_id:
                    conditions.append("(scope = 'work' AND work_id = ?)")
                    params.append(work_id)
                if session_id:
                    conditions.append("(scope = 'session' AND session_id = ?)")
                    params.append(session_id)
                where_clause = f"({' OR '.join(conditions)})"
                if user_id:
                    where_clause = f"{where_clause} AND user_id = ?"
                    params.append(user_id)
                cursor.execute(
                    f"""
                    SELECT * FROM prompt_files
                    WHERE {where_clause}
                    ORDER BY
                        CASE scope WHEN 'global' THEN 1 WHEN 'work' THEN 2 ELSE 3 END,
                        created_at ASC
                    """,
                    tuple(params),
                )
            rows = cursor.fetchall()
            return [self._row_to_prompt_file(r) for r in rows]

    def get_prompt_file(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """读取指定 Markdown 提示词文件的完整内容"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM prompt_files WHERE id = ? AND user_id = ?",
                    (file_id, user_id),
                )
            else:
                cursor.execute("SELECT * FROM prompt_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return self._row_to_prompt_file(row) if row else None

    def update_prompt_file(
        self, file_id: str, req: UpdatePromptFileRequest, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新 Markdown 提示词文件 (文件名、内容、作用域、启停状态)"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params: List[Any] = []
            if req.filename is not None:
                updates.append("filename = ?")
                params.append(req.filename.strip())
            if req.content is not None:
                updates.append("content = ?")
                params.append(req.content)
            if req.scope is not None and req.scope in ("session", "work", "global"):
                updates.append("scope = ?")
                params.append(req.scope)
                if req.scope == "global":
                    updates.extend(["session_id = NULL", "work_id = NULL"])
                elif req.scope == "work":
                    updates.append("session_id = NULL")
                    if req.work_id is not None:
                        updates.append("work_id = ?")
                        params.append(req.work_id or None)
                elif req.scope == "session":
                    updates.append("work_id = NULL")
                    if req.session_id is not None:
                        updates.append("session_id = ?")
                        params.append(req.session_id or None)
            else:
                if req.session_id is not None:
                    updates.append("session_id = ?")
                    params.append(req.session_id or None)
                if req.work_id is not None:
                    updates.append("work_id = ?")
                    params.append(req.work_id or None)
            if req.enabled is not None:
                updates.append("enabled = ?")
                params.append(1 if req.enabled else 0)

            if not updates:
                return self.get_prompt_file(file_id, user_id=user_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(file_id)
            if user_id:
                params.append(user_id)
                sql = f"UPDATE prompt_files SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            else:
                sql = f"UPDATE prompt_files SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_prompt_file(file_id, user_id=user_id)

    def delete_prompt_file(
        self, file_id: str, user_id: Optional[str] = None
    ) -> bool:
        """删除指定的 Markdown 提示词文件"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "DELETE FROM prompt_files WHERE id = ? AND user_id = ?",
                    (file_id, user_id),
                )
            else:
                cursor.execute("DELETE FROM prompt_files WHERE id = ?", (file_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_active_prompt_files_for_session(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """获取当前会话生效且已启用的 Markdown 提示词文件 (用于注入模型上下文)"""
        work = getattr(self, "get_session_work")(session_id) if hasattr(self, "get_session_work") else None
        work_id = work["id"] if work else None
        all_visible = self.list_prompt_files(
            session_id=session_id, work_id=work_id, include_all=False
        )
        return [pf for pf in all_visible if pf["enabled"]]

