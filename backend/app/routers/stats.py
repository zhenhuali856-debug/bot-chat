from fastapi import APIRouter, Depends, Query
from app.core.auth import get_current_user
from app.core.memory import memory_manager

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _resolve_stats_user_filter(current_user: dict, scope: str = "auto"):
    """
    权限矩阵校验：
    - admin 默认看全站汇总（返回 None 表示不按 user_id 过滤），传 scope='mine' 时可只看自己；
    - member 强制只能看自己的数据（返回 current_user['id']），防止越权。
    """
    if current_user.get("role") == "admin":
        if scope == "mine":
            return current_user["id"]
        return None
    return current_user["id"]


@router.get("/overview")
async def stats_overview_endpoint(
    scope: str = Query("auto", description="admin 可选 all/mine，member 强制仅个人"),
    current_user=Depends(get_current_user),
):
    """概览卡：作品数 / 章节数 / 总字数 / 角色卡 / 素材数 / 会话数"""
    uid = _resolve_stats_user_filter(current_user, scope)
    return memory_manager.get_stats_overview(user_id=uid)


@router.get("/trend")
async def stats_trend_endpoint(
    range: str = Query("day", description="统计粒度：day(近7日) / week(近4周)"),
    scope: str = Query("auto"),
    current_user=Depends(get_current_user),
):
    """写作趋势：按日或按周统计字数与章节增长"""
    uid = _resolve_stats_user_filter(current_user, scope)
    clean_range = "week" if range == "week" else "day"
    return memory_manager.get_stats_trend(range_type=clean_range, user_id=uid)


@router.get("/works-progress")
async def stats_works_progress_endpoint(
    scope: str = Query("auto"),
    current_user=Depends(get_current_user),
):
    """各作品完成率（word_count / target_words）"""
    uid = _resolve_stats_user_filter(current_user, scope)
    works = memory_manager.get_stats_works_progress(user_id=uid)
    return {"scope": "personal" if uid else "all", "works": works, "total": len(works)}


@router.get("/genre-distribution")
async def stats_genre_distribution_endpoint(
    scope: str = Query("auto"),
    current_user=Depends(get_current_user),
):
    """作品体裁分布占比"""
    uid = _resolve_stats_user_filter(current_user, scope)
    genres = memory_manager.get_stats_genre_distribution(user_id=uid)
    return {"scope": "personal" if uid else "all", "genres": genres}

