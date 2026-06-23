"""打印队列处理定时任务

每30秒检查一次待打印的任务，尝试发送到打印机。
"""
from loguru import logger


async def process_print_queue_job():
    """处理打印队列（每30秒执行一次）

    遍历所有有待打印任务的门店，处理队列。
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, distinct
    from app.models.sys import PrintQueue
    from app.services.printer_service import PrinterService

    # 获取有待打印任务的门店ID
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(distinct(PrintQueue.store_id)).where(
                PrintQueue.status == "pending"
            )
        )
        store_ids = [row[0] for row in result.fetchall()]

    if not store_ids:
        return

    logger.info(f"打印队列处理: 发现 {len(store_ids)} 个门店有待打印任务")

    # 遍历每个门店处理队列
    for store_id in store_ids:
        try:
            async with AsyncSessionLocal() as session:
                service = PrinterService(session)
                result = await service.process_queue(store_id)
                if result["processed"] > 0:
                    logger.info(
                        f"门店 {store_id} 打印队列处理: "
                        f"处理={result['processed']}, "
                        f"成功={result['success']}, "
                        f"失败={result['failed']}"
                    )
        except Exception as e:
            logger.error(f"门店 {store_id} 打印队列处理失败: {e}")
