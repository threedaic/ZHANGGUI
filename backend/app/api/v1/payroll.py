"""
工资计算 API 路由
/api/v1/payroll/

GET    /monthly        月度工资汇总
GET    /records/{id}   工资详情
GET    /my             员工查看自己的历史工资
GET    /my-preview     员工当月工资预览（每日同步，未结算）
POST   /generate       生成工资
POST   /review         会计复核
POST   /finalize       老板确认
POST   /mark-paid      会计发放
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.payroll import (
    PayrollGenerateRequest,
    PayrollFinalizeRequest,
    PayrollMarkPaidRequest,
)
from app.services.payroll import PayrollService
from app.services.auto_payroll import AutoPayrollService
from app.utils.deps import get_store_id, require_role, get_employee_id, require_employee_id, make_response

router = APIRouter()


# ==================== 工资生成 ====================

@router.post("/generate", summary="生成月度工资(老板/会计)")
async def generate_payroll(
    request: Request,
    body: PayrollGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    store_id = get_store_id(request)
    user_id = getattr(request.state, "user_id", None)
    service = PayrollService(db, store_id)
    records = await service.generate(body.period, body.employee_ids, user_id=user_id)

    return make_response(
        message=f"已生成 {len(records)} 条工资记录",
        data={
            "period": body.period,
            "count": len(records),
            "employees": [
                {"employee_id": r.employee_id, "net_pay": float(r.net_pay or 0), "status": r.status}
                for r in records
            ],
        },
        request=request,
    )


# ==================== 工资查询 ====================

@router.get("/monthly", summary="门店月度工资汇总(店长)")
async def list_monthly(
    request: Request,
    period: str = Query(..., description="月份 2026-06"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """门店月度工资汇总（仅老板/会计可见全员工资，店长不可见）"""
    require_role(request, ["boss", "accountant"])
    store_id = get_store_id(request)
    service = PayrollService(db, store_id)
    data = await service.get_monthly(period=period, page=page, page_size=page_size)
    return make_response(data=data, request=request)


@router.get("/records/{record_id}", summary="工资记录详情")
async def get_record(
    request: Request,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """工资记录详情

    权限: 老板/会计可查看任意记录；普通员工仅可查看自己的工资条。店长不可见他人明细。
    """
    store_id = get_store_id(request)
    role = getattr(request.state, "role", "staff")
    service = PayrollService(db, store_id)
    data = await service.get_detail(record_id)

    # 普通员工（含店长）只能看自己的工资条
    if role not in ("boss", "accountant"):
        employee_id = require_employee_id(request)
        if data["employee_id"] != employee_id:
            from app.utils.exceptions import ForbiddenError
            raise ForbiddenError("无权查看他人的工资条")

    return make_response(data=data, request=request)


@router.get("/my", summary="员工查看自己的工资")
async def my_payroll(
    request: Request,
    period: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = PayrollService(db, store_id)

    from sqlalchemy import select, and_
    from app.models.payroll import PayrollRecord
    stmt = select(PayrollRecord).where(
        and_(
            PayrollRecord.store_id == store_id,
            PayrollRecord.employee_id == employee_id,
        )
    )
    if period:
        stmt = stmt.where(PayrollRecord.period == period)
    stmt = stmt.order_by(PayrollRecord.period.desc()).limit(50)
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    if not records:
        return make_response(data=[], request=request)

    emp_info = await service._get_employee_info([employee_id])
    emp = emp_info.get(employee_id, {"name": "", "role": ""})

    items = []
    for r in records:
        items.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "period": r.period,
            "total_income": float(r.total_income or 0),
            "total_deduction": float(r.total_deduction or 0),
            "net_pay": float(r.net_pay or 0),
            "status": r.status,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "finalized_at": r.finalized_at.isoformat() if r.finalized_at else None,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            "employee_name": emp["name"],
            "employee_role": emp["role"],
        })

    return make_response(data=items, request=request)


# ==================== 员工当月预览（每日同步） ====================

@router.get("/my-preview", summary="员工当月工资预览（每日同步）")
async def my_payroll_preview(
    request: Request,
    period: str | None = Query(None, description="账期 YYYY-MM，默认当前月"),
    db: AsyncSession = Depends(get_db),
):
    """员工自助查看本月工资预估。

    数据来自 6 张业务表的实时聚合（合同/业绩/考勤/KPI/奖惩/加班），
    与老板看到的"自动发薪大表格"使用同一套计算逻辑，保证数据一致。

    每日自动更新，员工随时可查，减少月底争议。
    """
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = AutoPayrollService(db, uuid.UUID(store_id))
    data = await service.get_my_preview(uuid.UUID(employee_id), period)
    return make_response(data=data, request=request)


# ==================== 会计复核 ====================

@router.post("/review", summary="会计复核(会计/店长)")
async def review_payroll(
    request: Request,
    body: PayrollFinalizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """会计复核工资：draft -> reviewed"""
    require_role(request, ["boss", "store_manager", "accountant"])
    store_id = get_store_id(request)
    issuer_id = require_employee_id(request)
    service = PayrollService(db, store_id)
    count = await service.review(body.record_ids, issuer_id, body.notes)
    return make_response(message=f"已复核 {count} 条工资记录，等待老板确认", request=request)


# ==================== 老板确认 ====================

@router.post("/finalize", summary="老板确认工资条(老板)")
async def finalize_payroll(
    request: Request,
    body: PayrollFinalizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """老板确认工资：reviewed -> confirmed"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    issuer_id = require_employee_id(request)
    service = PayrollService(db, store_id)
    count = await service.finalize(body.record_ids, issuer_id, body.notes)

    # 为每位员工创建签收任务
    from app.services.sign_task import SignTaskService
    from sqlalchemy import select, and_
    from app.models.payroll import PayrollRecord
    from app.models.employee import Employee

    sign_service = SignTaskService(db, store_id)
    tasks_created = 0
    try:
        # 批量查询工资记录（避免 N+1）
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.store_id == store_id,
                PayrollRecord.id.in_(body.record_ids),
            )
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        # 批量查询员工姓名
        emp_ids = [r.employee_id for r in records]
        emp_name_map: dict[int, str] = {}
        if emp_ids:
            emp_result = await db.execute(
                select(Employee.id, Employee.name).where(Employee.id.in_(emp_ids))
            )
            emp_name_map = {row[0]: row[1] for row in emp_result.all()}

        for record in records:
            emp_name = emp_name_map.get(record.employee_id, f"员工{record.employee_id}")

            await sign_service.send_to_inbox(
                employee_id=record.employee_id,
                msg_type="salary_slip",
                ref_id=record.id,
                issued_by=issuer_id,
                extra={
                    "period": record.period,
                    "net_pay": float(record.net_pay or 0),
                    "employee_name": emp_name,
                },
            )
            tasks_created += 1
    except Exception as e:
        from loguru import logger
        logger.warning(f"工资单签收任务创建部分失败: {e}")

    await db.commit()
    return make_response(message=f"已确认 {count} 条工资记录，{tasks_created} 个签收任务已推送", request=request)


@router.post("/mark-paid", summary="会计发放工资(会计/老板)")
async def mark_paid(
    request: Request,
    body: PayrollMarkPaidRequest,
    db: AsyncSession = Depends(get_db),
):
    """会计操作发放：confirmed -> paid"""
    require_role(request, ["boss", "store_manager", "accountant"])
    store_id = get_store_id(request)
    user_id = require_employee_id(request)
    service = PayrollService(db, store_id)
    count = await service.mark_paid(body.record_ids, user_id, body.paid_at)
    return make_response(message=f"已标记 {count} 条工资为已发放", request=request)
