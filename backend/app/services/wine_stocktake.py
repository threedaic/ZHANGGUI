"""
存酒盘点单业务逻辑层
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from loguru import logger

from app.repositories.wine_stocktake import WineStocktakeRepository
from app.repositories.wine import WineRepository
from app.models.wine_stocktake import WineStocktakeItem
from app.utils.exceptions import NotFoundError, ValidationError


async def generate_monthly_stocktake(
    session: AsyncSession, store_id: uuid.UUID, period: str | None = None,
    assigned_to: str | None = None,
) -> int:
    """生成月度盘点单：拉取当前在库酒 → 创建盘点单 + 明细。

    Returns: 盘点单 ID
    """
    if period is None:
        period = datetime.now().strftime("%Y-%m")

    repo = WineStocktakeRepository(session, store_id)

    # 同月已有盘点单则跳过
    existing = await repo.get_by_period(period)
    if existing:
        logger.info(f"门店 {store_id} {period} 盘点单已存在 (id={existing.id})，跳过生成")
        return existing.id

    # 拉取当前在库酒
    wines = await repo.get_current_stored_wines()
    if not wines:
        logger.info(f"门店 {store_id} {period} 无在库酒，跳过生成盘点单")
        return 0

    # 创建盘点单
    stocktake = await repo.create_stocktake(period=period, assigned_to=assigned_to)

    # 批量创建明细
    items = [
        WineStocktakeItem(
            stocktake_id=stocktake.id,
            wine_id=w.id,
            bottle_label=w.bottle_label or f"NO-LABEL-{w.id}",
            customer_name=w.customer_name,
            phone=w.phone,
            wine_name=w.wine_name,
            expected_ml=w.remaining_ml,
            check_status="pending",
        )
        for w in wines
    ]
    await repo.add_items_batch(items)

    # 更新应盘数量
    stocktake.total_count = len(items)
    await session.flush()

    logger.info(f"门店 {store_id} {period} 盘点单已生成: id={stocktake.id}, 共 {len(items)} 瓶")
    return stocktake.id


async def scan_bottle(
    session: AsyncSession, store_id: uuid.UUID, stocktake_id: uuid.UUID,
    bottle_label: str, actual_ml: int | None, user_id: uuid.UUID | None,
) -> dict:
    """扫码核对单瓶酒。

    逻辑：
    1. 在盘点单明细中查找该瓶身码
    2. 找到 → 标记 matched/mismatch（量不符）
    3. 未找到 → 查 wine_storage 表，如果在库则标记 extra（多出），否则报错
    4. 更新盘点单统计数
    """
    repo = WineStocktakeRepository(session, store_id)
    wine_repo = WineRepository(session, store_id)

    stocktake = await repo.get_by_id(stocktake_id)
    if not stocktake:
        raise NotFoundError("盘点单不存在")
    if stocktake.status == "completed":
        raise ValidationError("盘点单已完成，无法继续核对")

    # 首次扫码 → 标记为进行中
    if stocktake.status == "pending":
        await repo.mark_started(stocktake_id)

    # 在盘点单明细中查找
    item = await repo.find_item_by_label(stocktake_id, bottle_label)

    if item:
        # 已核对过 → 幂等返回
        if item.check_status != "pending":
            await repo.update_stocktake_counts(stocktake_id)
            return {
                "bottle_label": bottle_label,
                "check_status": item.check_status,
                "wine_name": item.wine_name,
                "customer_name": item.customer_name,
                "expected_ml": item.expected_ml,
                "actual_ml": item.actual_ml,
                "message": "该瓶已核对过",
            }

        # 判断量是否匹配
        if actual_ml is not None and item.expected_ml is not None and actual_ml != item.expected_ml:
            check_status = "mismatch"
            message = f"量不符：应剩 {item.expected_ml}ml，实际 {actual_ml}ml"
        else:
            check_status = "matched"
            message = "匹配成功"

        await repo.update_item_check(item.id, check_status, actual_ml, user_id)
        await repo.update_stocktake_counts(stocktake_id)

        return {
            "bottle_label": bottle_label,
            "check_status": check_status,
            "wine_name": item.wine_name,
            "customer_name": item.customer_name,
            "expected_ml": item.expected_ml,
            "actual_ml": actual_ml,
            "message": message,
        }

    # 盘点单中没找到 → 查 wine_storage 看是否在库
    wine = await wine_repo.get_by_bottle_label(bottle_label)
    if wine and wine.status == "stored":
        # 多出的酒：在库但不在盘点单上
        # 创建一条 extra 明细
        extra_item = WineStocktakeItem(
            stocktake_id=stocktake_id,
            wine_id=wine.id,
            bottle_label=bottle_label,
            customer_name=wine.customer_name,
            phone=wine.phone,
            wine_name=wine.wine_name,
            expected_ml=None,  # 盘点单上没有
            actual_ml=actual_ml,
            check_status="matched",  # 标记为匹配（实物在库）
            checked_by=user_id,
        )
        await repo.add_item(extra_item)
        stocktake.extra_count = (stocktake.extra_count or 0) + 1
        stocktake.total_count = (stocktake.total_count or 0) + 1
        await repo.update_stocktake_counts(stocktake_id)

        return {
            "bottle_label": bottle_label,
            "check_status": "extra",
            "wine_name": wine.wine_name,
            "customer_name": wine.customer_name,
            "expected_ml": None,
            "actual_ml": actual_ml,
            "message": "该瓶不在盘点单上，但实物在库（存酒后新增）",
        }

    # 既不在盘点单也不在库 → 未知瓶身码
    raise NotFoundError(f"瓶身码 {bottle_label} 不在库中，请检查是否扫错")


async def complete_stocktake(
    session: AsyncSession, store_id: uuid.UUID, stocktake_id: uuid.UUID, notes: str | None,
) -> dict:
    """完成盘点：将未核对的明细标记为 missing"""
    repo = WineStocktakeRepository(session, store_id)

    stocktake = await repo.get_by_id(stocktake_id)
    if not stocktake:
        raise NotFoundError("盘点单不存在")
    if stocktake.status == "completed":
        raise ValidationError("盘点单已完成")

    # 将所有 pending 的明细标记为 missing
    items, _ = await repo.list_items(stocktake_id, check_status="pending")
    from datetime import datetime as dt
    now = dt.now().isoformat()
    for item in items:
        item.check_status = "missing"
        item.checked_at = now

    await session.flush()
    await repo.update_stocktake_counts(stocktake_id)
    await repo.mark_completed(stocktake_id, notes)

    logger.info(f"盘点单 {stocktake_id} 已完成: 应盘 {stocktake.total_count}, 已核 {stocktake.checked_count}, 匹配 {stocktake.matched_count}, 缺失 {stocktake.missing_count}")
    return {
        "id": stocktake_id,
        "status": "completed",
        "total_count": stocktake.total_count,
        "checked_count": stocktake.checked_count,
        "matched_count": stocktake.matched_count,
        "missing_count": stocktake.missing_count,
        "extra_count": stocktake.extra_count,
    }
