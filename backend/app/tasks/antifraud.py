"""
防飞单定时任务
每天凌晨 3:00 自动扫描前一天的数据。
注册于 scheduler.py 中:
    scheduler.add_job(run_daily_antifraud_scan, 'cron', hour=3, minute=0)
"""
from datetime import date, timedelta
from loguru import logger
from app.database import AsyncSessionLocal
from app.services.antifraud import AntiFraudService
from app.utils.http_client import http_client


async def run_daily_antifraud_scan():
    """
    每日防飞单扫描。
    遍历所有活跃门店，扫描昨日所有开台会话。
    异常会话 >50 分自动推送企微群。
    """
    scan_date = (date.today() - timedelta(days=1)).isoformat()
    logger.info(f"[防飞单定时任务] 开始扫描 {scan_date}")

    # 获取所有活跃门店
    from app.models.store import Store
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Store.store_id, Store.name).where(Store.status == "active")
        )
        stores = [(row[0], row[1]) for row in result.all()]

    if not stores:
        logger.warning("[防飞单定时任务] 无活跃门店，跳过")
        return

    total_anomalies = 0
    for store_id, store_name in stores:
        try:
            async with AsyncSessionLocal() as session:
                service = AntiFraudService(session, store_id)
                result = await service.scan_daily(scan_date, push_alert=True)
                anomalies = result.get("anomaly_count", 0)
                total_anomalies += anomalies
                logger.info(
                    f"[防飞单] {store_name}(ID:{store_id}) {scan_date}: "
                    f"{result['total_sessions']} 桌, {anomalies} 异常 "
                    f"(高危 {result['high_risk_count']}, 严重 {result['critical_count']})"
                )
        except Exception as e:
            logger.error(f"[防飞单] {store_name}(ID:{store_id}) 扫描失败: {e}")

    logger.info(f"[防飞单定时任务] 完成, {len(stores)} 门店, 共 {total_anomalies} 异常")
