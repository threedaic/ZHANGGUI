"""
企微群消息推送服务
所有模块统一调用此服务发送异常/提醒到企微群。
"""
import json
from app.utils.http_client import http_client
from loguru import logger


async def send_to_group(webhook_url: str, content: str) -> bool:
    """
    发送 Markdown 消息到企微群机器人。
    webhook_url: 企微群里添加机器人后获得的 Webhook 地址
    返回 True/False 表示是否发送成功
    """
    try:
        payload = json.dumps(
            {"msgtype": "markdown", "markdown": {"content": content}},
            ensure_ascii=False,
        ).encode("utf-8")
        await http_client.post(
            webhook_url,
            content=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        return True
    except Exception as e:
        logger.error(f"企微群消息发送失败: {e}")
        return False


async def notify_alert(store_id: int, title: str, detail: str):
    """
    统一异常告警入口。
    从 StoreSettings 读 wecom_bot_enabled + wecom_webhook_url，老板关闭开关则不推送。
    各业务模块直接调：
        await notify_alert(store_id, "防飞单预警", "B2桌3小时无收款")
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.store import StoreSettings

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoreSettings.wecom_bot_enabled, StoreSettings.wecom_webhook_url)
            .where(StoreSettings.store_id == store_id)
        )
        row = result.one_or_none()

    if not row:
        return

    enabled, webhook_url = row
    if not enabled:
        return  # 老板关闭了群通知开关

    if not webhook_url:
        logger.warning(f"门店 {store_id} 未配置企微群 webhook")
        return

    payload = f"## {title}\n{detail}"
    await send_to_group(webhook_url, payload)
