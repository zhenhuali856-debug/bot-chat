"""
后台数据层 Mixin (向前兼容适配层，领域逻辑已拆解至 app.stores.* 与 app.core.database)
"""
from typing import Optional
from app.core.database import (
    BUSINESS_TABLES,
    DEFAULT_BOT_NICKNAME,
    DEFAULT_BOT_PERSONA,
    SYSTEM_USER_ID,
    backup_db_file,
    init_auth_and_isolation,
)
from app.stores.stats import StatsStore
from app.stores.users import UsersStore


class AdminStoreMixin(UsersStore, StatsStore):
    """向后兼容 Mixin，继承用户与统计 Store 并桥接数据库初始化备份方法"""

    def _backup_db_file(self, suffix: str = "bak") -> Optional[str]:
        return backup_db_file(self.db_path, suffix)

    def _init_auth_and_isolation(self, conn):
        return init_auth_and_isolation(conn, self.db_path)
