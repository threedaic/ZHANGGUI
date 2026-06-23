"""订桌预约 API 路由。

前缀: /api/v1/reservations (由 main.py 提供)

完整路径映射:
  GET  ""               → /api/v1/reservations          (预约列表)
  POST ""               → /api/v1/reservations          (创建预约)
  GET  "/stats"         → /api/v1/reservations/stats    (预约统计)
  GET  "/{booking_id}"  → /api/v1/reservations/{id}     (预约详情)
  PUT  "/{booking_id}"  → /api/v1/reservations/{id}     (更新预约)
  DELETE "/{booking_id}" → /api/v1/reservations/{id}    (取消预约)
"""

import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingStats,
)
from app.services.booking import BookingService
from app.utils.pagination import PageParams
from app.utils.deps import get_store_id, make_response

router = APIRouter()


# ==================== Bookings CRUD ====================

@router.get("")
async def list_bookings(
    request: Request,
    date: str | None = Query(None, description="YYYY-MM-DD"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """查询预约列表，支持按日期、状态筛选和分页。"""
    store_id = get_store_id(request)
    svc = BookingService(db)
    result = await svc.list(store_id, date=date, status=status, params=PageParams(page=page, page_size=page_size))
    return make_response(data=result.model_dump(), request=request)


@router.post("")
async def create_booking(
    body: BookingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建预约，自动分配桌位并检测冲突。记录创建人以关联个人业绩。"""
    store_id = get_store_id(request)
    employee_id = getattr(request.state, "employee_id", None)
    svc = BookingService(db)
    booking = await svc.create(store_id, body, created_by=employee_id)
    return make_response(data=booking.model_dump(), request=request)


@router.get("/stats")
async def booking_stats(
    request: Request,
    date: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """获取某日预约统计（总桌位数、已预约、空闲）。"""
    store_id = get_store_id(request)
    svc = BookingService(db)
    stats = await svc.stats(store_id, date)
    return make_response(data=stats.model_dump(), request=request)


@router.get("/{booking_id}")
async def get_booking(
    booking_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取单个预约详情。"""
    store_id = get_store_id(request)
    svc = BookingService(db)
    booking = await svc.get(booking_id, store_id)
    return make_response(data=booking.model_dump(), request=request)


@router.put("/{booking_id}")
async def update_booking(
    booking_id: uuid.UUID,
    body: BookingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新预约信息（时段、人数、桌位、状态、备注）。"""
    store_id = get_store_id(request)
    svc = BookingService(db)
    booking = await svc.update(booking_id, store_id, body)
    return make_response(data=booking.model_dump(), request=request)


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """取消预约（状态改为 cancelled）。"""
    store_id = get_store_id(request)
    svc = BookingService(db)
    booking = await svc.cancel(booking_id, store_id)
    return make_response(data=booking.model_dump(), request=request)
