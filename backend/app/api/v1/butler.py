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
    require_role(request, ["boss", "store_manager"])
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
    require_role(request, ["boss", "store_manager"])
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
    require_role(request, ["boss", "store_manager"])
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
    require_role(request, ["boss", "store_manager"])
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
    require_role(request, ["boss", "store_manager"])
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


# ==================== 看板 ====================

@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """多店开闭店状态看板（仅老板）"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    repo = ButlerRepository(db, store_id)
    data = await repo.get_all_stores_status()
    return make_response(request=request, data=data)
