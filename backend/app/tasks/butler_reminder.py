"""
开闭店检查单定时提醒任务

规则：
- 开店检查单：每天 11:00 检查，若今日无开店会话则提醒
- 闭店检查单：每天 23:00 检查，若今日无闭店会话则提醒
- 超时未执行：标记提醒，连续未执行可计入考核
"""
import uuid
from datetime import datetime, date, timedelta
from loguru import logger
from sqlalchemy import select, and_, func
from app.database import AsyncSessionLocal
from app.models.store import Store
from app.models.butler import ClosingSession, ClosingChecklistTemplate
from app.services.notification_service import NotificationService


async def _get_active_stores(db) -> list[Store]:
    """获取所有活跃门店"""
    result = await db.execute(select(Store).where(Store.status == "active"))
    return list(result.scalars().all())


async def _has_session_today(db, store_id: uuid.UUID, session_type: str) -> bool:
    """检查今日是否已有指定类型的检查会话"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    stmt = select(func.count(ClosingSession.id)).where(
        and_(
            ClosingSession.store_id == store_id,
            ClosingSession.session_type == session_type,
            ClosingSession.started_at >= today_start,
            ClosingSession.started_at <= today_end,
        )
    )
    result = await db.execute(stmt)
    return (result.scalar() or 0) > 0


async def _has_template(db, store_id: uuid.UUID, session_type: str) -> bool:
    """检查门店是否配置了指定类型的检查单模板"""
    stmt = select(func.count(ClosingChecklistTemplate.id)).where(
        and_(
            ClosingChecklistTemplate.store_id == store_id,
            ClosingChecklistTemplate.session_type == session_type,
        )
    )
    result = await db.execute(stmt)
    return (result.scalar() or 0) > 0


async def butler_opening_reminder_job():
    """开店检查单提醒：每天 11:00 执行（时间由 schedule_time 配置控制）"""
    logger.info("[开闭店提醒] 开始检查开店检查单执行情况")
    async with AsyncSessionLocal() as db:
        stores = await _get_active_stores(db)
        reminded = 0
        for store in stores:
            try:
                # 没配置开店检查单的门店跳过
                if not await _has_template(db, store.id, "opening"):
                    continue
                # 今日已执行则跳过
                if await _has_session_today(db, store.id, "opening"):
                    continue
                # 统一推送（站内信 + 企微群，由 butler_opening_overdue 配置控制）
                notif = NotificationService(db, store.id)
                text = (
                    f"门店：{store.name}\n"
                    f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"今日尚未执行开店检查单，请店长尽快完成！"
                )
                await notif.send(
                    notification_type="butler_opening_overdue",
                    title="开店检查单未执行提醒",
                    content=text,
                    channel="all",
                )
                await db.commit()
                reminded += 1
            except Exception as e:
                logger.error(f"[开闭店提醒] 门店 {store.id} 开店提醒失败: {e}")
        logger.info(f"[开闭店提醒] 开店检查完成，提醒 {reminded} 家门店")


async def butler_closing_reminder_job():
    """闭店检查单提醒：每天 23:00 执行（时间由 schedule_time 配置控制）"""
    logger.info("[开闭店提醒] 开始检查闭店检查单执行情况")
    async with AsyncSessionLocal() as db:
        stores = await _get_active_stores(db)
        reminded = 0
        for store in stores:
            try:
                if not await _has_template(db, store.id, "closing"):
                    continue
                if await _has_session_today(db, store.id, "closing"):
                    continue
                notif = NotificationService(db, store.id)
                text = (
                    f"门店：{store.name}\n"
                    f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"今日尚未执行闭店检查单，请店长尽快完成！"
                )
                await notif.send(
                    notification_type="butler_closing_overdue",
                    title="闭店检查单未执行提醒",
                    content=text,
                    channel="all",
                )
                await db.commit()
                reminded += 1
            except Exception as e:
                logger.error(f"[开闭店提醒] 门店 {store.id} 闭店提醒失败: {e}")
        logger.info(f"[开闭店提醒] 闭店检查完成，提醒 {reminded} 家门店")
