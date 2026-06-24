"""
存酒管理数据访问层
封装 SQL 查询，返回 ORM 对象。
"""
import uuid
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wine_storage import WineStorage
from app.models.employee import Employee
from app.utils.pagination import PageParams, paginate


class WineRepository:
    """存酒管理 Repository"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def create(self, wine: WineStorage) -> WineStorage:
        self.session.add(wine)
        await self.session.flush()
        return wine

    async def get_by_id(self, wine_id: uuid.UUID) -> WineStorage | None:
        stmt = select(WineStorage).where(
            and_(WineStorage.id == wine_id, WineStorage.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_bottle_label(self, bottle_label: str) -> WineStorage | None:
        """通过瓶身唯一码查找存酒记录，用于取酒流程。"""
        stmt = select(WineStorage).where(
            and_(
                WineStorage.bottle_label == bottle_label,
                WineStorage.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_retriever_info(self, retriever_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
        """批量查询取酒人姓名+工号，避免 N+1"""
        if not retriever_ids:
            return {}
        stmt = select(Employee.id, Employee.name, Employee.employee_code).where(Employee.id.in_(retriever_ids))
        result = await self.session.execute(stmt)
        return {row[0]: {"name": row[1], "employee_code": row[2]} for row in result.all()}

    async def list_wines(
        self,
        status: str | None = None,
        keyword: str | None = None,
        search_type: str | None = None,
        params: PageParams | None = None,
    ) -> tuple[list[WineStorage], int]:
        stmt = select(WineStorage).where(WineStorage.store_id == self.store_id)

        if status:
            stmt = stmt.where(WineStorage.status == status)

        if keyword:
            kw = f"%{keyword}%"
            if search_type == "phone":
                stmt = stmt.where(WineStorage.phone.ilike(kw))
            elif search_type == "customer":
                stmt = stmt.where(WineStorage.customer_name.ilike(kw))
            elif search_type == "wine":
                stmt = stmt.where(WineStorage.wine_name.ilike(kw))
            elif search_type == "bottle":
                stmt = stmt.where(WineStorage.bottle_label.ilike(kw))
            else:
                stmt = stmt.where(
                    or_(
                        WineStorage.customer_name.ilike(kw),
                        WineStorage.phone.ilike(kw),
                        WineStorage.wine_name.ilike(kw),
                        WineStorage.bottle_label.ilike(kw),
                    )
                )

        stmt = stmt.order_by(WineStorage.date_stored.desc())

        # Count
        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Paginate
        if params:
            stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_inventory(self) -> dict[str, int]:
        """获取存酒盘点汇总：总数 / 在存 / 已取"""
        base = select(WineStorage).where(WineStorage.store_id == self.store_id)

        total_stmt = base.with_only_columns(func.count()).order_by(None)
        stored_stmt = base.where(WineStorage.status == "stored").with_only_columns(func.count()).order_by(None)
        retrieved_stmt = base.where(WineStorage.status == "retrieved").with_only_columns(func.count()).order_by(None)

        total = (await self.session.execute(total_stmt)).scalar() or 0
        stored = (await self.session.execute(stored_stmt)).scalar() or 0
        retrieved = (await self.session.execute(retrieved_stmt)).scalar() or 0

        return {"total": total, "stored": stored, "retrieved": retrieved}

    async def get_inventory_items(self, params: PageParams | None = None) -> tuple[list[WineStorage], int]:
        """获取盘点明细（所有在存状态的酒）。"""
        return await self.list_wines(status="stored", params=params)

    async def update(self, wine: WineStorage, **kwargs) -> WineStorage:
        for key, value in kwargs.items():
            if hasattr(wine, key):
                setattr(wine, key, value)
        await self.session.flush()
        return wine

    async def partial_retrieve(
        self, wine: WineStorage, retrieve_ml: int, table_no: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> WineStorage:
        """
        分批取酒：remaining_ml -= retrieve_ml。
        如果全部取完，status 变为 retrieved。
        """
        current = wine.remaining_ml or 0
        new_remaining = current - retrieve_ml
        wine.remaining_ml = max(new_remaining, 0)

        if table_no:
            wine.table_no = table_no

        if wine.remaining_ml == 0:
            from datetime import datetime
            wine.status = "retrieved"
            wine.retrieved_at = datetime.now()
        if user_id is not None:
            wine.retrieved_by = user_id

        await self.session.flush()
        return wine

    async def next_cabinet_no(self) -> str:
        """自动分配柜号：统计在存瓶数，1→2→3→4 循环"""
        stmt = select(func.count()).where(
            and_(WineStorage.store_id == self.store_id, WineStorage.status == "stored")
        )
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return str((count % 4) + 1)
