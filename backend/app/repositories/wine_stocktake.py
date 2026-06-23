"""
存酒盘点单数据访问层
"""
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wine_stocktake import WineStocktake, WineStocktakeItem
from app.models.wine_storage import WineStorage
from app.utils.pagination import PageParams, PageResult
from datetime import datetime


class WineStocktakeRepository:
    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    async def create_stocktake(self, period: str, assigned_to: str | None = None) -> WineStocktake:
        """创建盘点单主记录"""
        stocktake = WineStocktake(
            store_id=self.store_id,
            period=period,
            status="pending",
            assigned_to=assigned_to,
            total_count=0,
            checked_count=0,
            matched_count=0,
            missing_count=0,
            extra_count=0,
        )
        self.session.add(stocktake)
        await self.session.flush()
        return stocktake

    async def add_item(self, item: WineStocktakeItem) -> WineStocktakeItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def add_items_batch(self, items: list[WineStocktakeItem]) -> int:
        """批量添加明细"""
        self.session.add_all(items)
        await self.session.flush()
        return len(items)

    async def get_by_id(self, stocktake_id: int) -> WineStocktake | None:
        stmt = select(WineStocktake).where(
            and_(WineStocktake.id == stocktake_id, WineStocktake.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_period(self, period: str) -> WineStocktake | None:
        stmt = select(WineStocktake).where(
            and_(WineStocktake.period == period, WineStocktake.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_stocktakes(
        self, status: str | None = None, params: PageParams | None = None,
    ) -> tuple[list[WineStocktake], int]:
        stmt = select(WineStocktake).where(WineStocktake.store_id == self.store_id)
        if status:
            stmt = stmt.where(WineStocktake.status == status)
        stmt = stmt.order_by(WineStocktake.period.desc())

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if params:
            stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_items(
        self, stocktake_id: int, check_status: str | None = None,
        params: PageParams | None = None,
    ) -> tuple[list[WineStocktakeItem], int]:
        stmt = select(WineStocktakeItem).where(WineStocktakeItem.stocktake_id == stocktake_id)
        if check_status:
            stmt = stmt.where(WineStocktakeItem.check_status == check_status)
        stmt = stmt.order_by(WineStocktakeItem.id)

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if params:
            stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def find_item_by_label(self, stocktake_id: int, bottle_label: str) -> WineStocktakeItem | None:
        """在盘点单中按瓶身码查找明细"""
        stmt = select(WineStocktakeItem).where(
            and_(
                WineStocktakeItem.stocktake_id == stocktake_id,
                WineStocktakeItem.bottle_label == bottle_label,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_item_check(
        self, item_id: int, check_status: str, actual_ml: int | None, user_id: int | None,
    ) -> None:
        """更新明细核对状态"""
        now = datetime.now()
        stmt = (
            update(WineStocktakeItem)
            .where(WineStocktakeItem.id == item_id)
            .values(
                check_status=check_status,
                actual_ml=actual_ml,
                checked_at=now,
                checked_by=user_id,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_stocktake_counts(self, stocktake_id: int) -> WineStocktake:
        """重新统计盘点单的核对数量"""
        base = select(WineStocktakeItem).where(WineStocktakeItem.stocktake_id == stocktake_id)

        checked = (
            await self.session.execute(
                base.where(WineStocktakeItem.check_status != "pending").with_only_columns(func.count()).order_by(None)
            )
        ).scalar() or 0

        matched = (
            await self.session.execute(
                base.where(WineStocktakeItem.check_status == "matched").with_only_columns(func.count()).order_by(None)
            )
        ).scalar() or 0

        missing = (
            await self.session.execute(
                base.where(WineStocktakeItem.check_status == "missing").with_only_columns(func.count()).order_by(None)
            )
        ).scalar() or 0

        mismatch = (
            await self.session.execute(
                base.where(WineStocktakeItem.check_status == "mismatch").with_only_columns(func.count()).order_by(None)
            )
        ).scalar() or 0

        stocktake = await self.get_by_id(stocktake_id)
        if stocktake:
            stocktake.checked_count = checked
            stocktake.matched_count = matched
            stocktake.missing_count = missing + mismatch
            await self.session.flush()
        return stocktake

    async def mark_started(self, stocktake_id: int) -> None:
        stmt = (
            update(WineStocktake)
            .where(WineStocktake.id == stocktake_id)
            .values(status="in_progress", started_at=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_completed(self, stocktake_id: int, notes: str | None = None) -> None:
        values = {
            "status": "completed",
            "completed_at": datetime.now(),
        }
        if notes is not None:
            values["notes"] = notes
        stmt = update(WineStocktake).where(WineStocktake.id == stocktake_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_current_stored_wines(self) -> list[WineStorage]:
        """获取当前在库的所有存酒记录（用于生成盘点单）"""
        stmt = (
            select(WineStorage)
            .where(
                and_(
                    WineStorage.store_id == self.store_id,
                    WineStorage.status == "stored",
                )
            )
            .order_by(WineStorage.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
