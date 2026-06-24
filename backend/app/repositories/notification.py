"""
消息通知数据访问层
"""
import uuid
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, NotificationSetting
from app.utils.pagination import PageParams


class NotificationRepository:
    """消息 Repository"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def create_notification(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        page: PageParams | None = None,
    ) -> tuple[list[Notification], int]:
        stmt = (
            select(Notification)
            .where(
                and_(
                    Notification.store_id == self.store_id,
                    Notification.user_id == user_id,
                )
            )
            .order_by(Notification.created_at.desc())
        )

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.store_id == self.store_id,
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def mark_read(self, notification_id: int, user_id: uuid.UUID) -> bool:
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.store_id == self.store_id,
                    Notification.user_id == user_id,
                )
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.store_id == self.store_id,
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_settings(self) -> list[NotificationSetting]:
        stmt = (
            select(NotificationSetting)
            .where(NotificationSetting.store_id == self.store_id)
            .order_by(NotificationSetting.setting_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_setting_by_key(self, setting_key: str) -> NotificationSetting | None:
        stmt = select(NotificationSetting).where(
            and_(
                NotificationSetting.store_id == self.store_id,
                NotificationSetting.setting_key == setting_key,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_setting(self, setting: NotificationSetting) -> NotificationSetting:
        self.session.add(setting)
        await self.session.flush()
        await self.session.refresh(setting)
        return setting
