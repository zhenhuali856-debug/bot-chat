import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import (
    CreateMaterialRequest,
    MaterialItem,
    UpdateMaterialRequest,
)
from app.stores.base import BaseStore


class MaterialsStore(BaseStore):
    """灵感与素材知识库 Store (按作品归属与类型/标签管理)"""

    @staticmethod
    def _row_to_material(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "work_id": row["work_id"],
            "type": row["type"] or "灵感",
            "title": row["title"] or "",
            "content": row["content"] or "",
            "tags": row["tags"] or "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_material(
        self, work_id: str, req: CreateMaterialRequest, user_id: Optional[str] = None
    ) -> Optional[MaterialItem]:
        """在指定作品下新建一条创作素材"""
        if hasattr(self, "get_work") and not getattr(self, "get_work")(work_id, user_id=user_id):
            return None

        mat_id = str(uuid.uuid4())
        now = time.time()
        uid = self._resolve_user_id(user_id)
        mat_type = (req.type or "灵感").strip()
        title = (req.title or "").strip()
        content = req.content.strip()
        tags = (req.tags or "").strip()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO materials (id, work_id, type, title, content, tags, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mat_id, work_id, mat_type, title, content, tags, now, now, uid),
            )
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, work_id),
            )
            conn.commit()

        return MaterialItem(
            id=mat_id,
            work_id=work_id,
            type=mat_type,
            title=title,
            content=content,
            tags=tags,
            created_at=now,
            updated_at=now,
        )

    def list_materials(
        self,
        work_id: str,
        mat_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取指定作品下的素材列表（可按类型过滤，支持 user_id 隔离）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            and_user = "AND user_id = ?" if user_id else ""
            if mat_type and mat_type != "全部":
                params = (work_id, mat_type, user_id) if user_id else (work_id, mat_type)
                cursor.execute(
                    f"""
                    SELECT * FROM materials
                    WHERE work_id = ? AND type = ? {and_user}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
            else:
                params = (work_id, user_id) if user_id else (work_id,)
                cursor.execute(
                    f"""
                    SELECT * FROM materials
                    WHERE work_id = ? {and_user}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
            rows = cursor.fetchall()
            return [self._row_to_material(r) for r in rows]

    def get_material(
        self, mat_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取单条素材详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM materials WHERE id = ? AND user_id = ?",
                    (mat_id, user_id),
                )
            else:
                cursor.execute("SELECT * FROM materials WHERE id = ?", (mat_id,))
            row = cursor.fetchone()
            return self._row_to_material(row) if row else None

    def update_material(
        self, mat_id: str, req: UpdateMaterialRequest, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新单条素材信息"""
        existing = self.get_material(mat_id, user_id=user_id)
        if not existing:
            return None

        now = time.time()
        updates = []
        params: List[Any] = []

        if req.type is not None:
            updates.append("type = ?")
            params.append(req.type.strip())
        if req.title is not None:
            updates.append("title = ?")
            params.append(req.title.strip())
        if req.content is not None:
            updates.append("content = ?")
            params.append(req.content.strip())
        if req.tags is not None:
            updates.append("tags = ?")
            params.append(req.tags.strip())

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(now)
        params.append(mat_id)
        if user_id:
            params.append(user_id)
            sql = f"UPDATE materials SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        else:
            sql = f"UPDATE materials SET {', '.join(updates)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_material(mat_id, user_id=user_id)

    def delete_material(
        self, mat_id: str, user_id: Optional[str] = None
    ) -> bool:
        """删除单条素材"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "DELETE FROM materials WHERE id = ? AND user_id = ?",
                    (mat_id, user_id),
                )
            else:
                cursor.execute("DELETE FROM materials WHERE id = ?", (mat_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

