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


@router.get("/app-config")
async def get_app_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """查询自建应用配置状态。

    所有门店共用同一企业微信主体，企微配置（corp_id/agent_id/secret）由系统环境变量统一配置，
    老板无需重复填写。此接口返回配置状态 + 推送开关，前端据此显示开关状态。
    不返回 secret 等敏感信息。
    """
    from app.config import get_settings
    settings = get_settings()
    configured = bool(settings.WECOM_CORP_ID and settings.WECOM_SECRET and settings.WECOM_AGENT_ID)

    # 读取门店自建应用推送开关（存于 StoreSettings.extra_config.wecom_app_enabled）
    # 默认：已配置则开启，未配置则关闭
    store_id = get_store_id(request)
    from sqlalchemy import select
    from app.models.store import StoreSettings
    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    store_settings = result.scalar_one_or_none()
    extra = store_settings.extra_config if store_settings and store_settings.extra_config else {}
    enabled = bool(extra.get("wecom_app_enabled", configured))

    return make_response(
        request=request,
        data={
            "configured": configured,
            "enabled": enabled,
            "source": "env" if configured else "store",
            "corp_id": settings.WECOM_CORP_ID if configured else "",
            "agent_id": settings.WECOM_AGENT_ID if configured else "",
        },
    )


class AppEnabledRequest(BaseModel):
    enabled: bool


@router.put("/app-enabled")
async def set_app_enabled(
    body: AppEnabledRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """保存自建应用推送开关（存入 StoreSettings.extra_config.wecom_app_enabled）。仅老板可操作。"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)

    from sqlalchemy import select
    from app.models.store import StoreSettings
    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    if not settings:
        settings = StoreSettings(store_id=store_id)
        db.add(settings)
    extra = settings.extra_config if settings.extra_config else {}
    extra["wecom_app_enabled"] = body.enabled
    settings.extra_config = extra
    await db.commit()
    return make_response(request=request, message="已更新", data={"enabled": body.enabled})


@router.post("/test-webhook")
async def test_webhook(
    request: Request,
    body: TestWebhookRequest,
):
    """测试群机器人 Webhook 是否可用。仅老板可操作。"""
    require_role(request, ["boss"])
    from app.services.notification_service import send_to_group

    ok = await send_to_group(
        body.webhook_url,
        "## 测试消息\nCrush掌柜群机器人配置成功。\n\n这条消息由掌柜系统自动发送，确认 Webhook 地址有效。",
    )
    if ok:
        return make_response(request=request, message="测试消息已发送")
    else:
        raise AppError(code=50200, message="企微群消息发送失败，请检查 Webhook 地址是否正确", http_status=502)


@router.post("/test-app")
async def test_app_push(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """测试自建应用消息推送（推送给当前老板自己的企微）。仅老板可操作。

    需要门店已配置 corp_id / agent_id / secret，且老板账号已绑定企微 userid
    （通过「企业微信配置」页同步通讯录后自动绑定）。
    """
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)

    from sqlalchemy import select, and_
    from app.models.user import User
    from app.models.employee import Employee

    stmt = select(Employee).join(User, User.employee_id == Employee.id).where(
        and_(User.id == user_id, Employee.store_id == store_id)
    )
    result = await db.execute(stmt)
    emp = result.scalar_one_or_none()
    if not emp or not emp.wework_userid:
        raise AppError(
            code=40000,
            message="当前老板未绑定企微账号，无法测试。请先在「企业微信配置」同步通讯录。",
        )

    svc = NotificationService(db, store_id)
    ok, msg = await svc.send_app_message(
        wework_userids=[emp.wework_userid],
        title="测试消息",
        content="Crush掌柜自建应用推送配置成功。这条消息由系统自动发送，确认应用配置有效。",
    )
    if ok:
        return make_response(request=request, message="测试消息已发送到您的企微")
    else:
        raise AppError(code=50200, message=f"推送失败: {msg}", http_status=502)
