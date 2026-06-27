"""
统一审批 API

路由映射：
GET  /              审批列表
POST /              发起审批
GET  /{approval_id} 审批详情
PUT  /{approval_id}/approve 审批通过
PUT  /{approval_id}/reject  审批驳回
"""
from datetime import date
import os
import uuid
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.approval import ApprovalRequest
from app.services.approval_service import ApprovalService
from app.repositories.approval import ApprovalRepository
from app.repositories.leave_balance import LeaveBalanceRepository
from app.schemas.approval import ApprovalCreateRequest, ApprovalReviewRequest
from app.utils.deps import get_store_id, get_user_id, get_employee_id, require_role, make_response
from app.utils.pagination import PageParams, paginate
from app.utils.exceptions import ValidationError

router = APIRouter()


TYPE_LABELS = {
    "leave": "请假",
    "makeup": "补卡",
    "swap": "调班",
    "expense": "报销",
}

# 请假子类型
LEAVE_TYPES = {
    "comp_off": {"label": "调休", "default_days": 0},
    "sick": {"label": "病假", "default_days": 12},
    "personal": {"label": "事假", "default_days": 3},
}


def _approval_to_dict(approval, name_map: dict, approver_name_map: dict | None = None) -> dict:
    return {
        "id": approval.id,
        "employee_id": approval.employee_id,
        "employee_name": name_map.get(approval.employee_id, ""),
        "type": approval.type,
        "type_label": TYPE_LABELS.get(approval.type, approval.type),
        "status": approval.status,
        "start_date": str(approval.start_date) if approval.start_date else None,
        "end_date": str(approval.end_date) if approval.end_date else None,
        "reason": approval.reason,
        "extra": approval.extra,
        "approver_id": approval.approver_id,
        "approver_name": (approver_name_map or {}).get(approval.approver_id) if approval.approver_id else None,
        "reject_reason": approval.reject_reason,
        "created_at": str(approval.created_at) if approval.created_at else None,
    }


@router.get("")
async def list_approvals(
    request: Request,
    status: str | None = Query(None, description="pending/approved/rejected"),
    approval_type: str | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """审批列表（员工看自己，店长/老板看全店）"""
    store_id = get_store_id(request)
    role = getattr(request.state, "role", "staff")
    employee_id = getattr(request.state, "employee_id", None)

    repo = ApprovalRepository(db, store_id)
    params = PageParams(page=page, page_size=page_size)

    query_employee_id = None
    user_id = get_user_id(request)
    if role not in ("boss", "store_manager"):
        query_employee_id = employee_id

    approvals, total = await repo.list_approvals(
        employee_id=query_employee_id,
        status=status,
        approval_type=approval_type,
        page=params,
        approver_id=user_id if role not in ("boss", "store_manager") else None,
        include_assigned=role not in ("boss", "store_manager"),
    )

    emp_ids = list(set(a.employee_id for a in approvals))
    name_map = await repo.get_employee_name_map(emp_ids)

    # 解析审批人姓名
    approver_ids = list({a.approver_id for a in approvals if a.approver_id})
    approver_name_map = {}
    if approver_ids:
        from sqlalchemy import select as sa_select
        from app.models.user import User
        stmt = sa_select(User.id, User.name).where(User.id.in_(approver_ids))
        result_rows = await db.execute(stmt)
        approver_name_map = {row[0]: row[1] for row in result_rows.all()}

    items = [_approval_to_dict(a, name_map, approver_name_map) for a in approvals]
    result = paginate(items, total, params)
    return make_response(request=request, data=result.model_dump())


@router.get("/pending-count")
async def get_pending_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取待我审批的数量"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    role = getattr(request.state, "role", "staff")

    repo = ApprovalRepository(db, store_id)
    # 指定给我的待审批数（调班等）
    from sqlalchemy import select as sa_select, func, and_
    stmt = sa_select(func.count(ApprovalRequest.id)).where(
        and_(
            ApprovalRequest.store_id == store_id,
            ApprovalRequest.status == "pending",
            ApprovalRequest.approver_id == user_id,
        )
    )
    assigned_to_me = (await db.execute(stmt)).scalar() or 0

    # 店长/老板还能看到全店待审批总数
    total_pending = 0
    if role in ("boss", "store_manager"):
        _, total_pending = await repo.list_approvals(status="pending", page=PageParams(page=1, page_size=1))

    return make_response(
        request=request,
        data={
            "total_pending": total_pending,
            "assigned_to_me": assigned_to_me,
        },
    )


@router.get("/approvers")
async def list_approvers(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取可指定的审批人列表（店长/老板）"""
    store_id = get_store_id(request)
    from sqlalchemy import select as sa_select, and_
    from app.models.user import User
    from app.models.employee import Employee
    stmt = (
        sa_select(User.id, User.username, User.role, Employee.name)
        .join(Employee, Employee.id == User.employee_id, isouter=True)
        .where(
            and_(
                Employee.store_id == store_id,
                User.is_active.is_(True),
                User.role.in_(["boss", "store_manager"]),
            )
        )
    )
    rows = (await db.execute(stmt)).all()
    return make_response(
        request=request,
        data=[
            {"id": r[0], "name": r[3] or r[1], "role": r[2]} for r in rows
        ],
    )


@router.post("")
async def create_approval(
    request: Request,
    body: ApprovalCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """发起审批"""
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)

    start_date = date.fromisoformat(body.start_date) if body.start_date else None
    end_date = date.fromisoformat(body.end_date) if body.end_date else None

    svc = ApprovalService(db, store_id)
    approval = await svc.create_approval(
        employee_id=employee_id,
        approval_type=body.type,
        start_date=start_date,
        end_date=end_date,
        reason=body.reason,
        extra=body.extra,
        approver_id=body.approver_id,
    )

    name_map = await svc.repo.get_employee_name_map([approval.employee_id])

    # 推送审批提醒通知给店长/老板（或指定审批人）
    try:
        from app.services.notification_service import NotificationService
        notif_svc = NotificationService(db, store_id)
        applicant_name = name_map.get(approval.employee_id, "员工")
        type_label = TYPE_LABELS.get(approval.type, approval.type)
        title = f"新{type_label}审批待处理"
        content = f"{applicant_name} 提交了{type_label}申请：{approval.reason or '无原因'}"
        if approval.start_date:
            content += f"（{approval.start_date}"
            if approval.end_date and approval.end_date != approval.start_date:
                content += f" ~ {approval.end_date}"
            content += "）"

        target_user_ids = None
        if approval.approver_id:
            # 指定了审批人，只通知他
            target_user_ids = [approval.approver_id]

        await notif_svc.send(
            notification_type="approval_pending",
            title=title,
            content=content,
            target_user_ids=target_user_ids,
            channel="all",  # 站内 + 企微
            extra={"approval_id": approval.id, "type": approval.type},
        )
    except Exception as e:
        # 通知失败不影响主流程
        from loguru import logger
        logger.warning(f"推送审批提醒失败: {e}")

    return make_response(
        request=request,
        message="审批已提交",
        data=_approval_to_dict(approval, name_map),
    )


# ==================== 请假类型 & 假期余额（必须在 /{approval_id} 之前定义） ====================

@router.post("/upload")
async def upload_expense_image(
    request: Request,
    file: UploadFile = File(...),
):
    """上传报销附件图片"""
    store_id = get_store_id(request)
    # 校验文件类型
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise ValidationError("仅支持 JPG/PNG/WebP/GIF 图片")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ValidationError("图片大小不能超过 10MB")

    # 保存到 uploads/expense/
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads", "expense"
    )
    os.makedirs(upload_dir, exist_ok=True)
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/uploads/expense/{safe_name}"
    return make_response(request=request, data={"url": url}, message="上传成功")


@router.get("/leave-types")
async def get_leave_types(request: Request):
    """获取请假子类型字典"""
    return make_response(request=request, data={"types": LEAVE_TYPES})


@router.get("/leave-balance")
async def get_my_leave_balance(
    request: Request,
    year: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """查询我的假期余额（员工自助）"""
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)
    if not employee_id:
        raise ValidationError("当前用户未绑定员工档案")

    from datetime import datetime as _dt
    y = year or _dt.now().year

    lb_repo = LeaveBalanceRepository(db, store_id)
    balances = await lb_repo.get_balance(employee_id, y)

    # 补全所有类型（即使没有记录也显示默认值）
    existing_map = {b.leave_type: b for b in balances}
    result = []
    for k, v in LEAVE_TYPES.items():
        b = existing_map.get(k)
        total = b.total_days if b else v["default_days"]
        used = b.used_days if b else 0
        result.append({
            "leave_type": k,
            "label": v["label"],
            "total_days": total,
            "used_days": used,
            "remaining_days": max(0, total - used),
        })

    return make_response(request=request, data={"year": y, "balances": result})


@router.get("/{approval_id}")
async def get_approval(
    request: Request,
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """审批详情"""
    store_id = get_store_id(request)
    repo = ApprovalRepository(db, store_id)
    approval = await repo.get_approval_by_id(approval_id)
    if not approval:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("审批记录不存在")
    name_map = await repo.get_employee_name_map([approval.employee_id])
    return make_response(request=request, data=_approval_to_dict(approval, name_map))


@router.put("/{approval_id}/approve")
async def approve_approval(
    request: Request,
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """审批通过"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    role = getattr(request.state, "role", "staff")

    # 查询审批记录，判断权限
    repo = ApprovalRepository(db, store_id)
    approval = await repo.get_approval_by_id(approval_id)
    if not approval:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("审批记录不存在")

    # 权限校验：
    # - 店长/老板可审批所有
    # - 调班类型：被调班员工（approver_id == 当前用户）可审批
    is_manager = role in ("boss", "store_manager")
    is_assigned_approver = approval.approver_id == user_id
    if not (is_manager or (approval.type == "swap" and is_assigned_approver)):
        from app.utils.exceptions import ForbiddenError
        raise ForbiddenError("无权审批此记录")

    svc = ApprovalService(db, store_id)
    approval = await svc.approve(approval_id, user_id)
    name_map = await svc.repo.get_employee_name_map([approval.employee_id])

    # 通知申请人审批已通过
    try:
        from app.services.notification_service import NotificationService
        from sqlalchemy import select as sa_select
        from app.models.user import User
        notif_svc = NotificationService(db, store_id)
        type_label = TYPE_LABELS.get(approval.type, approval.type)
        user_id_row = await db.execute(
            sa_select(User.id).where(User.employee_id == approval.employee_id)
        )
        applicant_user_id = user_id_row.scalar()
        if applicant_user_id:
            await notif_svc.send(
                notification_type="approval_result",
                title=f"您的{type_label}申请已通过",
                content=f"您提交的{type_label}申请已审批通过。",
                target_user_ids=[applicant_user_id],
                channel="all",
                extra={"approval_id": approval.id, "result": "approved"},
            )
    except Exception as e:
        from loguru import logger
        logger.warning(f"推送审批结果通知失败: {e}")

    return make_response(request=request, message="审批已通过", data=_approval_to_dict(approval, name_map))


@router.put("/{approval_id}/reject")
async def reject_approval(
    request: Request,
    approval_id: uuid.UUID,
    body: ApprovalReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """审批驳回"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)

    svc = ApprovalService(db, store_id)
    reason = body.reason if body else None
    approval = await svc.reject(approval_id, user_id, reject_reason=reason)
    name_map = await svc.repo.get_employee_name_map([approval.employee_id])

    # 通知申请人审批被驳回
    try:
        from app.services.notification_service import NotificationService
        from sqlalchemy import select as sa_select
        from app.models.user import User
        notif_svc = NotificationService(db, store_id)
        type_label = TYPE_LABELS.get(approval.type, approval.type)
        user_id_row = await db.execute(
            sa_select(User.id).where(User.employee_id == approval.employee_id)
        )
        applicant_user_id = user_id_row.scalar()
        if applicant_user_id:
            content = f"您提交的{type_label}申请被驳回。"
            if approval.reject_reason:
                content += f" 驳回原因：{approval.reject_reason}"
            await notif_svc.send(
                notification_type="approval_result",
                title=f"您的{type_label}申请被驳回",
                content=content,
                target_user_ids=[applicant_user_id],
                channel="all",
                extra={"approval_id": approval.id, "result": "rejected"},
            )
    except Exception as e:
        from loguru import logger
        logger.warning(f"推送审批结果通知失败: {e}")

    return make_response(request=request, message="审批已驳回", data=_approval_to_dict(approval, name_map))


@router.get("/leave-balance/{employee_id}")
async def get_employee_leave_balance(
    request: Request,
    employee_id: uuid.UUID,
    year: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """查询指定员工的假期余额（店长/老板）"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)

    from datetime import datetime as _dt
    y = year or _dt.now().year

    lb_repo = LeaveBalanceRepository(db, store_id)
    balances = await lb_repo.get_balance(employee_id, y)

    existing_map = {b.leave_type: b for b in balances}
    result = []
    for k, v in LEAVE_TYPES.items():
        b = existing_map.get(k)
        total = b.total_days if b else v["default_days"]
        used = b.used_days if b else 0
        result.append({
            "leave_type": k,
            "label": v["label"],
            "total_days": total,
            "used_days": used,
            "remaining_days": max(0, total - used),
        })

    return make_response(request=request, data={"year": y, "balances": result})


@router.put("/leave-balance/{employee_id}/{leave_type}")
async def update_leave_balance(
    request: Request,
    employee_id: uuid.UUID,
    leave_type: str,
    total_days: float = Query(..., ge=0),
    year: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """调整员工假期余额（仅老板）"""
    require_role(request, ["system_admin", "boss"])
    if leave_type not in LEAVE_TYPES:
        raise ValidationError(f"无效的请假类型: {leave_type}")

    store_id = get_store_id(request)
    from datetime import datetime as _dt
    y = year or _dt.now().year

    lb_repo = LeaveBalanceRepository(db, store_id)
    balances = await lb_repo.get_balance(employee_id, y)
    existing = next((b for b in balances if b.leave_type == leave_type), None)

    if existing:
        existing.total_days = total_days
        await db.flush()
    else:
        from app.models.leave_balance import LeaveBalance
        new_balance = LeaveBalance(
            store_id=store_id,
            employee_id=employee_id,
            year=y,
            leave_type=leave_type,
            total_days=total_days,
            used_days=0,
        )
        db.add(new_balance)
        await db.flush()

    await db.commit()
    return make_response(request=request, message="假期余额已更新")
