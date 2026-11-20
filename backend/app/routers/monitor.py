from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.auth import get_current_user
from app.core.memory import memory_manager

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


def _resolve_monitor_user_filter(current_user: dict, scope: str = "auto") -> Optional[str]:
    """
    运营监控权限矩阵校验 (同款安全隔离逻辑，对应验收 AC-1 / AC-2):
    - admin 默认查看全站汇总 (返回 None 表示不按 user_id 过滤)；传 scope='mine' 时仅看自己。
    - member 强制只能查看自己的调用流水与统计 (返回 current_user['id'])，杜绝越权访问他人数据。
    """
    if current_user.get("role") == "admin":
        if scope == "mine":
            return current_user["id"]
        return None
    return current_user["id"]


@router.get("/overview")
async def monitor_overview_endpoint(
    range: str = Query("7d", description="统计时间范围：7d / 30d"),
    scope: str = Query("auto", description="admin 可选 all/mine，member 强制 mine"),
    current_user=Depends(get_current_user),
):
    """
    运营监控概览统计与趋势折线数据 (调用总数 / 成功失败 / 总 Token / 平均耗时 / 每日双线趋势)
    """
    uid = _resolve_monitor_user_filter(current_user, scope)
    clean_range = "30d" if range == "30d" else "7d"
    return memory_manager.get_monitor_overview(range_type=clean_range, user_id=uid)


@router.get("/model-distribution")
async def monitor_model_distribution_endpoint(
    range: str = Query("7d", description="统计时间范围：7d / 30d"),
    scope: str = Query("auto", description="admin 可选 all/mine，member 强制 mine"),
    current_user=Depends(get_current_user),
):
    """
    模型调用分布比例与 Token 消耗统计
    """
    uid = _resolve_monitor_user_filter(current_user, scope)
    clean_range = "30d" if range == "30d" else "7d"
    models = memory_manager.get_monitor_model_distribution(range_type=clean_range, user_id=uid)
    return {
        "scope": "mine" if uid else "all",
        "range": clean_range,
        "models": models,
        "total_models": len(models),
    }


@router.get("/calls")
async def monitor_calls_endpoint(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="状态筛选：success / error / aborted"),
    model: Optional[str] = Query(None, description="模型名称筛选"),
    scope: str = Query("auto", description="admin 可选 all/mine，member 强制 mine"),
    current_user=Depends(get_current_user),
):
    """
    API 调用日志流水列表 (分页 + 状态/模型筛选 + 耗时/Token/错误信息)
    """
    uid = _resolve_monitor_user_filter(current_user, scope)
    return memory_manager.get_monitor_calls(
        page=page,
        size=size,
        status=status,
        model=model,
        user_id=uid,
    )

