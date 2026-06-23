"""
消息通知 API

路由映射：
GET  /                    消息列表
PUT  /{notification_id}/read   标记已读
PUT  /read-all          全部已读
GET  /unread-count      未读数
GET  /settings          推送设置（老板）
POST /settings          保存推送设置（老板）
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.notification_service import NotificationService
from app.repositories.notification import NotificationRepository
from app.schemas.notification import NotificationSettingSaveRequest
from app.utils.deps import get_store_id, get_user_id, require_role, make_response
from app.utils.exceptions import AppError
from app.utils.pagination import PageParams, paginate
from pydantic import BaseModel

router = APIRouter()


class TestWebhookRequest(BaseModel):
    webhook_url: str


@router.get("")
async def list_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """消息列表"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = NotificationRepository(db, store_id)
    params = PageParams(page=page, page_size=page_size)

    notifications, total = await repo.list_notifications(user_id, page=params)
    items = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "channel": n.channel,
            "is_read": n.is_read,
            "created_at": str(n.created_at) if n.created_at else None,
        }
        for n in notifications
    ]
    result = paginate(items, total, params)
    return make_response(request=request, data=result.model_dump())


@router.put("/{notification_id}/read")
async def mark_read(
    request: Request,
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """标记已读"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = NotificationRepository(db, store_id)
    ok = await repo.mark_read(notification_id, user_id)
    return make_response(request=request, message="已标记为已读", data={"success": ok})


@router.put("/read-all")
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """全部已读"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = NotificationRepository(db, store_id)
    count = await repo.mark_all_read(user_id)
    return make_response(request=request, message=f"已标记 {count} 条消息为已读", data={"count": count})


@router.get("/unread-count")
async def unread_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """未读消息数"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = NotificationRepository(db, store_id)
    count = await repo.get_unread_count(user_id)
    return make_response(request=request, data={"unread_count": count})


@router.get("/settings")
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """推送设置（仅老板/店长）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    svc = NotificationService(db, store_id)
    settings = await svc.get_settings()
    return make_response(
        request=request,
        data=[
            {
                "id": s.id,
                "setting_key": s.setting_key,
                "enabled": s.enabled,
                "channel": s.channel,
                "push_to_group": s.push_to_group,
                "target_roles": s.target_roles,
                "schedule_time": s.schedule_time,
            }
            for s in settings
        ],
    )


@router.post("/settings")
async def save_setting(
    request: Request,
    body: NotificationSettingSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存推送设置（仅老板/店长）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    svc = NotificationService(db, store_id)
    setting = await svc.save_setting(body.model_dump())
    await db.commit()

    # 如果修改的是开闭店提醒时间，刷新定时任务
    if body.setting_key in ("butler_opening_overdue", "butler_closing_overdue") and body.schedule_time:
        try:
            from app.tasks.scheduler import refresh_butler_reminder_jobs
            refresh_butler_reminder_jobs()
        except Exception as e:
            from loguru import logger
            logger.warning(f"刷新开闭店提醒任务失败: {e}")

    return make_response(
        request=request,
        message="设置已保存",
        data={
            "id": setting.id,
            "setting_key": setting.setting_key,
            "enabled": setting.enabled,
            "channel": setting.channel,
            "push_to_group": setting.push_to_group,
            "target_roles": setting.target_roles,
            "schedule_time": setting.schedule_time,
        },
    )


@router.post("/test-webhook")
async def test_webhook(
    request: Request,
    body: TestWebhookRequest,
):
    """测试群机器人 Webhook 是否可用。仅老板可操作。"""
    require_role(request, ["boss"])
    from app.services.wecom_notify import send_to_group

    ok = await send_to_group(
        body.webhook_url,
        "## 测试消息\nCrush掌柜群机器人配置成功。\n\n这条消息由掌柜系统自动发送，确认 Webhook 地址有效。",
    )
    if ok:
        return make_response(request=request, message="测试消息已发送")
    else:
        raise AppError(code=50200, message="企微群消息发送失败，请检查 Webhook 地址是否正确", http_status=502)
