import os
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# SQLite 数据库持久化路径
DB_PATH = os.path.join(os.path.dirname(__file__), "chat_memory.db")


class MessageItem(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str  # system, user, assistant
    content: str
    reasoning_content: Optional[str] = ""
    created_at: float = Field(default_factory=time.time)


class SessionItem(BaseModel):
    id: str
    title: str
    system_prompt: Optional[str] = "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    message_count: int = 0


class SessionMemoryManager:
    """
    服务端会话记忆管理器 (基于 SQLite + 滑动窗口机制)
    
    设计核心思路:
    1. 服务端掌控: 会话状态由后端唯一控制，前端只传 session_id，解耦且安全。
    2. 真正持久化: 采用 SQLite 轻量级数据库，服务重启、前端刷新均不丢失记忆。
    3. 滑动窗口防溢出: 自动控制送入大模型的历史轮次(默认保留最近 10 轮)，防止 Token 溢出与费用爆炸。
    4. 思考链留存: 支持 DeepSeek-R1 的 reasoning_content 记忆与还原。
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 会话元数据表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    system_prompt TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            # 消息历史表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    reasoning_content TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, created_at)"
            )
            conn.commit()

    def create_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = "新建对话",
        system_prompt: Optional[str] = None,
    ) -> SessionItem:
        """创建新会话"""
        sid = session_id or str(uuid.uuid4())
        prompt = (
            system_prompt
            or "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。"
        )
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO sessions (id, title, system_prompt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, title, prompt, now, now),
            )
            conn.commit()
        return SessionItem(
            id=sid,
            title=title,
            system_prompt=prompt,
            created_at=now,
            updated_at=now,
            message_count=0,
        )

    def get_or_create_session(self, session_id: Optional[str]) -> SessionItem:
        """获取或创建指定 session_id"""
        if not session_id:
            return self.create_session()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, system_prompt, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
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
                )
        return self.create_session(session_id=session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表 (按更新时间倒序)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "system_prompt": row["system_prompt"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
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
    ):
        """记录单条对话消息，并刷新会话时间与首条标题"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (session_id, role, content, reasoning_content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, reasoning_content or "", now),
            )

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

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取某个会话的所有完整消息（供前端展示）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
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

    def get_model_context(
        self, session_id: str, max_rounds: int = 10
    ) -> List[Dict[str, str]]:
        """
        构造传递给大模型的上下文消息数组 (滑动窗口截断机制)
        
        策略:
        1. 必须始终携带 System Prompt 置顶；
        2. 选取最近的 max_rounds 轮对话 (1轮 = 1条user + 1条assistant，即最多 2*max_rounds 条)；
        3. 避免 Token 暴涨，同时保持即时多轮上下文连贯性。
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT system_prompt FROM sessions WHERE id = ?",
                (session_id,),
            )
            s_row = cursor.fetchone()
            system_prompt = (
                s_row["system_prompt"]
                if s_row and s_row["system_prompt"]
                else "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。"
            )

            # 抓取最近的 2 * max_rounds 条消息
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

        # 倒序反转，恢复自然时间顺序
        messages = [{"role": "system", "content": system_prompt}]
        for row in reversed(recent_rows):
            messages.append({"role": row["role"], "content": row["content"]})

        return messages

    def delete_session(self, session_id: str):
        """删除指定会话及其全部记忆"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    def clear_session_messages(self, session_id: str):
        """清空某个会话的消息记录，保留会话本身"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (time.time(), session_id),
            )
            conn.commit()


# 全局单例
memory_manager = SessionMemoryManager()
