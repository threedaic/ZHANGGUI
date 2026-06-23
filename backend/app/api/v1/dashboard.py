"""
数据看板 API 路由
GET /api/v1/dashboard  — 返回看板全量数据，Redis 缓存 5 分钟。
数据来源: daily_revenue / guest_ratings / bookings / tables 四表实时查询。
"""
import json
from datetime import date
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.repositories.dashboard import DashboardRepository
from app.utils.redis_client import get_redis
from app.utils.deps import get_store_id, make_response

router = APIRouter()

CACHE_KEY_PREFIX = "dashboard"
CACHE_TTL = 300  # 5 分钟


def _empty_dashboard() -> dict:
    """无数据时返回零值看板"""
    return {
        "revenue": {
            "today_revenue": 0, "yesterday_revenue": 0, "growth_rate": 0,
            "total_orders": 0, "total_guests": 0, "avg_order_value": 0,
        },
        "breakdown": {
            "bottle_sales": 0, "card_sales": 0, "other_sales": 0,
            "total": 0, "bottle_pct": 0, "card_pct": 0, "other_pct": 0,
        },
        "chart": [],
        "rating": {
            "avg_score": 0, "total_ratings": 0,
            "low_score_count": 0, "alerts": [],
        },
        "booking": {
            "confirmed": 0, "total_tables": 0, "available": 0,
        },
        "attendance": {
            "scheduled_count": 0, "actual_count": 0,
            "late_count": 0, "absent_count": 0, "early_count": 0,
            "leave_count": 0,
        },
        "my_performance": {
            "total_wework_pay": 0, "period": "",
        },
        "updated_at": date.today().isoformat() + "T00:00:00",
    }


@router.get("", response_model=dict)
async def get_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """获取数据看板全量数据"""
    store_id = get_store_id(request)

    # 尝试读 Redis 缓存
    cache_key = f"{CACHE_KEY_PREFIX}:{store_id}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return make_response(data=data, request=request)
    except Exception as e:
        logger.warning(f"redis cache read error: {e}")

    # 从数据库读取
    repo = DashboardRepository(db, store_id)

    revenue_block = await repo.get_revenue_block()
    breakdown = await repo.get_revenue_breakdown()
    chart = await repo.get_7day_revenue()
    rating = await repo.get_ratings_summary()
    booking = await repo.get_booking_summary()
    attendance = await repo.get_attendance_summary()
    # 我的业绩（每人不同，不缓存）
    employee_id = getattr(request.state, "employee_id", None)
    if employee_id:
        my_performance = await repo.get_my_performance(employee_id)
    else:
        from app.schemas.dashboard import MyPerformance
        my_performance = MyPerformance(total_wework_pay=0, period="")

    # 营收无数据时用零值，但仍返回其他模块的数据
    if revenue_block is None:
        from app.schemas.dashboard import RevenueBlock
        revenue_block = RevenueBlock(
            today_revenue=0, yesterday_revenue=0, growth_rate=0,
            total_orders=0, total_guests=0, avg_order_value=0,
        )

    data = {
        "revenue": revenue_block.model_dump(),
        "breakdown": breakdown.model_dump() if breakdown else {
            "bottle_sales": 0, "card_sales": 0, "other_sales": 0,
            "total": 0, "bottle_pct": 0, "card_pct": 0, "other_pct": 0,
        },
        "chart": [p.model_dump() for p in chart],
        "rating": rating.model_dump(),
        "booking": booking.model_dump(),
        "attendance": attendance.model_dump(),
        "my_performance": my_performance.model_dump(),
        "updated_at": date.today().isoformat() + "T00:00:00",
    }

    # 写 Redis 缓存
    try:
        redis = await get_redis()
        await redis.setex(cache_key, CACHE_TTL, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"redis cache write error: {e}")

    return make_response(data=data, request=request)


@router.get("/my-performance-detail", response_model=dict)
async def get_my_performance_detail(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取个人业绩明细：当月每日企微收款明细"""
    store_id = get_store_id(request)
    employee_id = getattr(request.state, "employee_id", None)
    if not employee_id:
        return make_response(data=[], request=request)
    repo = DashboardRepository(db, store_id)
    detail = await repo.get_my_performance_detail(employee_id)
    return make_response(data=detail, request=request)
