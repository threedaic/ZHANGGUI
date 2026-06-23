"""
账期管理 API 路由
/api/v1/periods/

GET    /{period}           查询账期状态
POST   /{period}/lock      锁定账期(店长)
POST   /{period}/close     关账(店长)
POST   /{period}/reopen    重新开放账期(老板)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.period import PeriodService
from app.utils.deps import get_store_id, require_role, require_employee_id, make_response

router = APIRouter()


@router.get("/{period}", summary="查询账期状态")
async def get_period(
    request: Request,
    period: str,
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = PeriodService(db, store_id)
    period_obj = await service.get_period(period)
    if not period_obj:
        return make_response(
            data={"period": period, "status": "open", "message": "账期未创建，默认为 open"},
            request=request,
        )
    return make_response(
        data={
            "period": period_obj.period,
            "status": period_obj.status,
            "locked_at": period_obj.locked_at.isoformat() if period_obj.locked_at else None,
            "locked_by": period_obj.locked_by,
            "closed_at": period_obj.closed_at.isoformat() if period_obj.closed_at else None,
            "closed_by": period_obj.closed_by,
            "note": period_obj.note,
        },
        request=request,
    )


@router.post("/{period}/lock", summary="锁定账期(店长)")
async def lock_period(
    request: Request,
    period: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = require_employee_id(request)
    service = PeriodService(db, store_id)
    period_obj = await service.lock_period(period, user_id)
    await db.commit()
    return make_response(
        message=f"账期 {period} 已锁定",
        data={"period": period, "status": period_obj.status},
        request=request,
    )


@router.post("/{period}/close", summary="关账(店长)")
async def close_period(
    request: Request,
    period: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = require_employee_id(request)
    service = PeriodService(db, store_id)
    period_obj = await service.close_period(period, user_id)
    await db.commit()
    return make_response(
        message=f"账期 {period} 已关账",
        data={"period": period, "status": period_obj.status},
        request=request,
    )


@router.post("/{period}/reopen", summary="重新开放账期(老板)")
async def reopen_period(
    request: Request,
    period: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    user_id = require_employee_id(request)
    service = PeriodService(db, store_id)
    period_obj = await service.reopen_period(period, user_id)
    await db.commit()
    return make_response(
        message=f"账期 {period} 已重新开放",
        data={"period": period, "status": period_obj.status},
        request=request,
    )
