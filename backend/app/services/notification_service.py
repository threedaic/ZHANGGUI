"""
统一消息通知 Service
- 站内信
- 企微应用消息
- 企微群机器人（支持文本+图片）
"""
import base64
import hashlib
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.notification import Notification, NotificationSetting
from app.repositories.notification import NotificationRepository
from app.models.user import User
from app.models.employee import Employee
from app.services.wework import get_access_token
from app.utils.http_client import http_client
from app.utils.redis_client import get_redis


WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin"


class NotificationService:
    """通知 Service"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id
        self.repo = NotificationRepository(session, store_id)

    async def send(
        self,
        notification_type: str,
        title: str,
        content: str,
        target_user_ids: list[int] | None = None,
        channel: str | None = None,
        extra: dict[str, Any] | None = None,
        push_to_group: bool | None = None,
    ) -> list[Notification]:
        """发送通知（统一推送入口）

        所有模块统一调用此方法发送推送，推送行为由 notification_settings 表配置控制：
        - enabled: 总开关
        - channel: 站内信/企微应用消息（in_app / wecom / all）
        - push_to_group: 是否同时推送到企微群机器人
        - target_roles: 接收角色
        - schedule_time: 定时推送时间（由定时任务读取）

        参数覆盖优先级：调用方传参 > setting 配置 > 默认值

        target_user_ids: 指定接收用户，None 表示按 setting 中 target_roles 发送
        channel: 强制渠道，None 则读取 setting
        push_to_group: 强制是否群推送，None 则读取 setting
        """
        setting = await self.repo.get_setting_by_key(notification_type)
        if setting and not setting.enabled:
            return []

        if channel is None:
            channel = setting.channel if setting else "in_app"

        if push_to_group is None:
            push_to_group = bool(setting.push_to_group) if setting else False

        if target_user_ids is None:
            target_roles = setting.target_roles if setting else ["boss", "store_manager"]
            target_user_ids = await self._resolve_user_ids_by_roles(target_roles)

        notifications = []
        for user_id in target_user_ids:
            notification = Notification(
                store_id=self.store_id,
                user_id=user_id,
                type=notification_type,
                title=title,
                content=content,
                channel=channel,
                extra=extra,
            )
            notifications.append(await self.repo.create_notification(notification))

        # 企微应用消息推送
        if channel in ("wecom", "all"):
            await self._push_wecom_to_users(target_user_ids, title, content)

        # 企微群机器人推送（受 push_to_group 配置控制）
        if push_to_group:
            await self.send_group_text(f"{title}\n{content}")

        return notifications

    async def send_alert(
        self,
        notification_type: str,
        title: str,
        detail: str,
    ) -> None:
        """统一告警推送入口（替代 wecom_notify.notify_alert）

        告警类消息统一走此方法，推送行为由 notification_settings 表配置控制。
        同时发送站内信 + 企微群机器人（如果 push_to_group 开启）。

        使用场景：防飞单预警、低分评分预警、存酒盘点通知、系统异常告警等。
        """
        await self.send(
            notification_type=notification_type,
            title=title,
            content=detail,
            channel="all",
        )

    async def _resolve_user_ids_by_roles(self, roles: list[str]) -> list[int]:
        """根据角色解析用户 ID 列表"""
        from sqlalchemy import select, and_
        stmt = select(User).join(Employee, User.employee_id == Employee.id).where(
            and_(
                Employee.store_id == self.store_id,
                User.role.in_(roles),
                User.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return [u.id for u in result.scalars().all()]

    async def _push_wecom_to_users(
        self,
        user_ids: list[int],
        title: str,
        content: str,
    ) -> None:
        """通过企微应用消息推送给指定用户"""
        # 企微应用消息推送，wecom_notify.py 暂未覆盖此场景
        try:
            from sqlalchemy import select, and_
            stmt = select(User).join(Employee, User.employee_id == Employee.id).where(
                and_(
                    User.id.in_(user_ids),
                    Employee.store_id == self.store_id,
                )
            )
            result = await self.session.execute(stmt)
            users = result.scalars().all()

            # 收集有 employee 关联的 wework_userid
            emp_stmt = select(Employee).join(User, User.employee_id == Employee.id).where(
                and_(
                    Employee.store_id == self.store_id,
                    User.id.in_(user_ids),
                    Employee.wework_userid.isnot(None),
                )
            )
            emp_result = await self.session.execute(emp_stmt)
            userids = [e.wework_userid for e in emp_result.scalars().all()]

            if not userids:
                return

            token = await get_access_token(self.session, self.store_id)
            url = f"{WECOM_API}/message/send?access_token={token}"
            body = {
                "touser": "|".join(userids),
                "msgtype": "textcard",
                "agentid": await self._get_agent_id(),
                "textcard": {
                    "title": title,
                    "description": content,
                    "url": "https://zhanggui.crushserver.cloud/notifications",
                },
            }
            resp = await http_client.post(url, json_body=body)
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"企微消息推送失败: {data}")
        except Exception as e:
            logger.error(f"企微推送异常: {e}")

    async def _get_agent_id(self) -> int:
        from sqlalchemy import select
        from app.models.store import Store
        stmt = select(Store).where(Store.id == self.store_id)
        result = await self.session.execute(stmt)
        store = result.scalar_one_or_none()
        return store.wework_agent_id if store and store.wework_agent_id else 0

    async def _get_bot_config(self) -> tuple[bool, str | None]:
        """获取本店群机器人配置（开关 + webhook URL）

        从 StoreSettings 表读取，而非 Store 表。
        返回 (enabled, webhook_url)。未配置时返回 (False, None)。
        """
        from sqlalchemy import select
        from app.models.store import StoreSettings
        stmt = select(StoreSettings).where(StoreSettings.store_id == self.store_id)
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()
        if not settings:
            return False, None
        enabled = bool(settings.wecom_bot_enabled)
        webhook = settings.wecom_webhook_url if settings.wecom_webhook_url else None
        return enabled, webhook

    async def send_group_text(self, content: str) -> bool:
        """通过群机器人发送文本消息（受 wecom_bot_enabled 开关控制）"""
        enabled, webhook = await self._get_bot_config()
        if not enabled:
            logger.info(f"store {self.store_id} 群机器人未开启，跳过文本推送")
            return False
        if not webhook:
            logger.warning(f"store {self.store_id} 群机器人已开启但未配置 webhook")
            return False
        try:
            body = {"msgtype": "text", "text": {"content": content}}
            resp = await http_client.post(webhook, json_body=body)
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"群机器人文本发送失败: {data}")
                return False
            return True
        except Exception as e:
            logger.error(f"群机器人文本发送异常: {e}")
            return False

    async def send_group_image(self, image_bytes: bytes) -> bool:
        """通过群机器人发送图片（base64+md5，受 wecom_bot_enabled 开关控制）"""
        enabled, webhook = await self._get_bot_config()
        if not enabled:
            logger.info(f"store {self.store_id} 群机器人未开启，跳过图片推送")
            return False
        if not webhook:
            logger.warning(f"store {self.store_id} 群机器人已开启但未配置 webhook")
            return False
        try:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            md5 = hashlib.md5(image_bytes).hexdigest()
            body = {
                "msgtype": "image",
                "image": {"base64": b64, "md5": md5},
            }
            resp = await http_client.post(webhook, json_body=body)
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"群机器人图片发送失败: {data}")
                return False
            return True
        except Exception as e:
            logger.error(f"群机器人图片发送异常: {e}")
            return False

    async def send_group_markdown(self, content: str) -> bool:
        """通过群机器人发送 markdown 消息（受 wecom_bot_enabled 开关控制）"""
        enabled, webhook = await self._get_bot_config()
        if not enabled:
            logger.info(f"store {self.store_id} 群机器人未开启，跳过 markdown 推送")
            return False
        if not webhook:
            logger.warning(f"store {self.store_id} 群机器人已开启但未配置 webhook")
            return False
        try:
            body = {"msgtype": "markdown", "markdown": {"content": content}}
            resp = await http_client.post(webhook, json_body=body)
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"群机器人markdown发送失败: {data}")
                return False
            return True
        except Exception as e:
            logger.error(f"群机器人markdown发送异常: {e}")
            return False

    async def get_settings(self) -> list[NotificationSetting]:
        return await self.repo.get_settings()

    async def save_setting(self, data: dict[str, Any]) -> NotificationSetting:
        setting_key = data["setting_key"]
        existing = await self.repo.get_setting_by_key(setting_key)
        if existing:
            for key in ["enabled", "channel", "push_to_group", "target_roles", "schedule_time"]:
                if key in data:
                    setattr(existing, key, data[key])
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        new_setting = NotificationSetting(store_id=self.store_id, **data)
        return await self.repo.save_setting(new_setting)
