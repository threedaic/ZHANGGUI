"""操作日志查询 API"""
import uuid
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.audit import AuditLog
from app.utils.deps import make_response, get_store_id, require_role

router = APIRouter()


@router.get("")
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: str | None = Query(None, description="表名筛选"),
    action: str | None = Query(None, description="操作类型: create/update/delete"),
    user_id: uuid.UUID | None = Query(None, description="操作人筛选"),
    date_from: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """查询操作日志（老板/店长可看）"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)

    # 构建查询
    q = select(AuditLog).where(AuditLog.store_id == store_id)

    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if action:
        q = q.where(AuditLog.action == action)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if date_from:
        q = q.where(AuditLog.created_at >= f"{date_from}T00:00:00")
    if date_to:
        q = q.where(AuditLog.created_at <= f"{date_to}T23:59:59")

    # 总数
    count_q = select(func.count()).select_from(q.alias("sub"))
    total = (await db.execute(count_q)).scalar() or 0

    # 分页
    q = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()

    # 关联用户名
    from app.models.user import User
    user_ids = list({log.user_id for log in logs if log.user_id})
    user_map = {}
    if user_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        user_map = {u.id: u.username for u in user_result.scalars().all()}

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": user_map.get(log.user_id, "系统"),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "request_id": log.request_id,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        })

    return make_response(request=request, data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
