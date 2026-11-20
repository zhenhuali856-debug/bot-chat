from typing import Any, Dict, List, Optional
from app.config import DB_PATH
from app.core.context import build_model_context
from app.core.database import backup_db_file, init_auth_and_isolation, init_database
from app.core.search import SearchService, extract_snippet
from app.stores.base import BaseStore
from app.stores.chapters import ChaptersStore
from app.stores.characters import CharactersStore
from app.stores.materials import MaterialsStore
from app.stores.monitor import MonitorStore
from app.stores.prompts import PromptsStore
from app.stores.sessions import SessionsStore
from app.stores.stats import StatsStore
from app.stores.users import (
    BUSINESS_TABLES,
    DEFAULT_BOT_NICKNAME,
    DEFAULT_BOT_PERSONA,
    SYSTEM_USER_ID,
    UsersStore,
)
from app.stores.works import WorksStore


class SessionMemoryManager(
    UsersStore,
    StatsStore,
    MonitorStore,
    WorksStore,
    ChaptersStore,
    CharactersStore,
    MaterialsStore,
    PromptsStore,
    SessionsStore,
):
    """
    服务端会话记忆与创作领域数据统一门面管理器 (Facade)：
    - 组合继承各个单一职责的领域 Store (Works, Chapters, Characters, Materials, Prompts, Users, Stats, Sessions)
    - 委托上下文构建器 (ContextBuilder) 与全局搜索引擎 (SearchService)
    - 保持 100% 签名与调用向后兼容性
    """

    def __init__(self, db_path: str = DB_PATH):
        super().__init__(db_path=db_path)
        self._init_db()

    def _init_db(self):
        """初始化数据表结构、迁移与安全备份"""
        init_database(self.db_path)

    def _backup_db_file(self, suffix: str = "bak") -> Optional[str]:
        return backup_db_file(self.db_path, suffix)

    def _init_auth_and_isolation(self, conn):
        return init_auth_and_isolation(conn, self.db_path)

    def get_model_context(
        self, session_id: str, max_rounds: int = 10
    ) -> List[Dict[str, str]]:
        """构造传递给大模型的上下文消息数组 (滑动窗口截断 + 创作设定 + 角色卡 + 前情承接 + 提示词)"""
        return build_model_context(self, session_id, max_rounds=max_rounds)

    def search_history(
        self, keyword: str, limit: int = 50, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """在历史会话标题和消息内容中搜索关键词"""
        return SearchService.search_history(self, keyword, limit=limit, user_id=user_id)

    def _extract_snippet(self, text: str, keyword: str, context_len: int = 40) -> str:
        """提取关键词前后一定长度的文本摘要"""
        return extract_snippet(text, keyword, context_len=context_len)

    def search_global(
        self, keyword: str, limit: int = 50, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """全局搜索扩展（支持 user_id 隔离），覆盖会话、消息、角色卡、素材库、章节 5 类数据源"""
        return SearchService.search_global(self, keyword, limit=limit, user_id=user_id)


# 全局单例管理器
memory_manager = SessionMemoryManager()
