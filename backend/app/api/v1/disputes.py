"""
工资申诉 API 路由
/api/v1/disputes/

POST   /                    员工提交工资申诉
GET    /my                  员工查看自己的申诉
GET    /list                管理端查看所有申诉（收件箱）
GET    /{id}                查看申诉详情
PUT    /{id}/confirm        确认有误（老板）
PUT    /{id}/reject         驳回申诉（老板）
PUT    /{id}/adjust         确认调整并指定调整月份（老板）
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.dispute import WageDispute
from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from app.utils.deps import (
    get_store_id, require_role, get_employee_id,
    require_employee_id, make_response,
)

router = APIRouter()


@router.post("/", summary="员工提交工资申诉")
async def create_dispute(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """员工对自己的工资提交申诉"""
    store_id = get_store_id(request)
    employee_id = require_employee_id(request)
    body = await request.json()

    wage_id = body.get("wage_id")
    dispute_type = body.get("dispute_type", "other")
    expected_amount = body.get("expected_amount")
    reason = body.get("reason", "")
    evidence = body.get("evidence")

    if not wage_id:
        return make_response(code=40001, message="缺少工资记录ID", request=request)
    if not reason:
        return make_response(code=40002, message="请填写申诉原因", request=request)

    # 检查工资记录是否存在
    wage = await db.get(PayrollRecord, uuid.UUID(wage_id))
    if not wage:
        return make_response(code=40003, message="工资记录不存在", request=request)
    if str(wage.employee_id) != str(employee_id):
        return make_response(code=40004, message="只能申诉自己的工资", request=request)
    if wage.status == "draft":
        return make_response(code=40005, message="工资尚未确认，无法申诉", request=request)

    # 检查是否已申诉过
    existing = await db.execute(
        select(WageDispute).where(
            and_(
                WageDispute.wage_id == uuid.UUID(wage_id),
                WageDispute.status.in_(["pending", "confirmed"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        return make_response(code=40006, message="该月工资已有待处理的申诉", request=request)

    # 创建申诉
    dispute = WageDispute(
        store_id=uuid.UUID(store_id),
        wage_id=uuid.UUID(wage_id),
        employee_id=uuid.UUID(employee_id),
        period=wage.period,
        dispute_type=dispute_type,
        original_amount=float(wage.net_pay or 0),
        expected_amount=float(expected_amount) if expected_amount else None,
        reason=reason,
        evidence=evidence,
        status="pending",
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)

    return make_response(
        message="申诉已提交，请等待处理",
        data={"dispute_id": str(dispute.id)},
        request=request,
    )


@router.get("/my", summary="员工查看自己的申诉列表")
async def list_my_disputes(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)

    result = await db.execute(
        select(WageDispute, Employee.name.label("reviewer_name"))
        .outerjoin(Employee, WageDispute.reviewed_by == Employee.id)
        .where(WageDispute.employee_id == uuid.UUID(employee_id))
        .order_by(WageDispute.created_at.desc())
    )
    rows = result.all()

    items = []
    for d, reviewer_name in rows:
        items.append({
            "dispute_id": str(d.id),
            "wage_id": str(d.wage_id),
            "period": d.period,
            "dispute_type": d.dispute_type,
            "original_amount": float(d.original_amount) if d.original_amount else None,
            "expected_amount": float(d.expected_amount) if d.expected_amount else None,
            "reason": d.reason,
            "status": d.status,
            "resolution": d.resolution,
            "adjusted_amount": float(d.adjusted_amount) if d.adjusted_amount else None,
            "adjusted_in_period": d.adjusted_in_period,
            "reviewer_name": reviewer_name,
            "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return make_response(data=items, request=request)


@router.get("/list", summary="管理端查看所有申诉（收件箱）")
async def list_disputes(
    request: Request,
    status: str = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    query = (
        select(WageDispute, Employee.name.label("employee_name"))
        .join(Employee, WageDispute.employee_id == Employee.id)
        .where(WageDispute.store_id == uuid.UUID(store_id))
    )
    if status:
        query = query.where(WageDispute.status == status)
    query = query.order_by(WageDispute.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    items = []
    for d, employee_name in rows:
        items.append({
            "dispute_id": str(d.id),
            "wage_id": str(d.wage_id),
            "employee_id": str(d.employee_id),
            "employee_name": employee_name,
            "period": d.period,
            "dispute_type": d.dispute_type,
            "original_amount": float(d.original_amount) if d.original_amount else None,
            "expected_amount": float(d.expected_amount) if d.expected_amount else None,
            "reason": d.reason,
            "evidence": d.evidence,
            "status": d.status,
            "resolution": d.resolution,
            "adjusted_amount": float(d.adjusted_amount) if d.adjusted_amount else None,
            "adjusted_in_period": d.adjusted_in_period,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return make_response(data=items, request=request)


@router.get("/{dispute_id}", summary="查看申诉详情")
async def get_dispute(
    request: Request,
    dispute_id: str,
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)

    dispute = await db.get(WageDispute, uuid.UUID(dispute_id))
    if not dispute:
        return make_response(code=40401, message="申诉不存在", request=request)

    # 权限检查：员工只能看自己的，boss/store_manager 可以看本店的
    role = getattr(request.state, "role", None)
    if role not in ("boss", "store_manager", "admin"):
        if str(dispute.employee_id) != str(employee_id):
            return make_response(code=40301, message="无权查看", request=request)
    elif str(dispute.store_id) != str(store_id):
        return make_response(code=40302, message="无权查看其他门店申诉", request=request)

    # 获取员工姓名
    emp = await db.get(Employee, dispute.employee_id)
    reviewer = await db.get(Employee, dispute.reviewed_by) if dispute.reviewed_by else None

    return make_response(
        data={
            "dispute_id": str(dispute.id),
            "wage_id": str(dispute.wage_id),
            "employee_id": str(dispute.employee_id),
            "employee_name": emp.name if emp else None,
            "period": dispute.period,
            "dispute_type": dispute.dispute_type,
            "original_amount": float(dispute.original_amount) if dispute.original_amount else None,
            "expected_amount": float(dispute.expected_amount) if dispute.expected_amount else None,
            "reason": dispute.reason,
            "evidence": dispute.evidence,
            "status": dispute.status,
            "resolution": dispute.resolution,
            "adjusted_amount": float(dispute.adjusted_amount) if dispute.adjusted_amount else None,
            "adjusted_in_period": dispute.adjusted_in_period,
            "reviewer_name": reviewer.name if reviewer else None,
            "reviewed_at": dispute.reviewed_at.isoformat() if dispute.reviewed_at else None,
            "created_at": dispute.created_at.isoformat() if dispute.created_at else None,
        },
        request=request,
    )


@router.put("/{dispute_id}/reject", summary="驳回申诉（老板）")
async def reject_dispute(
    request: Request,
    dispute_id: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    user_id = getattr(request.state, "user_id", None)
    body = await request.json()

    dispute = await db.get(WageDispute, uuid.UUID(dispute_id))
    if not dispute:
        return make_response(code=40401, message="申诉不存在", request=request)
    if str(dispute.store_id) != str(store_id):
        return make_response(code=40302, message="无权操作", request=request)
    if dispute.status != "pending":
        return make_response(code=40001, message="只能处理待处理的申诉", request=request)

    resolution = body.get("resolution", "")
    if not resolution:
        return make_response(code=40002, message="请填写驳回原因", request=request)

    dispute.status = "rejected"
    dispute.resolution = resolution
    dispute.reviewed_by = uuid.UUID(user_id) if user_id else None
    dispute.reviewed_at = datetime.utcnow()

    await db.commit()
    return make_response(message="申诉已驳回", request=request)


@router.put("/{dispute_id}/confirm", summary="确认工资有误（老板）")
async def confirm_dispute(
    request: Request,
    dispute_id: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    user_id = getattr(request.state, "user_id", None)
    body = await request.json()

    dispute = await db.get(WageDispute, uuid.UUID(dispute_id))
    if not dispute:
        return make_response(code=40401, message="申诉不存在", request=request)
    if str(dispute.store_id) != str(store_id):
        return make_response(code=40302, message="无权操作", request=request)
    if dispute.status != "pending":
        return make_response(code=40001, message="只能处理待处理的申诉", request=request)

    adjusted_amount = body.get("adjusted_amount")
    adjusted_in_period = body.get("adjusted_in_period")
    resolution = body.get("resolution", "")

    if adjusted_amount is None:
        return make_response(code=40003, message="请填写调整金额", request=request)

    # 计算差额：正数=补发，负数=扣回
    original = float(dispute.original_amount or 0)
    expected = float(dispute.expected_amount or 0)
    diff = float(adjusted_amount)

    dispute.status = "confirmed"
    dispute.adjusted_amount = diff
    dispute.adjusted_in_period = adjusted_in_period
    dispute.resolution = resolution or f"确认工资有误，差额{diff:+.2f}元将在{adjusted_in_period or '下月'}工资中调整"
    dispute.reviewed_by = uuid.UUID(user_id) if user_id else None
    dispute.reviewed_at = datetime.utcnow()

    await db.commit()
    return make_response(message="已确认工资有误，请在工资调整中处理差额", request=request)


@router.get("/stats/summary", summary="申诉统计（收件箱摘要）")
async def dispute_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    result = await db.execute(
        select(
            func.count(WageDispute.id).label("total"),
            func.count().filter(WageDispute.status == "pending").label("pending"),
            func.count().filter(WageDispute.status == "confirmed").label("confirmed"),
            func.count().filter(WageDispute.status == "rejected").label("rejected"),
            func.count().filter(WageDispute.status == "adjusted").label("adjusted"),
        ).where(WageDispute.store_id == uuid.UUID(store_id))
    )
    row = result.one()

    return make_response(
        data={
            "total": row.total,
            "pending": row.pending,
            "confirmed": row.confirmed,
            "rejected": row.rejected,
            "adjusted": row.adjusted,
        },
        request=request,
    )
