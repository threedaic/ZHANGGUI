"""企微对外收款同步 API

- POST /sync: 同步指定日期范围的收款记录
- GET /list: 查看已同步的收款记录
- GET /summary: 按员工汇总收款金额
"""

from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.database import get_db
from app.utils.deps import make_response, require_role, get_store_id
from app.utils.exceptions import NotFoundError, ValidationError
from app.services.wework_payment import WeworkPaymentService
from app.models.wework_payment import WeworkPaymentSync
from app.models.employee import Employee

router = APIRouter()


class SyncRequest(BaseModel):
    begin_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD


@router.post("/sync", summary="同步企微收款记录")
async def sync_payments(
    request: Request,
    body: SyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """从企微对外收款 API 拉取收款记录，写入数据库"""
    store_id = request.state.store_id
    try:
        begin = datetime.strptime(body.begin_date, "%Y-%m-%d").date()
        end = datetime.strptime(body.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("日期格式错误，需要 YYYY-MM-DD")

    if begin > end:
        raise ValidationError("开始日期不能晚于结束日期")

    # 企微 API 限制：起止时间间隔不能超过1个月
    if (end - begin).days > 31:
        raise ValidationError("日期范围不能超过31天")

    service = WeworkPaymentService(db, store_id)
    result = await service.sync_payments(begin, end)
    return make_response(
        message=f"同步完成: 拉取{result['total']}条, 新增{result['inserted']}条, 跳过{result['skipped']}条",
        data=result,
        request=request,
    )


@router.get("/list", summary="查看收款记录")
async def list_payments(
    request: Request,
    begin_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    employee_id: str | None = Query(None, description="按员工筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """查看已同步的收款记录"""
    store_id = request.state.store_id
    begin = datetime.strptime(begin_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    conditions = [
        WeworkPaymentSync.store_id == store_id,
        WeworkPaymentSync.pay_time >= begin,
        WeworkPaymentSync.pay_time <= end,
    ]
    if employee_id:
        conditions.append(WeworkPaymentSync.employee_id == employee_id)

    # 总数
    count_stmt = select(func.count()).select_from(WeworkPaymentSync).where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页查询
    stmt = (
        select(
            WeworkPaymentSync,
            Employee.name.label("employee_name"),
        )
        .outerjoin(Employee, WeworkPaymentSync.employee_id == Employee.employee_id)
        .where(and_(*conditions))
        .order_by(WeworkPaymentSync.pay_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)

    items = []
    for row in result:
        p = row[0]
        items.append({
            "payment_id": str(p.id),
            "transaction_id": p.transaction_id,
            "employee_id": str(p.employee_id) if p.employee_id else None,
            "employee_name": row[1],
            "amount": float(p.amount),
            "pay_time": p.pay_time.isoformat() if p.pay_time else None,
            "payer_name": p.payer_name,
            "remark": p.remark,
            "sync_status": p.sync_status,
        })

    return make_response(
        data={"items": items, "total": total, "page": page, "page_size": page_size},
        request=request,
    )


@router.get("/summary", summary="按员工汇总收款")
async def summary_by_employee(
    request: Request,
    begin_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """按员工汇总收款金额，用于业绩对账"""
    store_id = request.state.store_id
    begin = datetime.strptime(begin_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    stmt = (
        select(
            Employee.name.label("employee_name"),
            func.count(WeworkPaymentSync.id).label("bill_count"),
            func.sum(WeworkPaymentSync.amount).label("total_amount"),
        )
        .select_from(WeworkPaymentSync)
        .outerjoin(Employee, WeworkPaymentSync.employee_id == Employee.employee_id)
        .where(
            and_(
                WeworkPaymentSync.store_id == store_id,
                WeworkPaymentSync.pay_time >= begin,
                WeworkPaymentSync.pay_time <= end,
            )
        )
        .group_by(Employee.name)
        .order_by(func.sum(WeworkPaymentSync.amount).desc())
    )
    result = await db.execute(stmt)

    items = []
    for row in result:
        items.append({
            "employee_name": row[0] or "未关联员工",
            "bill_count": row[1],
            "total_amount": float(row[2] or 0),
        })

    return make_response(data={"items": items}, request=request)
