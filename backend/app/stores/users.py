import os
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.core.auth import hash_password
from app.core.database import (
    BUSINESS_TABLES,
    DEFAULT_BOT_NICKNAME,
    DEFAULT_BOT_PERSONA,
    SYSTEM_USER_ID,
    backup_db_file,
)
from app.stores.base import BaseStore


class UsersStore(BaseStore):
    """用户账号、系统设置与多用户权限管理 Store"""

    def get_system_setting(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM bot_settings WHERE user_id = ? AND key = ?",
                (SYSTEM_USER_ID, key),
            )
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_system_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_settings (user_id, key, value) VALUES (?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
                """,
                (SYSTEM_USER_ID, key, str(value)),
            )
            conn.commit()

    def is_multi_user_mode(self) -> bool:
        return self.get_system_setting("multi_user_mode", "0") == "1"

    def set_multi_user_mode(self, enabled: bool) -> bool:
        self.set_system_setting("multi_user_mode", "1" if enabled else "0")
        return enabled

    @staticmethod
    def _row_to_user(row: sqlite3.Row, include_secret: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "display_name": row["display_name"] or row["username"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "last_login_at": row["last_login_at"],
        }
        if include_secret:
            data["password_hash"] = row["password_hash"]
            data["salt"] = row["salt"]
        return data

    def get_user_by_id(
        self, user_id: str, include_secret: bool = False
    ) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row, include_secret=include_secret) if row else None

    def get_user_by_username(
        self, username: str, include_secret: bool = False
    ) -> Optional[Dict[str, Any]]:
        if not username:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
            row = cursor.fetchone()
            return self._row_to_user(row, include_secret=include_secret) if row else None

    def get_default_admin_user(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE role = 'admin' AND is_active = 1 ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        """管理员：获取所有用户列表及其名下作品数/章节数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at ASC")
            rows = cursor.fetchall()

            cursor.execute("SELECT user_id, COUNT(*) AS cnt FROM works GROUP BY user_id")
            works_map = {r["user_id"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("SELECT user_id, COUNT(*) AS cnt FROM chapters GROUP BY user_id")
            chapters_map = {r["user_id"]: r["cnt"] for r in cursor.fetchall()}

            result = []
            for row in rows:
                u = self._row_to_user(row)
                u["work_count"] = works_map.get(u["id"], 0)
                u["chapter_count"] = chapters_map.get(u["id"], 0)
                result.append(u)
            return result

    def create_user(
        self,
        username: str,
        password: str,
        display_name: Optional[str] = None,
        role: str = "member",
    ) -> Dict[str, Any]:
        clean_username = (username or "").strip()
        if not clean_username:
            raise ValueError("用户名不能为空")
        if len(password or "") < 6:
            raise ValueError("密码长度不能少于 6 位")
        clean_role = role if role in ("admin", "member") else "member"

        uid = str(uuid.uuid4())
        pwd_hash, salt = hash_password(password)
        now = time.time()
        clean_display = (display_name or "").strip() or clean_username

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (clean_username,))
            if cursor.fetchone():
                raise ValueError(f"用户名 '{clean_username}' 已存在")

            cursor.execute(
                """
                INSERT INTO users (id, username, password_hash, salt, role, display_name, is_active, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)
                """,
                (uid, clean_username, pwd_hash, salt, clean_role, clean_display, now),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, 'bot_nickname', ?)",
                (uid, DEFAULT_BOT_NICKNAME),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, 'bot_persona', ?)",
                (uid, DEFAULT_BOT_PERSONA),
            )
            conn.commit()

        user = self.get_user_by_id(uid)
        assert user is not None
        user["work_count"] = 0
        user["chapter_count"] = 0
        return user

    def update_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        new_password: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        existing = self.get_user_by_id(user_id)
        if not existing:
            return None

        fields: List[str] = []
        values: List[Any] = []

        if display_name is not None:
            fields.append("display_name = ?")
            values.append(display_name.strip() or existing["username"])
        if role is not None and role in ("admin", "member"):
            fields.append("role = ?")
            values.append(role)
        if is_active is not None:
            fields.append("is_active = ?")
            values.append(1 if is_active else 0)
        if new_password is not None:
            if len(new_password) < 6:
                raise ValueError("新密码长度不能少于 6 位")
            pwd_hash, salt = hash_password(new_password)
            fields.append("password_hash = ?")
            values.append(pwd_hash)
            fields.append("salt = ?")
            values.append(salt)

        if fields:
            values.append(user_id)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                    tuple(values),
                )
                conn.commit()

        return self.get_user_by_id(user_id)

    def update_user_last_login(self, user_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (time.time(), user_id),
            )
            conn.commit()

    def delete_user(
        self,
        user_id: str,
        strategy: str = "transfer",
        transfer_to_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        删除用户（RK-05 防止孤儿数据）：
        - 删除前强制备份 SQLite 数据库
        - strategy='transfer': 将该用户 8 张业务表数据转移给指定管理员
        - strategy='delete': 一并删除该用户全部业务数据
        """
        target = self.get_user_by_id(user_id)
        if not target:
            raise ValueError("用户不存在")
        if target["username"] == "admin":
            raise ValueError("不能删除系统默认管理员账号 admin")

        backup_path = backup_db_file(self.db_path, "bak")

        if strategy == "transfer":
            receiver_id = transfer_to_user_id
            if not receiver_id:
                admin_user = self.get_default_admin_user()
                receiver_id = admin_user["id"] if admin_user else None
            if not receiver_id or receiver_id == user_id:
                raise ValueError("未找到可用的数据接收管理员账号")

            with self._get_connection() as conn:
                cursor = conn.cursor()
                for table in BUSINESS_TABLES:
                    cursor.execute(
                        f"UPDATE {table} SET user_id = ? WHERE user_id = ?",
                        (receiver_id, user_id),
                    )
                cursor.execute("DELETE FROM bot_settings WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for table in BUSINESS_TABLES:
                    cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM bot_settings WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()

        return {
            "deleted_user": target["username"],
            "strategy": strategy,
            "backup_created": bool(backup_path),
        }

