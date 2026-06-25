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

# 推送项默认配置（新门店数据库无记录时，前端也能看到全部推送项）
# target_roles 决定默认推给谁；channel 固定 all（站内信+企微应用）；push_to_group 跟随群机器人总开关
DEFAULT_SETTINGS = {
    # 老板该看的
    "system_error": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss"], "schedule_time": None},
    "antifraud_alert": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss"], "schedule_time": None},
    "rating_alert": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss"], "schedule_time": None},
    "wine_stocktake_alert": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss"], "schedule_time": None},
    "penalty_notice": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "butler_manual_review": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "daily_report": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "attendance_alert": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "butler_opening_overdue": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": "11:00"},
    "butler_closing_overdue": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": "23:00"},
    "approval": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "approval_pending": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "approval_result": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    "sign_dispute": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["boss", "store_manager"], "schedule_time": None},
    # 店长该处理的
    "shift_status": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["store_manager"], "schedule_time": None},
    "shift_change": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["store_manager", "staff"], "schedule_time": None},
    "sign_remind": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["store_manager", "staff"], "schedule_time": None},
    # 员工该知道的
    "reminder": {"enabled": True, "channel": "all", "push_to_group": True, "target_roles": ["staff"], "schedule_time": None},
}


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

        # 企微应用消息推送（受自建应用开关控制）
        if channel in ("wecom", "all"):
            if await self._is_app_enabled():
                await self._push_wecom_to_users(target_user_ids, title, content)
            else:
                logger.info(f"store {self.store_id} 自建应用推送未开启，跳过企微应用消息")

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

    async def send_app_message(
        self,
        wework_userids: list[str],
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """通过企微自建应用推送消息给指定企微成员（推送给个人，非群）。

        与群机器人不同，自建应用消息直接推送到员工企微「应用消息」入口，
        需要门店配置 corp_id / agent_id / secret。

        安全防御：自动过滤掉不属于本店的 wework_userid，防止跨店推送。
        返回 (是否成功, 错误信息)。
        """
        if not wework_userids:
            return False, "无接收人"
        try:
            # 防御：只推送给本店员工，过滤掉其他门店的 userid，防止跨店推送
            from sqlalchemy import select, and_
            stmt = select(Employee.wework_userid).where(
                and_(
                    Employee.store_id == self.store_id,
                    Employee.wework_userid.in_(wework_userids),
                    Employee.status == "active",
                )
            )
            result = await self.session.execute(stmt)
            safe_userids = [uid for uid in result.scalars().all() if uid]
            if not safe_userids:
                logger.warning(
                    f"store {self.store_id} 自建应用推送被拦截：传入的 userid 均不属于本店"
                )
                return False, "接收人均不属于本店，已拦截跨店推送"
            if len(safe_userids) != len(wework_userids):
                logger.warning(
                    f"store {self.store_id} 自建应用推送过滤：传入 {len(wework_userids)} 人，"
                    f"本店匹配 {len(safe_userids)} 人，已剔除非本店成员"
                )

            token = await get_access_token(self.session, self.store_id)
            url = f"{WECOM_API}/message/send?access_token={token}"
            body = {
                "touser": "|".join(safe_userids),
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
                logger.error(f"自建应用推送失败: {data}")
                return False, data.get("errmsg", "未知错误")
            return True, ""
        except Exception as e:
            logger.error(f"自建应用推送异常: {e}")
            return False, str(e)

    async def _get_agent_id(self) -> int:
        # 优先读环境变量（所有门店共用同一企微主体，统一配置）
        from app.config import get_settings
        settings = get_settings()
        if settings.WECOM_AGENT_ID:
            try:
                return int(settings.WECOM_AGENT_ID)
            except (ValueError, TypeError):
                pass
        # 回退门店表（兼容旧数据 / 单店独立配置）
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

    async def _is_app_enabled(self) -> bool:
        """自建应用推送开关是否开启。

        优先读 StoreSettings.extra_config.wecom_app_enabled；
        未设置时，若企微已由环境变量统一配置则默认开启，否则关闭。
        """
        from sqlalchemy import select
        from app.models.store import StoreSettings
        stmt = select(StoreSettings).where(StoreSettings.store_id == self.store_id)
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()
        extra = settings.extra_config if settings and settings.extra_config else {}
        if "wecom_app_enabled" in extra:
            return bool(extra["wecom_app_enabled"])
        # 未显式设置：已配置则默认开启
        from app.config import get_settings
        cfg = get_settings()
        return bool(cfg.WECOM_CORP_ID and cfg.WECOM_SECRET and cfg.WECOM_AGENT_ID)

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
        settings = await self.repo.get_settings()
        existing_keys = {s.setting_key for s in settings}
        # 补全缺失的默认设置（新门店数据库无记录时，前端也能看到全部推送项）
        for key, default in DEFAULT_SETTINGS.items():
            if key not in existing_keys:
                settings.append(NotificationSetting(
                    store_id=self.store_id,
                    setting_key=key,
                    **default,
                ))
        return settings

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
