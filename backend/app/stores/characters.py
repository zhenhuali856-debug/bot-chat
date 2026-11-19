import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.models import (
    CharacterItem,
    CreateCharacterRequest,
    UpdateCharacterRequest,
)
from app.stores.base import BaseStore


class CharactersStore(BaseStore):
    """角色卡设定库 Store (按作品归属，防 OOC)"""

    @staticmethod
    def _row_to_character(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "work_id": row["work_id"],
            "name": row["name"],
            "role_type": row["role_type"] or "配角",
            "traits": row["traits"] or "",
            "appearance": row["appearance"] or "",
            "speech_style": row["speech_style"] or "",
            "background": row["background"] or "",
            "relationships": row["relationships"] or "",
            "notes": row["notes"] or "",
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_character(
        self, work_id: str, req: CreateCharacterRequest, user_id: Optional[str] = None
    ) -> Optional[CharacterItem]:
        """在指定作品下新建一个角色卡"""
        if hasattr(self, "get_work") and not getattr(self, "get_work")(work_id, user_id=user_id):
            return None

        char_id = str(uuid.uuid4())
        now = time.time()
        uid = self._resolve_user_id(user_id)
        name = req.name.strip()
        role_type = (req.role_type or "配角").strip()
        is_active_int = 1 if req.is_active else 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO characters (
                    id, work_id, name, role_type, traits, appearance,
                    speech_style, background, relationships, notes,
                    is_active, created_at, updated_at, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    char_id,
                    work_id,
                    name,
                    role_type,
                    req.traits or "",
                    req.appearance or "",
                    req.speech_style or "",
                    req.background or "",
                    req.relationships or "",
                    req.notes or "",
                    is_active_int,
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

        return CharacterItem(
            id=char_id,
            work_id=work_id,
            name=name,
            role_type=role_type,
            traits=req.traits or "",
            appearance=req.appearance or "",
            speech_style=req.speech_style or "",
            background=req.background or "",
            relationships=req.relationships or "",
            notes=req.notes or "",
            is_active=req.is_active,
            created_at=now,
            updated_at=now,
        )

    def list_characters(
        self, work_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指定作品下的全部角色卡列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    """
                    SELECT * FROM characters
                    WHERE work_id = ? AND user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (work_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM characters
                    WHERE work_id = ?
                    ORDER BY created_at ASC
                    """,
                    (work_id,),
                )
            rows = cursor.fetchall()
            return [self._row_to_character(r) for r in rows]

    def get_character(
        self, char_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取单个角色卡详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM characters WHERE id = ? AND user_id = ?",
                    (char_id, user_id),
                )
            else:
                cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            return self._row_to_character(row) if row else None

    def update_character(
        self, char_id: str, req: UpdateCharacterRequest, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新角色卡信息（含启停状态）"""
        existing = self.get_character(char_id, user_id=user_id)
        if not existing:
            return None

        now = time.time()
        updates = []
        params: List[Any] = []

        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name.strip())
        if req.role_type is not None:
            updates.append("role_type = ?")
            params.append(req.role_type.strip())
        if req.traits is not None:
            updates.append("traits = ?")
            params.append(req.traits)
        if req.appearance is not None:
            updates.append("appearance = ?")
            params.append(req.appearance)
        if req.speech_style is not None:
            updates.append("speech_style = ?")
            params.append(req.speech_style)
        if req.background is not None:
            updates.append("background = ?")
            params.append(req.background)
        if req.relationships is not None:
            updates.append("relationships = ?")
            params.append(req.relationships)
        if req.notes is not None:
            updates.append("notes = ?")
            params.append(req.notes)
        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if req.is_active else 0)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(now)
        params.append(char_id)
        if user_id:
            params.append(user_id)
            sql = f"UPDATE characters SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        else:
            sql = f"UPDATE characters SET {', '.join(updates)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_character(char_id, user_id=user_id)

    def delete_character(
        self, char_id: str, user_id: Optional[str] = None
    ) -> bool:
        """删除单个角色卡"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "DELETE FROM characters WHERE id = ? AND user_id = ?",
                    (char_id, user_id),
                )
            else:
                cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

