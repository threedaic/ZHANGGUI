"""
签收任务 API 路由
/api/v1/sign-tasks/

GET    /inbox              我的收件箱（分页）
GET    /inbox/count        待签收数量
GET    /{task_id}          签收详情
POST   /{task_id}/sign     签收确认
POST   /{task_id}/dispute  提出异议
GET    /issued             我发出的签收
GET    /issued/disputes    异议列表
POST   /{task_id}/remind   提醒员工
POST   /{task_id}/revoke   撤回重签
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.sign_task import SignRequest, BatchSignRequest, DisputeRequest, RevokeRequest
from app.services.sign_task import SignTaskService
from app.services.notification_service import NotificationService
from app.utils.deps import require_role, require_employee_id, make_response
from app.utils.exceptions import NotFoundError, ForbiddenError, ConflictError, ValidationError

router = APIRouter()


def _get_service(request: Request, db: AsyncSession) -> SignTaskService:
    store_id = getattr(request.state, "store_id", None)
    return SignTaskService(db, store_id)


# ==================== 员工端 ====================


@router.get("/inbox", summary="我的收件箱")
async def list_inbox(
    request: Request,
    status: str | None = Query(None, pattern="^(pending|signed|disputed|revoked)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    items, total = await service.get_inbox(
        employee_id=employee_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return make_response(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }, request=request)


@router.get("/inbox/count", summary="待签收数量")
async def pending_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    count = await service.get_pending_count(employee_id)
    return make_response(data={"pending": count}, request=request)


@router.post("/batch/sign", summary="批量签收")
async def batch_sign_tasks(
    request: Request,
    body: BatchSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """用同一份签名批量签收多个任务"""
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    result = await service.batch_sign(
        task_ids=body.task_ids,
        employee_id=employee_id,
        signature_data=body.signature_data,
        notes=body.notes,
    )
    msg = f"已签收 {result['success_count']} 项"
    if result["failed_count"]:
        msg += f"，{result['failed_count']} 项失败"
    return make_response(data=result, message=msg, request=request)


# ==================== 管理端 ====================


@router.get("/issued", summary="我发出的签收")
async def list_issued(
    request: Request,
    status: str | None = Query(None, pattern="^(pending|signed|disputed|revoked)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    require_role(request, ["boss", "store_manager", "accountant"])
    service = _get_service(request, db)
    items, total = await service.get_issued(
        issued_by=employee_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return make_response(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }, request=request)


@router.get("/issued/disputes", summary="异议列表")
async def list_disputes(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager", "accountant"])
    service = _get_service(request, db)
    items, total = await service.get_disputes(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return make_response(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }, request=request)


# ==================== 动态路径（必须放在所有静态路径之后） ====================


@router.get("/{task_id}", summary="签收详情")
async def get_task(
    request: Request,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    detail = await service.get_detail(task_id, employee_id)
    if not detail:
        raise NotFoundError("签收任务不存在")
    return make_response(data=detail, request=request)


@router.post("/{task_id}/sign", summary="签收确认")
async def sign_task(
    request: Request,
    task_id: uuid.UUID,
    body: SignRequest,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    ok = await service.sign(task_id, employee_id, body.signature_data, body.notes)
    if not ok:
        raise ConflictError("任务不存在或已处理")
    return make_response(message="签收成功", request=request)


@router.post("/{task_id}/dispute", summary="提出异议")
async def dispute_task(
    request: Request,
    task_id: uuid.UUID,
    body: DisputeRequest,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    ok = await service.dispute(task_id, employee_id, body.reason)
    if not ok:
        raise ConflictError("任务不存在或已处理")
    return make_response(message="异议已提交，管理员将尽快处理", request=request)


@router.post("/{task_id}/remind", summary="提醒员工签收")
async def remind_employee(
    request: Request,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager", "accountant"])
    store_id = getattr(request.state, "store_id", None)
    from app.repositories.sign_task import SignTaskRepository
    repo = SignTaskRepository(db, store_id)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError("签收任务不存在")
    if task.status != "pending":
        raise ConflictError("该任务已处理")

    # 推送企微提醒
    notifier = NotificationService(db, store_id)
    from app.models.user import User
    from app.models.employee import Employee
    from sqlalchemy import select, and_
    stmt = select(User.id).join(Employee, User.employee_id == Employee.id).where(
        and_(Employee.id == task.employee_id, User.is_active.is_(True))
    )
    result = await db.execute(stmt)
    user_ids = [row[0] for row in result.all()]

    if user_ids:
        await notifier.send(
            notification_type="sign_remind",
            title=f"请签收 - {task.title}",
            content=f"您有一份待签收任务：{task.title}，请在收件箱中及时处理。",
            target_user_ids=user_ids,
            channel="all",
            extra={"task_id": task_id},
        )
    return make_response(message="已发送提醒", request=request)


@router.post("/{task_id}/revoke", summary="撤回重签")
async def revoke_task(
    request: Request,
    task_id: uuid.UUID,
    body: RevokeRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    employee_id = require_employee_id(request)
    service = _get_service(request, db)
    ok = await service.revoke(
        task_id,
        reason=body.reason if body else None,
        revoked_by=employee_id,
    )
    if not ok:
        raise ConflictError("只能撤回已签收的任务")
    return make_response(message="已撤回，员工需重新签收", request=request)
