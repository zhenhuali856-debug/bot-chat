import os
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.config import DB_PATH
from app.models import (
    MessageItem,
    SessionItem,
    WorkItem,
    CreateWorkRequest,
    UpdateWorkRequest,
)


class SessionMemoryManager:
    """
    服务端会话记忆管理器 (基于 SQLite + 滑动窗口机制)
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
            # 作品表 (M1 新增)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS works (
                    id          TEXT PRIMARY KEY,
                    title       TEXT NOT NULL,
                    genre       TEXT,
                    summary     TEXT,
                    outline     TEXT,
                    target_words INTEGER DEFAULT 0,
                    status      TEXT DEFAULT 'draft',
                    created_at  REAL,
                    updated_at  REAL
                )
                """
            )
            # 会话元数据表 (即章节)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    system_prompt TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    work_id TEXT
                )
                """
            )
            # 兼容既有数据库结构：动态检查并添加 work_id 字段
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(sessions)").fetchall()]
            if "work_id" not in cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN work_id TEXT")

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
            # 全局助手设定表 (保存全局昵称与默认人设)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # 初始化默认助手昵称和人设 (M0 创作教练)
            cursor.execute(
                "INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_nickname', '灵感兔')"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_persona', '你是一位专业、富有灵气的创作教练与编辑，擅长为小说、剧本、文案提供构思、润色与结构建议，始终尊重作者的创作意图与独特声音。')"
            )
            conn.commit()

    def create_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = "新建对话",
        system_prompt: Optional[str] = None,
        work_id: Optional[str] = None,
    ) -> SessionItem:
        """创建新会话/章节"""
        sid = session_id or str(uuid.uuid4())
        prompt = system_prompt
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO sessions (id, title, system_prompt, created_at, updated_at, work_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sid, title, prompt, now, now, work_id),
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

    def get_or_create_session(self, session_id: Optional[str], work_id: Optional[str] = None) -> SessionItem:
        """获取或创建指定 session_id"""
        if not session_id:
            return self.create_session(work_id=work_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, system_prompt, created_at, updated_at, work_id FROM sessions WHERE id = ?",
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
                    work_id=row["work_id"],
                )
        return self.create_session(session_id=session_id, work_id=work_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表 (按更新时间倒序)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id,
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
                    "work_id": row["work_id"],
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
    ) -> int:
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
        构造传递给大模型的上下文消息数组 (滑动窗口截断机制 + 创作设定注入)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT system_prompt, work_id FROM sessions WHERE id = ?",
                (session_id,),
            )
            s_row = cursor.fetchone()
            bot_settings = self.get_bot_settings()
            nickname = bot_settings.get("bot_nickname", "灵感兔")
            persona = bot_settings.get(
                "bot_persona", "你是一位专业、富有灵气的创作教练与编辑。"
            )

            system_prompt = (
                f"【核心设定与身份要求】\n"
                f"你的名字是：{nickname}。\n"
                f"你的性格与人设：{persona}。\n"
                f"【行为准则】：\n"
                f"1. 在任何时候被问及名字、身份或在聊天时，你都必须自称【{nickname}】，绝对不要说自己是 DeepSeek 或其他公司的 AI！\n"
                f"2. 你的说话语气、用词习惯必须完全符合上述性格与人设（如富有灵气、循循善诱、提供启发式构思与结构建议）。\n"
                f"3. 始终尊重作者的创作意图与独特表达，以作品故事和创作为核心展开交流。"
            )
            if s_row and s_row["system_prompt"] and s_row["system_prompt"] not in [
                "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。", ""
            ]:
                system_prompt += f"\n【当前章节特别补充设定】：{s_row['system_prompt']}"

            # M1 创作上下文注入：若当前章节绑定了作品，注入作品设定 (在全局人设之后、历史记录之前)
            work = self.get_session_work(session_id)
            if work:
                work_block = (
                    f"\n【作品设定（当前创作项目，仅供参考）】\n"
                    f"作品名：《{work['title']}》\n"
                    f"体裁：{work.get('genre') or '未指定'}\n"
                    f"简介：{work.get('summary') or '无'}\n"
                    f"大纲：{work.get('outline') or '无'}\n"
                    f"请在上述作品的世界观、人物与风格基调下与作者协作，不要偏离体裁与既定设定。"
                )
                system_prompt += work_block

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

        messages = [{"role": "system", "content": system_prompt}]
        for row in reversed(recent_rows):
            messages.append({"role": row["role"], "content": row["content"]})

        return messages

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        work_id: Optional[str] = None,
    ) -> Optional[SessionItem]:
        """更新会话标题、人设 Prompt 或归属作品"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if system_prompt is not None:
                updates.append("system_prompt = ?")
                params.append(system_prompt)
            if work_id is not None:
                # 允许传入空字符串或已选作品 ID
                actual_work_id = work_id.strip() if isinstance(work_id, str) and work_id.strip() else None
                updates.append("work_id = ?")
                params.append(actual_work_id)

            if not updates:
                return self.get_or_create_session(session_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(session_id)

            sql = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_or_create_session(session_id)

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

    def delete_message(
        self,
        message_id: int,
        session_id: Optional[str] = None,
        truncate_after: bool = False,
    ):
        """删除指定单条消息 (若 truncate_after 为 True 则同时删除该消息及之后的所有消息)"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                if truncate_after:
                    cursor.execute(
                        "DELETE FROM messages WHERE session_id = ? AND id >= ?",
                        (session_id, message_id),
                    )
                else:
                    cursor.execute(
                        "DELETE FROM messages WHERE id = ? AND session_id = ?",
                        (message_id, session_id),
                    )
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id),
                )
            else:
                if truncate_after:
                    cursor.execute("DELETE FROM messages WHERE id >= ?", (message_id,))
                else:
                    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            conn.commit()

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """导出单个会话及其全部对话消息 (标准 JSON 数据)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
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

    def export_all_sessions(self) -> Dict[str, Any]:
        """导出所有会话及其所有历史消息 (全量数据备份)"""
        sessions_list = self.list_sessions()
        all_data = []
        for s in sessions_list:
            s_detail = self.export_session(s["id"])
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
    ) -> SessionItem:
        """导入单条会话及其消息记录"""
        now = time.time()
        final_title = title or "导入的对话"
        new_session = self.create_session(title=final_title, system_prompt=system_prompt)
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
                    INSERT INTO messages (session_id, role, content, reasoning_content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sid, role, content, reasoning, m_time),
                )

            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, sid),
            )
            conn.commit()

        return self.get_or_create_session(sid)

    def search_history(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """在历史会话标题和消息内容中搜索关键词，返回匹配的会话及消息上下文片段"""
        keyword = keyword.strip()
        if not keyword:
            return []

        pattern = f"%{keyword}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. 查找标题匹配的会话
            cursor.execute(
                """
                SELECT id, title, system_prompt, created_at, updated_at
                FROM sessions
                WHERE title LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (pattern, limit),
            )
            title_matched_sessions = {row["id"]: dict(row) for row in cursor.fetchall()}

            # 2. 查找消息正文匹配的消息
            cursor.execute(
                """
                SELECT m.id, m.session_id, m.role, m.content, m.created_at, s.title as session_title
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.content LIKE ? OR m.reasoning_content LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit * 2),
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
                    snippet = self._extract_snippet(row["content"], keyword)
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

    def _extract_snippet(self, text: str, keyword: str, context_len: int = 40) -> str:
        """提取关键词前后一定长度的文本摘要"""
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

    def get_bot_settings(self) -> Dict[str, str]:
        """获取开发助手/创作教练全局昵称与人设"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM bot_settings")
            rows = cursor.fetchall()
            settings = {
                "bot_nickname": "灵感兔",
                "bot_persona": "你是一位专业、富有灵气的创作教练与编辑，擅长为小说、剧本、文案提供构思、润色与结构建议，始终尊重作者的创作意图与独特声音。",
            }
            for row in rows:
                settings[row["key"]] = row["value"]
            return settings

    def update_bot_settings(
        self, bot_nickname: Optional[str] = None, bot_persona: Optional[str] = None
    ) -> Dict[str, str]:
        """更新开发助手/创作教练全局昵称与人设"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_nickname is not None:
                cursor.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_nickname', ?)",
                    (bot_nickname,),
                )
            if bot_persona is not None:
                cursor.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_persona', ?)",
                    (bot_persona,),
                )
            conn.commit()
        return self.get_bot_settings()

    # ==========================================
    # 作品管理 (Works CRUD - M1 创作工作台核心)
    # ==========================================

    def create_work(self, req: CreateWorkRequest) -> WorkItem:
        """创建新作品"""
        wid = str(uuid.uuid4())
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO works (id, title, genre, summary, outline, target_words, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)
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

    def list_works(self) -> List[Dict[str, Any]]:
        """获取所有作品列表 (按更新时间倒序)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.id, w.title, w.genre, w.summary, w.outline, w.target_words, w.status, w.created_at, w.updated_at,
                       COUNT(s.id) as session_count
                FROM works w
                LEFT JOIN sessions s ON w.id = s.work_id
                GROUP BY w.id
                ORDER BY w.updated_at DESC
                """
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

    def get_work(self, work_id: str) -> Optional[Dict[str, Any]]:
        """获取指定作品详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
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

    def update_work(self, work_id: str, req: UpdateWorkRequest) -> Optional[Dict[str, Any]]:
        """更新作品属性 (标题、体裁、简介、大纲、目标字数、状态等)"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
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
                return self.get_work(work_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(work_id)

            sql = f"UPDATE works SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_work(work_id)

    def delete_work(self, work_id: str):
        """删除作品：将该作品下章节的 work_id 置空（移回未归类），不删除章节，然后删除作品"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 级联把章节的 work_id 置空
            cursor.execute(
                "UPDATE sessions SET work_id = NULL, updated_at = ? WHERE work_id = ?",
                (now, work_id),
            )
            cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
            conn.commit()

    def get_sessions_by_work(self, work_id: Optional[str]) -> List[Dict[str, Any]]:
        """获取指定作品下的所有章节列表 (若 work_id 为空则返回未归类章节)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if work_id:
                cursor.execute(
                    """
                    SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id,
                           COUNT(m.id) as message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.work_id = ?
                    GROUP BY s.id
                    ORDER BY s.updated_at DESC
                    """,
                    (work_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id,
                           COUNT(m.id) as message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.work_id IS NULL OR s.work_id = ''
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


# 全局单例管理器
memory_manager = SessionMemoryManager()

