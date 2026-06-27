"""
智能管家模块 API 路由
前缀: /api/v1/butler
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.butler import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistItemsBatchRequest,
    SessionStartRequest,
    ItemConfirmRequest,
    AdHocItemRequest,
    ManualReviewRequest,
)
from app.repositories.butler import ButlerRepository
from app.services.butler import (
    start_session,
    confirm_item,
    upload_photo,
    add_adhoc_item,
    manual_review,
    resubmit_photo,
)
from app.utils.deps import get_store_id, get_user_id, require_role, make_response
from app.utils.exceptions import NotFoundError, ValidationError

router = APIRouter()


def _serialize_template(tpl) -> dict:
    """Serialize ClosingChecklistTemplate, mapping Python attr 'id' to 'template_id'."""
    return {
        "template_id": tpl.id,
        "store_id": tpl.store_id,
        "name": tpl.name,
        "session_type": tpl.session_type,
        "role_tag": tpl.role_tag,
        "sort_order": tpl.sort_order,
        "is_active": tpl.is_active,
        "created_by": tpl.created_by,
        "created_at": tpl.created_at,
        "updated_at": tpl.updated_at,
    }


# ==================== 模板管理 ====================

@router.get("/templates")
async def list_templates(
    request: Request,
    session_type: str | None = Query(None, description="opening / closing"),
    db: AsyncSession = Depends(get_db),
):
    """获取门店所有清单模板"""
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    data = await repo.list_templates(session_type=session_type)
    return make_response(request=request, data=data)


@router.post("/templates")
async def create_template(
    request: Request,
    body: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建清单模板（老板/店长）"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    user_id = get_user_id(request)
    tpl = await repo.create_template({
        "name": body.name,
        "session_type": body.session_type,
        "role_tag": body.role_tag,
        "sort_order": body.sort_order,
        "created_by": user_id,
    })
    await db.commit()
    await db.refresh(tpl)
    d = _serialize_template(tpl)
    return make_response(request=request, data=d, message="模板创建成功")


@router.put("/templates/{template_id}")
async def update_template(
    request: Request,
    template_id: uuid.UUID,
    body: ChecklistTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板信息"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")
    tpl = await repo.update_template(tpl, **body.model_dump(exclude_none=True))
    await db.commit()
    await db.refresh(tpl)
    d = _serialize_template(tpl)
    return make_response(request=request, data=d, message="模板更新成功")


@router.delete("/templates/{template_id}")
async def delete_template(
    request: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除模板"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")
    await repo.delete_template(tpl)
    await db.commit()
    return make_response(request=request, message="模板已删除")


@router.post("/templates/{template_id}/items")
async def batch_update_items(
    request: Request,
    template_id: uuid.UUID,
    body: ChecklistItemsBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量更新模板的清单项（全量替换）"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")

    items_data = []
    for i, item in enumerate(body.items):
        items_data.append({
            "item_name": item.item_name.strip(),
            "item_type": item.item_type,
            "required_photo": item.item_type == "photo",
            "sort_order": item.sort_order if item.sort_order else i,
            "ai_prompt": item.ai_prompt.strip() if item.ai_prompt else None,
        })

    new_items = await repo.replace_items(template_id, items_data)
    await db.commit()
    return make_response(
        request=request,
        data={"template_id": template_id, "count": len(new_items)},
        message=f"清单项已更新（{len(new_items)}项）",
    )


# ==================== 会话管理 ====================

@router.post("/sessions")
async def create_session(
    request: Request,
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """开始开店/闭店"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    data = await start_session(db, store_id, user_id, body.session_type)
    await db.commit()
    return make_response(request=request, data=data, message=f"已开始{body.session_type}")


@router.get("/sessions/{session_id}")
async def get_session(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """查看会话详情（含各项状态）"""
    store_id = get_store_id(request)
    from app.services.butler import _build_session_detail
    repo = ButlerRepository(db, store_id)
    data = await _build_session_detail(repo, session_id)
    return make_response(request=request, data=data)


@router.get("/sessions")
async def list_sessions(
    request: Request,
    session_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """历史会话列表"""
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    items, total = await repo.list_sessions(session_type=session_type, page=page, page_size=page_size)
    data = {
        "items": [{
            "id": s.id,
            "store_id": s.store_id,
            "session_type": s.session_type,
            "operator_user_id": s.operator_user_id,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "total_items": s.total_items,
            "completed_items": s.completed_items,
        } for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return make_response(request=request, data=data)


# ==================== 检查项操作 ====================

@router.post("/sessions/{session_id}/items/{result_id}/confirm")
async def item_confirm(
    request: Request,
    session_id: uuid.UUID,
    result_id: uuid.UUID,
    body: ItemConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """打勾确认一个检查项"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    data = await confirm_item(db, store_id, session_id, result_id, user_id, body.comment)
    await db.commit()
    return make_response(request=request, data=data, message="已确认")


@router.post("/sessions/{session_id}/items/{result_id}/photo")
async def item_photo(
    request: Request,
    session_id: uuid.UUID,
    result_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """拍照上传检查项"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    content = await file.read()
    data = await upload_photo(db, store_id, session_id, result_id, user_id, content, file.filename or "photo.jpg")
    await db.commit()
    return make_response(request=request, data=data, message="照片已上传")


@router.post("/sessions/{session_id}/items")
async def add_item(
    request: Request,
    session_id: uuid.UUID,
    body: AdHocItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """临时添加检查项"""
    store_id = get_store_id(request)
    data = await add_adhoc_item(db, store_id, session_id, body.item_name, body.item_type)
    await db.commit()
    return make_response(request=request, data=data, message="临时项已添加")


@router.post("/sessions/{session_id}/items/{result_id}/review")
async def item_review(
    request: Request,
    session_id: uuid.UUID,
    result_id: uuid.UUID,
    body: ManualReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """店长/老板人工复核一个检查项"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    data = await manual_review(db, store_id, session_id, result_id, user_id, body.action, body.comment)
    await db.commit()
    msg = "已通过" if body.action == "pass" else "已驳回，员工需重新提交"
    return make_response(request=request, data=data, message=msg)


@router.post("/sessions/{session_id}/items/{result_id}/resubmit")
async def item_resubmit(
    request: Request,
    session_id: uuid.UUID,
    result_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """员工被驳回后重新拍照提交"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    content = await file.read()
    data = await resubmit_photo(db, store_id, session_id, result_id, user_id, content, file.filename or "photo.jpg")
    await db.commit()
    return make_response(request=request, data=data, message="已重新提交")


# ==================== 今日待办状态（首页提醒条用）====================

@router.get("/today-status")
async def get_today_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    返回当前门店今日的开/闭店检查状态。
    前端首页提醒条调用此接口，判断是否显示"闭店检查还没做"。

    返回:
      - has_opening_template: 是否配置了开店检查单
      - has_closing_template: 是否配置了闭店检查单
      - opening_done: 今日开店检查是否已完成
      - closing_done: 今日闭店检查是否已完成
      - opening_session: 今日开店会话信息（没有则 null）
      - closing_session: 今日闭店会话信息（没有则 null）
      - pending: 待办列表（用于首页提醒条展示）
    """
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    from app.repositories.butler_assignee import ButlerAssigneeRepository
    assignee_repo = ButlerAssigneeRepository(db, store_id)

    from datetime import date
    today = date.today()

    # 查模板
    opening_tpls = await repo.list_templates(session_type="opening")
    closing_tpls = await repo.list_templates(session_type="closing")
    has_opening = len(opening_tpls) > 0
    has_closing = len(closing_tpls) > 0

    # 查今日会话
    sessions, _ = await repo.list_sessions(page=1, page_size=50)
    today_opening = None
    today_closing = None
    for s in sessions:
        if s.started_at and s.started_at.date() == today:
            info = {
                "id": str(s.id),
                "status": s.status,
                "total_items": s.total_items,
                "completed_items": s.completed_items,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            }
            if s.session_type == "opening":
                today_opening = info
            elif s.session_type == "closing":
                today_closing = info

    opening_done = today_opening and today_opening["status"] == "completed"
    closing_done = today_closing and today_closing["status"] == "completed"

    # 组装 pending 列表
    from datetime import datetime as dt
    now = dt.now()
    current_hour = now.hour

    pending = []
    # 开店检查：只在上午显示（6:00-14:00）
    if has_opening and not opening_done and 6 <= current_hour <= 14:
        assignee = await assignee_repo.get_today_assignment("opening")
        pending.append({
            "type": "opening",
            "label": "开店检查",
            "session_id": today_opening["id"] if today_opening else None,
            "completed": today_opening["completed_items"] if today_opening else 0,
            "total": today_opening["total_items"] if today_opening else 0,
            "assignee_name": assignee["employee_name"] if assignee else None,
            "assignee_id": assignee["employee_id"] if assignee else None,
            "fallback_used": assignee["fallback_used"] if assignee else False,
            "fallback_reason": assignee["fallback_reason"] if assignee else None,
        })
    # 闭店检查：只在晚上显示（20:00-次日4:00）
    if has_closing and not closing_done and (current_hour >= 20 or current_hour <= 4):
        assignee = await assignee_repo.get_today_assignment("closing")
        pending.append({
            "type": "closing",
            "label": "闭店检查",
            "session_id": today_closing["id"] if today_closing else None,
            "completed": today_closing["completed_items"] if today_closing else 0,
            "total": today_closing["total_items"] if today_closing else 0,
            "assignee_name": assignee["employee_name"] if assignee else None,
            "assignee_id": assignee["employee_id"] if assignee else None,
            "fallback_used": assignee["fallback_used"] if assignee else False,
            "fallback_reason": assignee["fallback_reason"] if assignee else None,
        })

    return make_response(request=request, data={
        "has_opening_template": has_opening,
        "has_closing_template": has_closing,
        "opening_done": opening_done,
        "closing_done": closing_done,
        "pending": pending,
    })


# ==================== 看板 ====================

@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """多店开闭店状态看板（仅老板）"""
    require_role(request, ["boss", "system_admin"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    data = await repo.get_all_stores_status()
    return make_response(request=request, data=data)


# ==================== 执行人顺位配置 ====================

from pydantic import BaseModel
from typing import List, Optional


class AssigneeItem(BaseModel):
    employee_id: str
    priority: int


class AssigneeRuleSave(BaseModel):
    session_type: str            # opening / closing
    items: List[AssigneeItem]


@router.get("/assignee-rules")
async def list_assignee_rules(
    request: Request,
    session_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """查询本店执行人顺位配置（含员工姓名）"""
    store_id = get_store_id(request)
    repo = ButlerAssigneeRepository(db, store_id)
    data = await repo.list_rules(session_type=session_type)
    return make_response(request=request, data=data)


@router.post("/assignee-rules")
async def save_assignee_rules(
    request: Request,
    body: AssigneeRuleSave,
    db: AsyncSession = Depends(get_db),
):
    """整体替换某会话类型的顺位（管理端拖动保存）"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    if body.session_type not in ("opening", "closing"):
        raise ValidationError("session_type 只能是 opening 或 closing")
    store_id = get_store_id(request)
    repo = ButlerAssigneeRepository(db, store_id)
    await repo.replace_rules(
        session_type=body.session_type,
        items=[it.model_dump() for it in body.items],
    )
    data = await repo.list_rules(session_type=body.session_type)
    return make_response(request=request, data=data, message="顺位保存成功")


@router.get("/assignee-employees")
async def list_assignable_employees(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """列出本店可指派的员工（管理端配置顺位时下拉用）"""
    require_role(request, ["boss", "system_admin", "store_manager"])
    store_id = get_store_id(request)
    repo = ButlerAssigneeRepository(db, store_id)
    data = await repo.list_active_employees()
    return make_response(request=request, data=data)
