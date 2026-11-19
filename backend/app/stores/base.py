import sqlite3
from typing import Optional
from app.config import DB_PATH


class BaseStore:
    """
    底层数据访问基类：
    - 管理 SQLite 连接及 RowFactory
    - 提供统一的多租户 user_id 解析逻辑
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _resolve_user_id(self, user_id: Optional[str]) -> Optional[str]:
        if user_id:
            return user_id
        if hasattr(self, "get_default_admin_user"):
            admin = getattr(self, "get_default_admin_user")()
            return admin["id"] if admin else None
        return None

