"""
防飞单 API 路由
/api/v1/antifraud/
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.database import get_db
from app.schemas.antifraud import ScanRequest
from app.services.antifraud import AntiFraudService
from app.utils.deps import get_store_id, require_role, make_response

router = APIRouter()


# ==================== 扫描 ====================

@router.post("/scan", summary="手动触发防飞单扫描")
async def trigger_scan(
    request: Request,
    body: ScanRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    if body.store_id:
        store_id = body.store_id

    scan_date = body.date or (date.today() - timedelta(days=1)).isoformat()

    service = AntiFraudService(db, store_id)
    result = await service.scan_daily(scan_date, push_alert=True)
    return make_response(
        message=f"扫描完成: {scan_date}, {result['total_sessions']} 桌, {result['anomaly_count']} 异常",
        data=result,
        request=request,
    )


# ==================== 预警列表 ====================

@router.get("/alerts", summary="防飞单预警列表")
async def list_alerts(
    request: Request,
    date_from: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    risk_level: str | None = Query(None, description="low/medium/high/critical"),
    employee_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    service = AntiFraudService(db, store_id)
    data = await service.get_alerts(
        date_from=date_from,
        date_to=date_to,
        risk_level=risk_level,
        employee_id=employee_id,
        page=page,
        page_size=page_size,
    )
    return make_response(data=data, request=request)


@router.get("/alerts/{session_id}", summary="预警详情")
async def get_alert_detail(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    service = AntiFraudService(db, store_id)
    detail = await service.get_alert_detail(session_id)
    return make_response(data=detail, request=request)


# ==================== 统计 ====================

@router.get("/stats", summary="防飞单统计")
async def get_stats(
    request: Request,
    date_from: str = Query(..., description="开始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    service = AntiFraudService(db, store_id)
    data = await service.get_stats(date_from=date_from, date_to=date_to)
    return make_response(data=data, request=request)
