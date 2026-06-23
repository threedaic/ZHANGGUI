"""
存酒盘点定时任务
每月1号 02:30 自动生成盘点单并通知会计。
"""
from datetime import datetime
from app.database import AsyncSessionLocal
from app.services.wine_stocktake import generate_monthly_stocktake
from app.services.notification_service import NotificationService
from loguru import logger


async def monthly_wine_stocktake_job() -> None:
    """每月1号 02:30 自动生成存酒盘点单。

    流程：
    1. 遍历所有启用的门店
    2. 为每个门店生成当月盘点单
    3. 通过企微群通知会计/店长
    """
    from app.models.store import Store
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Store).where(Store.status == "active")
            )
            stores = result.scalars().all()

            for store in stores:
                try:
                    period = datetime.now().strftime("%Y-%m")
                    stocktake_id = await generate_monthly_stocktake(
                        session=session, store_id=store.id, period=period,
                    )
                    await session.commit()

                    if stocktake_id and stocktake_id > 0:
                        logger.info(f"门店 {store.name} {period} 盘点单已生成: id={stocktake_id}")

                        # 统一推送通知
                        notif = NotificationService(session, store.id)
                        await notif.send_alert(
                            "wine_stocktake_alert",
                            "月度存酒盘点单已生成",
                            (
                                f"**{period} 月度存酒盘点单已生成**\n"
                                f"门店：{store.name}\n"
                                f"盘点单号：#{stocktake_id}\n"
                                f"请会计尽快扫码核对库存\n"
                                f"链接：https://zhanggui.crushserver.cloud/management/wine-stocktake/{stocktake_id}"
                            ),
                        )
                    else:
                        logger.info(f"门店 {store.name} {period} 无在库酒，跳过盘点单生成")

                except Exception as e:
                    logger.error(f"门店 {store.name} 盘点单生成失败: {e}")
                    await session.rollback()

        except Exception as e:
            logger.error(f"月度存酒盘点任务失败: {e}")
