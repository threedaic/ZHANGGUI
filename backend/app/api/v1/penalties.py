"""
奖惩通知 API 路由
/api/v1/penalties/

POST   /          创建奖惩通知 + 自动生成签收任务
GET    /          奖惩通知列表
GET    /{id}      奖惩通知详情
PUT    /{id}      修改 draft 状态的奖惩通知
DELETE /{id}      删除 draft 状态的奖惩通知
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.penalty import PenaltyCreateRequest, PenaltyUpdateRequest, NOTICE_TYPES
from app.services.penalty import PenaltyService
from app.utils.deps import require_role, require_employee_id, make_response
from app.utils.exceptions import NotFoundError, ConflictError, ValidationError

router = APIRouter()


def _get_service(request: Request, db: AsyncSession) -> PenaltyService:
    store_id = getattr(request.state, "store_id", None)
    return PenaltyService(db, store_id)


@router.post("", summary="创建奖惩通知")
async def create_penalty(
    request: Request,
    body: PenaltyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    issuer_id = require_employee_id(request)
    service = _get_service(request, db)
    notice = await service.create(
        employee_id=body.employee_id,
        penalty_type=body.penalty_type,
        amount=body.amount,
        reason=body.reason,
        issued_by=issuer_id,
        auto_issue=True,
    )
    await db.commit()
    return make_response(
        message="奖惩通知已发布，员工将收到签收提醒",
        data={"id": notice.id, "status": notice.status},
        request=request,
    )


@router.get("", summary="奖惩通知列表")
async def list_penalties(
    request: Request,
    penalty_type: str | None = Query(None),
    status: str | None = Query(None, pattern="^(draft|issued|acknowledged)$"),
    employee_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager", "accountant"])
    service = _get_service(request, db)
    items, total = await service.get_list(
        penalty_type=penalty_type,
        status=status,
        employee_id=employee_id,
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


@router.get("/types", summary="奖惩类型选项")
async def penalty_types(request: Request):
    """返回奖惩类型键值列表，供前端下拉菜单使用"""
    return make_response(data=[
        {"value": k, "label": v} for k, v in NOTICE_TYPES.items()
    ], request=request)


@router.get("/{notice_id}", summary="奖惩通知详情")
async def get_penalty(
    request: Request,
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager", "accountant"])
    service = _get_service(request, db)
    detail = await service.get_detail(notice_id)
    if not detail:
        raise NotFoundError("奖惩通知不存在")
    return make_response(data=detail, request=request)


@router.put("/{notice_id}", summary="修改奖惩通知（仅 draft 状态）")
async def update_penalty(
    request: Request,
    notice_id: uuid.UUID,
    body: PenaltyUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    service = _get_service(request, db)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise ValidationError("没有提供要修改的字段")
    notice = await service.update(notice_id, **updates)
    if not notice:
        raise ConflictError("只能修改草稿状态的奖惩通知")
    return make_response(message="修改成功", data={"id": notice.id}, request=request)


@router.delete("/{notice_id}", summary="删除奖惩通知（仅 draft 状态）")
async def delete_penalty(
    request: Request,
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "store_manager"])
    service = _get_service(request, db)
    ok = await service.delete(notice_id)
    if not ok:
        raise ConflictError("只能删除草稿状态的处罚通知")
    return make_response(message="已删除", request=request)
