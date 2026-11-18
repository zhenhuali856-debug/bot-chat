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
    ChapterItem,
    CreateChapterRequest,
    UpdateChapterRequest,
    CharacterItem,
    CreateCharacterRequest,
    UpdateCharacterRequest,
    MaterialItem,
    CreateMaterialRequest,
    UpdateMaterialRequest,
    PromptFileItem,
    CreatePromptFileRequest,
    UpdatePromptFileRequest,
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
            # 兼容既有数据库结构：动态检查并添加 work_id 与 target_chapter_id 字段
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(sessions)").fetchall()]
            if "work_id" not in cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN work_id TEXT")
            if "target_chapter_id" not in cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN target_chapter_id TEXT")

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
            # Markdown 提示词文件表 (用于存储上传给模型的 .md 提示词文件)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'session',
                    session_id TEXT,
                    work_id TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_prompt_files_scope ON prompt_files (scope, session_id, work_id)"
            )
            # 作品正文章节表 (存储从对话中提取保存或手动编辑的章节正文)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chapters (
                    id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    word_count INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    source_session_id TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_chapters_work ON chapters (work_id, sort_order, created_at)"
            )
            # M2 角色卡表 (按作品归属，结构化存储角色设定，防 OOC)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS characters (
                    id            TEXT PRIMARY KEY,
                    work_id       TEXT NOT NULL,
                    name          TEXT NOT NULL,
                    role_type     TEXT DEFAULT '配角',
                    traits        TEXT,
                    appearance    TEXT,
                    speech_style  TEXT,
                    background    TEXT,
                    relationships TEXT,
                    notes         TEXT,
                    is_active     INTEGER DEFAULT 1,
                    created_at    REAL,
                    updated_at    REAL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_characters_work ON characters(work_id, is_active)"
            )
            # M2 素材库表 (按作品归属，存储灵感/金句/参考/设定片段)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS materials (
                    id         TEXT PRIMARY KEY,
                    work_id    TEXT NOT NULL,
                    type       TEXT DEFAULT '灵感',
                    title      TEXT,
                    content    TEXT NOT NULL,
                    tags       TEXT,
                    created_at REAL,
                    updated_at REAL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_materials_work ON materials(work_id, type)"
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
                "SELECT id, title, system_prompt, created_at, updated_at, work_id, target_chapter_id FROM sessions WHERE id = ?",
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
                    target_chapter_id=row["target_chapter_id"],
                )
        return self.create_session(session_id=session_id, work_id=work_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表 (按更新时间倒序)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.title, s.system_prompt, s.created_at, s.updated_at, s.work_id, s.target_chapter_id,
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
                    "target_chapter_id": row["target_chapter_id"],
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

                # M2：注入该作品已启用的角色卡（结构化，防OOC，上限 8 个角色、单角色设定上限 400 字）
                chars = self.list_characters(work["id"])
                active_chars = [c for c in chars if c.get("is_active")]
                if active_chars:
                    role_priority = {"主角": 0, "配角": 1, "反派": 2, "路人": 3}
                    active_chars.sort(
                        key=lambda x: (
                            role_priority.get(x.get("role_type") or "配角", 9),
                            x.get("created_at") or 0,
                        )
                    )
                    active_chars = active_chars[:8]  # MAX_CONTEXT_CHARACTERS = 8
                    char_blocks = []
                    for c in active_chars:
                        header = f"【{c['name']}｜{c.get('role_type') or '角色'}】"
                        detail_lines = []
                        for label, key in [
                            ("身份背景", "background"),
                            ("性格", "traits"),
                            ("外貌", "appearance"),
                            ("说话风格/口头禅", "speech_style"),
                            ("人物关系", "relationships"),
                            ("备注", "notes"),
                        ]:
                            val = (c.get(key) or "").strip()
                            if val:
                                detail_lines.append(f"- {label}：{val}")
                        body_str = "\n".join(detail_lines)
                        if len(body_str) > 400:
                            body_str = body_str[:400] + "…"
                        char_blocks.append(f"{header}\n{body_str}" if body_str else header)
                    system_prompt += (
                        "\n\n【本作品出场角色设定（创作对话时严格遵守，勿让人物OOC、"
                        "勿混淆说话风格与身份关系）】\n" + "\n\n".join(char_blocks)
                    )

                # 跨章节无缝承接：自动提取上一章节末尾情节作为核心上下文注入
                prev_chapter = self.get_previous_chapter_for_session(session_id)
                if prev_chapter and prev_chapter.get("tail_content"):
                    tail_text = prev_chapter["tail_content"]
                    if prev_chapter.get("word_count", 0) > len(tail_text):
                        tail_text = "……\n" + tail_text
                    prev_chapter_block = (
                        f"\n\n【前情承接 / 上一章《{prev_chapter['title']}》结尾剧情（核心上下文）】\n"
                        f"以下是上一章节正文末尾的关键内容。在构思与创作本章时，请务必无缝承接上一章的情节、场景、人物动作、心理状态与未解悬念，保证全书剧情连贯流畅，严禁出现逻辑断层与人物割裂：\n"
                        f"```\n{tail_text}\n```\n"
                        f"【续写指引】：承接上述《{prev_chapter['title']}》结尾的情节走向，延续既有人物设定与情绪基调展开本章后续创作。"
                    )
                    system_prompt += prev_chapter_block

            # 外部 Markdown 提示词文件注入：读取已启用的 .md 提示词喂给模型
            active_prompts = self.get_active_prompt_files_for_session(session_id)
            if active_prompts:
                scope_labels = {
                    "global": "全局提示词",
                    "work": "作品级提示词",
                    "session": "当前章节提示词",
                }
                prompt_sections = [
                    f"--- [{scope_labels.get(pf['scope'], '提示词')}] 文件：{pf['filename']} ---\n"
                    f"{pf['content']}\n"
                    f"--- 文件结束 ---"
                    for pf in active_prompts
                ]
                system_prompt += (
                    "\n\n【用户上传的 Markdown 提示词文件（必须完整读取并在对话中严格遵循其中的规则、设定与要求）】\n"
                    + "\n\n".join(prompt_sections)
                )

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
        target_chapter_id: Optional[str] = None,
    ) -> Optional[SessionItem]:
        """更新会话标题、人设 Prompt、归属作品或指定承接章节"""
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
            if target_chapter_id is not None:
                actual_target = target_chapter_id.strip() if isinstance(target_chapter_id, str) and target_chapter_id.strip() else None
                updates.append("target_chapter_id = ?")
                params.append(actual_target)

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
        """删除指定会话及其全部记忆与会话级 MD 提示词"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute(
                "DELETE FROM prompt_files WHERE scope = 'session' AND session_id = ?",
                (session_id,),
            )
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
        """删除作品：将该作品下章节的 work_id 置空（移回未归类），保留作品级 MD 提示词为停用全局项"""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 级联把章节的 work_id 置空
            cursor.execute(
                "UPDATE sessions SET work_id = NULL, updated_at = ? WHERE work_id = ?",
                (now, work_id),
            )
            cursor.execute(
                "UPDATE prompt_files SET work_id = NULL, scope = 'global', enabled = 0, updated_at = ? WHERE scope = 'work' AND work_id = ?",
                (now, work_id),
            )
            cursor.execute("DELETE FROM chapters WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM characters WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM materials WHERE work_id = ?", (work_id,))
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

    def get_previous_chapter_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
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
                # 检查此会话在当前作品中已经关联/保存过的所有章节
                session_chapters = [
                    ch for ch in chapters if ch.get("source_session_id") == session_id
                ]

                if session_chapters:
                    # 如果该会话已经保存过多个章节（如第3、4、5、6、7章），
                    # 说明作者在该会话中已推进到了 session_chapters 的最后一章，
                    # 那么当前继续写作的“上一章”，正是该会话产出的最新章节（如第七章）！
                    prev_chapter = session_chapters[-1]
                else:
                    # 如果该会话尚未保存过章节，检查标题是否显式指向某一章
                    matched_idx = None
                    if session_title:
                        for idx, ch in enumerate(chapters):
                            if ch.get("title") and ch["title"].strip() == session_title:
                                matched_idx = idx
                                break

                    if matched_idx is not None:
                        # 若命中了已有章节，则上一章为其前序章节
                        if matched_idx > 0:
                            prev_chapter = chapters[matched_idx - 1]
                        else:
                            prev_chapter = None
                    else:
                        # 全新章节，默认承接作品中最新写完的最后一章
                        prev_chapter = chapters[-1]

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
            # 提取末尾 800 字（若总字数少于 800 则提取全部）
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

    # ==========================================
    # Markdown 提示词文件管理 (.md Prompt Files)
    # ==========================================
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

    def create_prompt_file(self, req: CreatePromptFileRequest) -> PromptFileItem:
        """上传并保存一条 Markdown 提示词文件"""
        file_id = str(uuid.uuid4())
        now = time.time()
        scope = req.scope if req.scope in ("session", "work", "global") else "session"
        session_id = req.session_id if scope == "session" else None
        work_id = req.work_id if scope == "work" else None
        enabled_int = 1 if req.enabled else 0
        content = req.content or ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO prompt_files (id, filename, content, scope, session_id, work_id, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ) -> List[Dict[str, Any]]:
        """获取当前上下文可见的 Markdown 提示词文件列表 (含全局/作品级/会话级)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if include_all:
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
                where_clause = " OR ".join(conditions)
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

    def get_prompt_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """读取指定 Markdown 提示词文件的完整内容"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompt_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return self._row_to_prompt_file(row) if row else None

    def update_prompt_file(
        self, file_id: str, req: UpdatePromptFileRequest
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
                return self.get_prompt_file(file_id)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(file_id)
            sql = f"UPDATE prompt_files SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            conn.commit()

        return self.get_prompt_file(file_id)

    def delete_prompt_file(self, file_id: str) -> bool:
        """删除指定的 Markdown 提示词文件"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_files WHERE id = ?", (file_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_active_prompt_files_for_session(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """获取当前会话生效且已启用的 Markdown 提示词文件 (用于注入模型上下文)"""
        work = self.get_session_work(session_id)
        work_id = work["id"] if work else None
        all_visible = self.list_prompt_files(
            session_id=session_id, work_id=work_id, include_all=False
        )
        return [pf for pf in all_visible if pf["enabled"]]

    # ==========================================
    # 作品正文章节管理 (Work Chapters)
    # ==========================================
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
        self, work_id: str, req: CreateChapterRequest
    ) -> Optional[ChapterItem]:
        """在指定作品下新建一个正文章节"""
        if not self.get_work(work_id):
            return None

        chapter_id = str(uuid.uuid4())
        now = time.time()
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
                INSERT INTO chapters (id, work_id, title, content, word_count, sort_order, source_session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def list_chapters(self, work_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指定作品下的正文章节列表，或全部作品的章节"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if work_id:
                cursor.execute(
                    """
                    SELECT * FROM chapters
                    WHERE work_id = ?
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    (work_id,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM chapters ORDER BY sort_order ASC, created_at ASC"
                )
            rows = cursor.fetchall()
            return [self._row_to_chapter(r) for r in rows]

    def get_chapter(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """获取单个章节详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
            row = cursor.fetchone()
            return self._row_to_chapter(row) if row else None

    def update_chapter(
        self, chapter_id: str, req: UpdateChapterRequest
    ) -> Optional[Dict[str, Any]]:
        """更新章节标题、覆盖内容或向章节末尾追加内容"""
        existing = self.get_chapter(chapter_id)
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

            if not updates:
                return existing

            updates.append("updated_at = ?")
            params.append(now)
            params.append(chapter_id)

            cursor.execute(
                f"UPDATE chapters SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_chapter(chapter_id)

    def delete_chapter(self, chapter_id: str) -> bool:
        """删除指定作品正文章节"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    # ==========================================
    # M2a 角色卡管理 (Characters CRUD)
    # ==========================================
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
        self, work_id: str, req: CreateCharacterRequest
    ) -> Optional[CharacterItem]:
        """在指定作品下新建一个角色卡"""
        if not self.get_work(work_id):
            return None

        char_id = str(uuid.uuid4())
        now = time.time()
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
                    is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def list_characters(self, work_id: str) -> List[Dict[str, Any]]:
        """获取指定作品下的全部角色卡列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
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

    def get_character(self, char_id: str) -> Optional[Dict[str, Any]]:
        """获取单个角色卡详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            return self._row_to_character(row) if row else None

    def update_character(
        self, char_id: str, req: UpdateCharacterRequest
    ) -> Optional[Dict[str, Any]]:
        """更新角色卡信息（含启停状态）"""
        existing = self.get_character(char_id)
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

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE characters SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_character(char_id)

    def delete_character(self, char_id: str) -> bool:
        """删除单个角色卡"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    # ==========================================
    # M2b 素材库管理 (Materials CRUD)
    # ==========================================
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
        self, work_id: str, req: CreateMaterialRequest
    ) -> Optional[MaterialItem]:
        """在指定作品下新建一条创作素材"""
        if not self.get_work(work_id):
            return None

        mat_id = str(uuid.uuid4())
        now = time.time()
        mat_type = (req.type or "灵感").strip()
        title = (req.title or "").strip()
        content = req.content.strip()
        tags = (req.tags or "").strip()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO materials (id, work_id, type, title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mat_id, work_id, mat_type, title, content, tags, now, now),
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
        self, work_id: str, mat_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指定作品下的素材列表（可按类型过滤）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if mat_type and mat_type != "全部":
                cursor.execute(
                    """
                    SELECT * FROM materials
                    WHERE work_id = ? AND type = ?
                    ORDER BY created_at DESC
                    """,
                    (work_id, mat_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM materials
                    WHERE work_id = ?
                    ORDER BY created_at DESC
                    """,
                    (work_id,),
                )
            rows = cursor.fetchall()
            return [self._row_to_material(r) for r in rows]

    def get_material(self, mat_id: str) -> Optional[Dict[str, Any]]:
        """获取单条素材详情"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (mat_id,))
            row = cursor.fetchone()
            return self._row_to_material(row) if row else None

    def update_material(
        self, mat_id: str, req: UpdateMaterialRequest
    ) -> Optional[Dict[str, Any]]:
        """更新单条素材信息"""
        existing = self.get_material(mat_id)
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

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE materials SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            cursor.execute(
                "UPDATE works SET updated_at = ? WHERE id = ?",
                (now, existing["work_id"]),
            )
            conn.commit()

        return self.get_material(mat_id)

    def delete_material(self, mat_id: str) -> bool:
        """删除单条素材"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (mat_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted


# 全局单例管理器
memory_manager = SessionMemoryManager()

