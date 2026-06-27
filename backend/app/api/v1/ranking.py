"""
员工排名 API 路由
/api/v1/rankings/

GET    /leaderboard           排行榜（全员可见，不显示工资）
POST   /calculate             计算排名（店长触发）
GET    /my                    员工查看自己的四维排名
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.ranking import RankingService, RANK_TYPES
from app.utils.deps import (
    get_store_id, require_role, require_employee_id, make_response,
)

router = APIRouter()


@router.get("/leaderboard", summary="排行榜(全员可见)")
async def get_leaderboard(
    request: Request,
    period: str = Query(..., description="月份 2026-06"),
    rank_type: str = Query(..., description="排名类型: performance/kpi/attendance/rating"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """排行榜接口

    全员可见，仅返回名次和排名数值，**不包含工资金额**。
    排名类型:
      - performance  业绩排名
      - kpi          KPI排名
      - attendance   考勤排名
      - rating       评分排名
    """
    store_id = get_store_id(request)
    service = RankingService(db, store_id)
    data = await service.get_leaderboard(period=period, rank_type=rank_type, limit=limit)
    return make_response(data=data, request=request)


@router.post("/calculate", summary="计算排名(店长)")
async def calculate_rankings(
    request: Request,
    period: str = Query(..., description="月份 2026-06"),
    rank_type: str | None = Query(
        None, description="排名类型，留空=计算全部4维"
    ),
    db: AsyncSession = Depends(get_db),
):
    """触发排名计算（支持重算）

    店长及以上权限。建议在月度账期锁定前计算一次。
    """
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    service = RankingService(db, store_id)
    records = await service.calculate_rankings(period=period, rank_type=rank_type)

    # 按类型统计
    type_counts: dict[str, int] = {}
    for r in records:
        type_counts[r.rank_type] = type_counts.get(r.rank_type, 0) + 1

    return make_response(
        message=f"已计算 {len(records)} 条排名记录",
        data={
            "period": period,
            "total": len(records),
            "by_type": type_counts,
            "rank_types": list(RANK_TYPES),
        },
        request=request,
    )


@router.get("/my", summary="员工查看自己的四维排名")
async def my_rankings(
    request: Request,
    period: str = Query(..., description="月份 2026-06"),
    db: AsyncSession = Depends(get_db),
):
    """员工查看自己在四个维度的排名"""
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = RankingService(db, store_id)
    data = await service.get_my_rankings(employee_id, period)
    return make_response(data=data, request=request)
