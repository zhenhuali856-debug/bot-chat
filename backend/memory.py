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
            # 全局助手设定表 (保存全局昵称与默认人设)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # 初始化默认助手昵称和人设
            cursor.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_nickname', 'Rabbit AI')")
            cursor.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_persona', '你是由 DeepSeek 驱动的高级全栈开发助手，擅长分析、架构与编写高质量代码，回答准确专业、富有逻辑。')")
            conn.commit()

    def create_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = "新建对话",
        system_prompt: Optional[str] = None,
    ) -> SessionItem:
        """创建新会话"""
        sid = session_id or str(uuid.uuid4())
        prompt = system_prompt  # 留空时动态继承全局设置
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
            bot_settings = self.get_bot_settings()
            nickname = bot_settings.get("bot_nickname", "小p")
            persona = bot_settings.get("bot_persona", "你是一个率真，内心敏感的小女孩")
            
            # 强化系统指令，确保大模型沉浸在人设中
            system_prompt = (
                f"【核心设定与身份要求】\n"
                f"你的名字是：{nickname}。\n"
                f"你的性格与人设：{persona}。\n"
                f"【行为准则】：\n"
                f"1. 在任何时候被问及名字、身份或在聊天时，你都必须自称【{nickname}】，绝对不要说自己是 DeepSeek 或其他公司的 AI！\n"
                f"2. 你的说话语气、用词习惯必须完全符合上述性格与人设（如情感表达、语调特征等）。\n"
                f"3. 即使面对开发、技术或日常问题，也请以【{nickname}】的身份自然交流。"
            )
            if s_row and s_row["system_prompt"] and s_row["system_prompt"] not in ["你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。", ""]:
                system_prompt += f"\n【当前对话特别补充设定】：{s_row['system_prompt']}"

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

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Optional[SessionItem]:
        """更新会话标题或人设 Prompt"""
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
                SELECT role, content, reasoning_content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            )
            m_rows = cursor.fetchall()

            return {
                "version": "1.0",
                "app": "Rabbit AI",
                "export_time": time.time(),
                "session": {
                    "id": s_row["id"],
                    "title": s_row["title"],
                    "system_prompt": s_row["system_prompt"],
                    "created_at": s_row["created_at"],
                    "updated_at": s_row["updated_at"],
                },
                "messages": [
                    {
                        "role": row["role"],
                        "content": row["content"],
                        "reasoning_content": row["reasoning_content"] or "",
                        "created_at": row["created_at"],
                    }
                    for row in m_rows
                ],
            }

    def export_all_sessions(self) -> Dict[str, Any]:
        """导出所有会话及其消息记录 (全量备份数据)"""
        sessions_list = self.list_sessions()
        all_data = []
        for s in sessions_list:
            exported = self.export_session(s["id"])
            if exported:
                all_data.append(exported)

        return {
            "version": "1.0",
            "app": "Rabbit AI",
            "export_time": time.time(),
            "total_sessions": len(all_data),
            "sessions": all_data,
        }

    def import_session_data(
        self,
        title: Optional[str],
        system_prompt: Optional[str],
        messages: List[Dict[str, Any]],
    ) -> SessionItem:
        """从数据中导入创建新会话及所有消息记录"""
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
                # 如果包含原创建时间则继承，否则顺延微秒以保持顺序
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

                # 每个会话最多提炼展示 3 个匹配片段
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
        """获取开发助手全局昵称与人设"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM bot_settings")
            rows = cursor.fetchall()
            settings = {
                "bot_nickname": "Rabbit AI",
                "bot_persona": "你是由 DeepSeek 驱动的高级全栈开发助手，擅长分析、架构与编写高质量代码，回答准确专业、富有逻辑。"
            }
            for row in rows:
                settings[row["key"]] = row["value"]
            return settings

    def update_bot_settings(self, bot_nickname: Optional[str] = None, bot_persona: Optional[str] = None) -> Dict[str, str]:
        """更新开发助手全局昵称与人设"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_nickname is not None:
                cursor.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_nickname', ?)",
                    (bot_nickname,)
                )
            if bot_persona is not None:
                cursor.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_persona', ?)",
                    (bot_persona,)
                )
            conn.commit()
        return self.get_bot_settings()


# 全局单例
memory_manager = SessionMemoryManager()


def format_session_to_markdown(
    session_title: str,
    system_prompt: Optional[str],
    messages: List[Dict[str, Any]],
    bot_name: str = "AI 助手",
) -> str:
    """将单个会话及对话列表格式化为美观且易读的 Markdown 文本"""
    from datetime import datetime

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_lines = [
        f"# {session_title}",
        f"> 导出时间: {now_str}",
    ]
    if system_prompt:
        md_lines.append(f"> 系统人设: {system_prompt}")
    md_lines.append("\n---\n")

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "") or ""
        m_time = msg.get("created_at")
        time_str = (
            f" ({datetime.fromtimestamp(m_time).strftime('%H:%M:%S')})"
            if m_time
            else ""
        )

        if role == "user":
            md_lines.append(f"### 👤 用户{time_str}\n\n{content}\n\n---\n")
        elif role == "assistant":
            header = f"### 🤖 {bot_name}{time_str}\n\n"
            body = ""
            if reasoning:
                quoted = "\n".join(f"> {line}" for line in reasoning.splitlines())
                body += f"> 💭 **思考过程**:\n{quoted}\n\n"
            body += f"{content}\n\n---\n"
            md_lines.append(header + body)
        else:
            md_lines.append(f"### ⚙️ {role.capitalize()}{time_str}\n\n{content}\n\n---\n")

    return "\n".join(md_lines)


def parse_markdown_to_messages(
    md_text: str,
) -> tuple[str, Optional[str], List[Dict[str, str]]]:
    """解析 Markdown 格式的聊天记录，自动提取标题、系统人设以及分轮次对话消息"""
    import re

    lines = md_text.strip().splitlines()
    title = "导入的对话"
    system_prompt = None
    messages = []

    content_start_idx = 0
    for idx, line in enumerate(lines[:15]):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("### "):
            title = stripped[2:].strip()
            content_start_idx = idx + 1
            break

    for idx in range(content_start_idx, min(content_start_idx + 15, len(lines))):
        stripped = lines[idx].strip()
        if any(
            stripped.startswith(prefix)
            for prefix in ["> 模型人设:", "> 系统人设:", "> 系统设定:", "> System Prompt:"]
        ):
            system_prompt = stripped.split(":", 1)[1].strip()
            break

    role_pattern = re.compile(
        r"^(?:###\s*(👤[^\n]*|🤖[^\n]*|⚙️[^\n]*|(?:用户|User|Human|提问)[^\n]*|(?:助手|Assistant|AI|Bot|回答)[^\n]*)|##\s*(👤[^\n]*|🤖[^\n]*|(?:用户|User)[^\n]*|(?:助手|Assistant|AI)[^\n]*)|(?:\*\*|__)(用户|User|助手|Assistant)(?:\*\*|__)\s*[:：][^\n]*)\n?",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(role_pattern.finditer(md_text))
    if not matches:
        if md_text.strip():
            messages.append(
                {"role": "user", "content": md_text.strip(), "reasoning_content": ""}
            )
        return title, system_prompt, messages

    for i in range(len(matches)):
        m = matches[i]
        matched_role_str = (m.group(1) or m.group(2) or m.group(3) or m.group(0)).lower()
        if "👤" in matched_role_str or any(keyword in matched_role_str for keyword in ["用户", "user", "human", "提问"]):
            role = "user"
        else:
            role = "assistant"

        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        block_text = md_text[start_pos:end_pos].strip()

        block_text = re.sub(r"^(?:---|\*\*\*)\s*", "", block_text).strip()
        block_text = re.sub(r"\s*(?:---|\*\*\*)$", "", block_text).strip()

        reasoning_content = ""
        reasoning_match = re.search(
            r"> (?:💭\s*)?(?:\*\*)?(?:思考过程|Reasoning)(?:\*\*)?\s*:\s*\n((?:>.*(?:\n|$))+)",
            block_text,
        )
        if reasoning_match:
            raw_lines = reasoning_match.group(1).splitlines()
            cleaned = "\n".join(
                line[1:].strip() if line.startswith(">") else line for line in raw_lines
            ).strip()
            reasoning_content = cleaned
            block_text = (
                block_text[: reasoning_match.start()]
                + block_text[reasoning_match.end() :]
            ).strip()

        if block_text or reasoning_content:
            messages.append(
                {
                    "role": role,
                    "content": block_text,
                    "reasoning_content": reasoning_content,
                }
            )

    return title, system_prompt, messages
