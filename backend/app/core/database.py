import os
import shutil
import sqlite3
import time
import uuid
from typing import Optional
from app.config import DB_PATH
from app.core.auth import hash_password

BUSINESS_TABLES = (
    "works",
    "sessions",
    "messages",
    "prompt_files",
    "chapters",
    "characters",
    "materials",
    "chapter_versions",
)

SYSTEM_USER_ID = "__system__"
DEFAULT_BOT_NICKNAME = "灵感兔"
DEFAULT_BOT_PERSONA = (
    "你是一位专业、富有灵气的创作教练与编辑，擅长为小说、剧本、文案提供构思、"
    "润色与结构建议，始终尊重作者的创作意图与独特声音。"
)


def backup_db_file(db_path: str = DB_PATH, suffix: str = "bak") -> Optional[str]:
    """在关键结构迁移或删除用户前强制备份 SQLite 数据库文件 (RK-04)"""
    try:
        if db_path and os.path.exists(db_path) and os.path.getsize(db_path) > 0:
            backup_path = f"{db_path}.{suffix}"
            shutil.copy2(db_path, backup_path)
            return backup_path
    except Exception as e:
        print(f"[DB Backup] 备份失败: {e}")
    return None


def init_auth_and_isolation(conn: sqlite3.Connection, db_path: str = DB_PATH):
    """幂等初始化 users 表、全表 user_id 列与索引、bot_settings 按用户隔离及存量回填"""
    cursor = conn.cursor()

    # 检查是否首次执行用户系统迁移，若是则在变更表结构前备份数据库 (RK-04)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    )
    first_migration = cursor.fetchone() is None
    if first_migration:
        backup_db_file(db_path, "pre_auth_migration.bak")

    # 1. 创建 users 表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'member',
            display_name  TEXT,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    REAL,
            last_login_at REAL
        )
        """
    )

    # 2. 确保默认管理员账号存在
    cursor.execute("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
    admin_row = cursor.fetchone()
    if admin_row:
        admin_id = admin_row["id"]
    else:
        admin_id = str(uuid.uuid4())
        default_pwd = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123").strip() or "admin123"
        pwd_hash, salt = hash_password(default_pwd)
        now = time.time()
        cursor.execute(
            """
            INSERT INTO users (id, username, password_hash, salt, role, display_name, is_active, created_at, last_login_at)
            VALUES (?, 'admin', ?, ?, 'admin', '系统管理员', 1, ?, NULL)
            """,
            (admin_id, pwd_hash, salt, now),
        )

    # 3. 为 8 张业务表统一添加 user_id 列、索引，并将存量 NULL 数据回填为 admin_id
    for table in BUSINESS_TABLES:
        cols = [r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        if "user_id" not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT")
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)"
        )
        cursor.execute(
            f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL OR user_id = ''",
            (admin_id,),
        )

    # 4. 迁移 bot_settings 为按 user_id 隔离的复合主键 (user_id, key)
    bs_cols = [r[1] for r in cursor.execute("PRAGMA table_info(bot_settings)").fetchall()]
    if "user_id" not in bs_cols:
        old_rows = cursor.execute("SELECT key, value FROM bot_settings").fetchall()
        cursor.execute("ALTER TABLE bot_settings RENAME TO bot_settings_legacy")
        cursor.execute(
            """
            CREATE TABLE bot_settings (
                user_id TEXT NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
            )
            """
        )
        for row in old_rows:
            k, v = row["key"], row["value"]
            owner = SYSTEM_USER_ID if k.startswith("sync_") or k in ("multi_user_mode", "auth_secret_key") else admin_id
            cursor.execute(
                "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, ?, ?)",
                (owner, k, v),
            )
        cursor.execute("DROP TABLE IF EXISTS bot_settings_legacy")

    # 确保默认人设与系统开关存在
    cursor.execute(
        "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, 'bot_nickname', ?)",
        (admin_id, DEFAULT_BOT_NICKNAME),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, 'bot_persona', ?)",
        (admin_id, DEFAULT_BOT_PERSONA),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO bot_settings (user_id, key, value) VALUES (?, 'multi_user_mode', '0')",
        (SYSTEM_USER_ID,),
    )
    conn.commit()


def init_database(db_path: str = DB_PATH):
    """初始化 SQLite 数据库及全套表结构、索引与迁移规则"""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
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

            # M3c 章节版本快照表 (记录每章手动保存的历史版本，支持并排 diff 对比)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_versions (
                    id          TEXT PRIMARY KEY,
                    chapter_id  TEXT NOT NULL,
                    title       TEXT,
                    content     TEXT NOT NULL,
                    version_no  INTEGER NOT NULL,
                    note        TEXT,
                    created_at  REAL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_versions_chapter ON chapter_versions(chapter_id, version_no)"
            )
            conn.commit()

            # D1/D2: 幂等初始化用户表、8张业务表 user_id 隔离迁移、bot_settings 隔离迁移及存量回填
            init_auth_and_isolation(conn, db_path)
    finally:
        conn.close()

