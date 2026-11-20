import datetime
import time
import uuid
from typing import Any, Dict, List, Optional
from app.stores.base import BaseStore

MODEL_COLOR_MAP = {
    "deepseek-chat": "linear-gradient(135deg,#3b82f6,#8b5cf6)",
    "deepseek-reasoner": "linear-gradient(135deg,#6366f1,#a855f7)",
    "glm-4-flash": "linear-gradient(135deg,#10b981,#059669)",
    "glm-4": "linear-gradient(135deg,#059669,#047857)",
    "gemini-2.5": "linear-gradient(135deg,#f59e0b,#d97706)",
    "gemini-2.0-flash": "linear-gradient(135deg,#fbbf24,#f59e0b)",
}
DEFAULT_MODEL_COLOR = "linear-gradient(135deg,#64748b,#475569)"


class MonitorStore(BaseStore):
    """运营监控中心 Store (API 流水日志、Token 统计、模型分布、错误率与耗时聚合)"""

    def log_call(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        model: str,
        provider: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        duration_ms: int = 0,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> str:
        """记录一次模型 API 调用流水 (安全持久化，从不阻断业务主流程)"""
        record_id = str(uuid.uuid4())
        now = time.time()
        resolved_total = total_tokens or (prompt_tokens + completion_tokens)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_call_logs (
                    id, user_id, session_id, model, provider,
                    prompt_tokens, completion_tokens, total_tokens,
                    duration_ms, status, error_msg, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    user_id,
                    session_id,
                    model,
                    provider or "unknown",
                    prompt_tokens,
                    completion_tokens,
                    resolved_total,
                    max(0, int(duration_ms)),
                    status,
                    error_msg or None,
                    now,
                ),
            )
            conn.commit()
        return record_id

    def get_monitor_overview(
        self,
        range_type: str = "7d",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取运营监控概览统计及每日趋势折线数据 (近 7 日或近 30 日)"""
        days = 30 if range_type == "30d" else 7
        now = time.time()
        since_time = now - days * 86400

        where_clauses = ["created_at >= ?"]
        params: List[Any] = [since_time]

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        where_sql = "WHERE " + " AND ".join(where_clauses)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 聚合基础指标
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_calls,
                    SUM(CASE WHEN status IN ('error', 'aborted') THEN 1 ELSE 0 END) AS error_calls,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
                FROM api_call_logs
                {where_sql}
                """,
                tuple(params),
            )
            row = cursor.fetchone()
            total_calls = int(row["total_calls"] or 0)
            success_calls = int(row["success_calls"] or 0)
            error_calls = int(row["error_calls"] or 0)
            total_tokens = int(row["total_tokens"] or 0)
            avg_duration_ms = int(round(row["avg_duration_ms"] or 0))

            failure_rate = (
                round((error_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
            )

            # 按天聚合趋势数据
            cursor.execute(
                f"""
                SELECT
                    strftime('%m-%d', datetime(created_at, 'unixepoch', 'localtime')) AS day_str,
                    COUNT(*) AS day_calls,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS day_success,
                    COALESCE(SUM(total_tokens), 0) AS day_tokens
                FROM api_call_logs
                {where_sql}
                GROUP BY day_str
                ORDER BY created_at ASC
                """,
                tuple(params),
            )
            trend_rows = {r["day_str"]: r for r in cursor.fetchall()}

        # 补齐连续日期的标签与数值，确保 SVG 渲染平滑连续
        labels: List[str] = []
        calls_list: List[int] = []
        success_list: List[int] = []
        tokens_list: List[int] = []

        for i in range(days - 1, -1, -1):
            day_dt = datetime.datetime.fromtimestamp(now - i * 86400)
            day_label = day_dt.strftime("%m-%d")
            labels.append(day_label)
            if day_label in trend_rows:
                r = trend_rows[day_label]
                calls_list.append(int(r["day_calls"] or 0))
                success_list.append(int(r["day_success"] or 0))
                tokens_list.append(int(r["day_tokens"] or 0))
            else:
                calls_list.append(0)
                success_list.append(0)
                tokens_list.append(0)

        return {
            "scope": "mine" if user_id else "all",
            "range": range_type,
            "total_calls": total_calls,
            "success_calls": success_calls,
            "error_calls": error_calls,
            "failure_rate": failure_rate,
            "total_tokens": total_tokens,
            "avg_duration_ms": avg_duration_ms,
            "trend": {
                "labels": labels,
                "calls": calls_list,
                "success": success_list,
                "tokens": tokens_list,
            },
        }

    def get_monitor_model_distribution(
        self,
        range_type: str = "7d",
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取指定时间范围内的模型调用分布比例"""
        days = 30 if range_type == "30d" else 7
        now = time.time()
        since_time = now - days * 86400

        where_clauses = ["created_at >= ?"]
        params: List[Any] = [since_time]

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        where_sql = "WHERE " + " AND ".join(where_clauses)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT
                    model,
                    provider,
                    COUNT(*) AS call_count,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
                FROM api_call_logs
                {where_sql}
                GROUP BY model
                ORDER BY call_count DESC
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

        total_sum = sum(int(r["call_count"] or 0) for r in rows)
        result: List[Dict[str, Any]] = []

        for r in rows:
            count = int(r["call_count"] or 0)
            pct = round(count / total_sum * 100, 1) if total_sum > 0 else 0.0
            model_name = r["model"] or "unknown"
            color = MODEL_COLOR_MAP.get(model_name, DEFAULT_MODEL_COLOR)
            result.append(
                {
                    "model": model_name,
                    "provider": r["provider"] or "unknown",
                    "call_count": count,
                    "total_tokens": int(r["total_tokens"] or 0),
                    "avg_duration_ms": int(round(r["avg_duration_ms"] or 0)),
                    "percent": pct,
                    "color": color,
                }
            )

        return result

    def get_monitor_calls(
        self,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取调用流水明细列表（支持按状态/模型/用户筛选与分页）"""
        page = max(1, int(page))
        size = min(100, max(1, int(size)))
        offset = (page - 1) * size

        where_clauses: List[str] = []
        params: List[Any] = []

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        if status and status != "all":
            where_clauses.append("status = ?")
            params.append(status)

        if model and model != "all":
            where_clauses.append("model = ?")
            params.append(model)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM api_call_logs {where_sql}",
                tuple(params),
            )
            total = int(cursor.fetchone()["total"] or 0)

            cursor.execute(
                f"""
                SELECT
                    id, user_id, session_id, model, provider,
                    prompt_tokens, completion_tokens, total_tokens,
                    duration_ms, status, error_msg, created_at
                FROM api_call_logs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params + [size, offset]),
            )
            rows = cursor.fetchall()

        total_pages = max(1, (total + size - 1) // size) if total > 0 else 1
        items = []
        for r in rows:
            created_ts = float(r["created_at"])
            dt = datetime.datetime.fromtimestamp(created_ts)
            items.append(
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "session_id": r["session_id"],
                    "model": r["model"],
                    "provider": r["provider"],
                    "prompt_tokens": int(r["prompt_tokens"] or 0),
                    "completion_tokens": int(r["completion_tokens"] or 0),
                    "total_tokens": int(r["total_tokens"] or 0),
                    "duration_ms": int(r["duration_ms"] or 0),
                    "status": r["status"],
                    "error_msg": r["error_msg"] or "",
                    "created_at": created_ts,
                    "time_str": dt.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        return {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "items": items,
        }

