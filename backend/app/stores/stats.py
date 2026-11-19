import datetime
import time
from typing import Any, Dict, List, Optional
from app.stores.base import BaseStore


class StatsStore(BaseStore):
    """创作数据看板统计 Store (作品/字数/会话/趋势/进度/体裁分布聚合分析)"""

    def get_stats_overview(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """概览卡：作品数 / 章节数 / 总字数 / 角色卡 / 素材数 / 会话数 + 近期增量"""
        now = time.time()
        thirty_days_ago = now - 30 * 86400
        seven_days_ago = now - 7 * 86400

        where_user = "WHERE user_id = ?" if user_id else ""
        and_user = "AND user_id = ?" if user_id else ""
        params_user = (user_id,) if user_id else ()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            def _count(table: str, since: Optional[float] = None) -> int:
                if since is not None:
                    sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE created_at >= ? {and_user}"
                    p = (since, user_id) if user_id else (since,)
                else:
                    sql = f"SELECT COUNT(*) AS cnt FROM {table} {where_user}"
                    p = params_user
                row = cursor.execute(sql, p).fetchone()
                return int(row["cnt"] or 0) if row else 0

            works_count = _count("works")
            works_month = _count("works", thirty_days_ago)

            chapters_count = _count("chapters")
            chapters_month = _count("chapters", thirty_days_ago)

            row_words = cursor.execute(
                f"SELECT COALESCE(SUM(word_count), 0) AS total FROM chapters {where_user}",
                params_user,
            ).fetchone()
            total_words = int(row_words["total"] or 0) if row_words else 0

            row_words_7d = cursor.execute(
                f"SELECT COALESCE(SUM(word_count), 0) AS total FROM chapters WHERE updated_at >= ? {and_user}",
                (seven_days_ago, user_id) if user_id else (seven_days_ago,),
            ).fetchone()
            words_7d = int(row_words_7d["total"] or 0) if row_words_7d else 0

            characters_count = _count("characters")
            characters_month = _count("characters", thirty_days_ago)

            materials_count = _count("materials")
            materials_month = _count("materials", thirty_days_ago)

            sessions_count = _count("sessions")
            sessions_month = _count("sessions", thirty_days_ago)

        return {
            "scope": "personal" if user_id else "all",
            "works": {"value": works_count, "delta_month": works_month},
            "chapters": {"value": chapters_count, "delta_month": chapters_month},
            "total_words": {"value": total_words, "delta_7d": words_7d},
            "characters": {"value": characters_count, "delta_month": characters_month},
            "materials": {"value": materials_count, "delta_month": materials_month},
            "sessions": {"value": sessions_count, "delta_month": sessions_month},
        }

    def get_stats_trend(
        self, range_type: str = "day", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """写作趋势：按日（近 7 日）或按周（近 4 周）统计章节字数与新建章节数"""
        today = datetime.date.today()
        and_user = "AND user_id = ?" if user_id else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if range_type == "week":
                points = []
                for w_idx in range(3, -1, -1):
                    end_date = today - datetime.timedelta(days=w_idx * 7)
                    start_date = end_date - datetime.timedelta(days=6)
                    start_ts = datetime.datetime.combine(start_date, datetime.time.min).timestamp()
                    end_ts = datetime.datetime.combine(end_date, datetime.time.max).timestamp()
                    iso_week = end_date.isocalendar()[1]
                    params = (start_ts, end_ts, user_id) if user_id else (start_ts, end_ts)
                    row = cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(word_count), 0) AS words, COUNT(*) AS chapters
                        FROM chapters
                        WHERE updated_at >= ? AND updated_at <= ? {and_user}
                        """,
                        params,
                    ).fetchone()
                    points.append(
                        {
                            "label": f"第{iso_week}周",
                            "words": int(row["words"] or 0),
                            "chapters": int(row["chapters"] or 0),
                        }
                    )
                return {
                    "range": "week",
                    "total_words": sum(p["words"] for p in points),
                    "points": points,
                }
            else:
                points = []
                for d_idx in range(6, -1, -1):
                    day = today - datetime.timedelta(days=d_idx)
                    start_ts = datetime.datetime.combine(day, datetime.time.min).timestamp()
                    end_ts = datetime.datetime.combine(day, datetime.time.max).timestamp()
                    params = (start_ts, end_ts, user_id) if user_id else (start_ts, end_ts)
                    row = cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(word_count), 0) AS words, COUNT(*) AS chapters
                        FROM chapters
                        WHERE updated_at >= ? AND updated_at <= ? {and_user}
                        """,
                        params,
                    ).fetchone()
                    points.append(
                        {
                            "label": day.strftime("%m-%d"),
                            "words": int(row["words"] or 0),
                            "chapters": int(row["chapters"] or 0),
                        }
                    )
                return {
                    "range": "day",
                    "total_words": sum(p["words"] for p in points),
                    "points": points,
                }

    def get_stats_works_progress(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """各作品完成率：word_count / target_words"""
        where_user = "WHERE w.user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                f"""
                SELECT w.id, w.title, w.genre, w.target_words, w.status, w.updated_at,
                       COALESCE(SUM(c.word_count), 0) AS word_count,
                       COUNT(c.id) AS chapter_count
                FROM works w
                LEFT JOIN chapters c ON c.work_id = w.id
                {where_user}
                GROUP BY w.id
                ORDER BY w.updated_at DESC
                """,
                params,
            ).fetchall()

            result = []
            for r in rows:
                wc = int(r["word_count"] or 0)
                tw = int(r["target_words"] or 0)
                pct = min(100, round(wc / tw * 100)) if tw > 0 else 0
                result.append(
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "genre": r["genre"] or "未分类",
                        "word_count": wc,
                        "target_words": tw,
                        "chapter_count": int(r["chapter_count"] or 0),
                        "progress_pct": pct,
                        "status": r["status"] or "draft",
                    }
                )
            return result

    def get_stats_genre_distribution(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """作品体裁分布统计"""
        where_user = "WHERE user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()
        palette = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#0ea5e9", "#64748b"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                f"""
                SELECT COALESCE(NULLIF(TRIM(genre), ''), '其他') AS genre_name, COUNT(*) AS cnt
                FROM works
                {where_user}
                GROUP BY genre_name
                ORDER BY cnt DESC
                """,
                params,
            ).fetchall()

            total = sum(int(r["cnt"] or 0) for r in rows)
            if total == 0:
                return []

            items = []
            for idx, r in enumerate(rows):
                cnt = int(r["cnt"] or 0)
                items.append(
                    {
                        "name": r["genre_name"],
                        "count": cnt,
                        "percent": round(cnt / total * 100),
                        "color": palette[idx % len(palette)],
                    }
                )
            return items

