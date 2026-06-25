"""订桌预约数据访问层。

所有查询通过 store_id 过滤（RLS），boss 角色传入 store_id=None 查全部。
"""
import uuid
from datetime import date as date_type, time as time_type

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.booking import Booking, Table
from app.models.employee import Employee
from app.utils.pagination import PageParams, paginate_query


class TableRepo:
    """桌位 CRUD。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, store_id: uuid.UUID, data: dict) -> Table:
        table = Table(store_id=store_id, **data)
        self.session.add(table)
        await self.session.commit()
        await self.session.refresh(table)
        return table

    async def get_by_id(self, table_id: uuid.UUID, store_id: uuid.UUID | None = None) -> Table | None:
        stmt = select(Table).where(Table.id == table_id)
        if store_id is not None:
            stmt = stmt.where(Table.store_id == store_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(
        self, table_ids: list[uuid.UUID], store_id: uuid.UUID | None = None
    ) -> list[Table]:
        """批量按 ID 查询桌位，避免 N+1"""
        if not table_ids:
            return []
        stmt = select(Table).where(Table.id.in_(table_ids))
        if store_id is not None:
            stmt = stmt.where(Table.store_id == store_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_employee_name_map(
        self, employee_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """批量获取员工姓名，返回 {employee_id: name}"""
        if not employee_ids:
            return {}
        stmt = select(Employee.id, Employee.name).where(Employee.id.in_(employee_ids))
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def list_by_store(
        self,
        store_id: uuid.UUID,
        *,
        area: str | None = None,
        status: str | None = None,
        params: PageParams | None = None,
    ) -> tuple[list[Table], int]:
        base = select(Table).where(Table.store_id == store_id)
        if area:
            base = base.where(Table.area == area)
        if status:
            base = base.where(Table.status == status)
        base = base.order_by(Table.area, Table.table_no)

        if params:
            items, total = await paginate_query(self.session, base, params)
        else:
            result = await self.session.execute(base)
            items = list(result.scalars().all())
            total = len(items)
        return items, total

    async def update(self, table: Table, data: dict) -> Table:
        for k, v in data.items():
            if v is not None:
                setattr(table, k, v)
        await self.session.commit()
        await self.session.refresh(table)
        return table

    async def delete(self, table: Table) -> None:
        await self.session.delete(table)
        await self.session.commit()

    async def count_active(self, store_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Table.store_id == store_id,
            Table.status == "active",
        )
        return (await self.session.execute(stmt)).scalar_one()


class BookingRepo:
    """预约 CRUD。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, store_id: uuid.UUID, data: dict) -> Booking:
        booking = Booking(store_id=store_id, **data)
        self.session.add(booking)
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def get_by_id(
        self, booking_id: uuid.UUID, store_id: uuid.UUID | None = None
    ) -> Booking | None:
        stmt = select(Booking).where(Booking.id == booking_id)
        if store_id is not None:
            stmt = stmt.where(Booking.store_id == store_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_date(
        self,
        store_id: uuid.UUID,
        *,
        date: str | None = None,
        status: str | None = None,
        params: PageParams | None = None,
    ) -> tuple[list[Booking], int]:
        base = select(Booking).where(Booking.store_id == store_id)
        if date:
            date_obj = date_type.fromisoformat(date) if isinstance(date, str) else date
            base = base.where(Booking.date == date_obj)
        if status:
            base = base.where(Booking.status == status)
        base = base.order_by(Booking.date.desc(), Booking.start_time.asc())

        if params:
            items, total = await paginate_query(self.session, base, params)
        else:
            result = await self.session.execute(base)
            items = list(result.scalars().all())
            total = len(items)
        return items, total

    async def update(self, booking: Booking, data: dict) -> Booking:
        for k, v in data.items():
            if v is not None:
                setattr(booking, k, v)
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def delete(self, booking: Booking) -> None:
        await self.session.delete(booking)
        await self.session.commit()

    async def count_by_date_status(
        self, store_id: uuid.UUID, date: str, status: str = "confirmed"
    ) -> int:
        date_obj = date_type.fromisoformat(date) if isinstance(date, str) else date
        stmt = select(func.count()).where(
            Booking.store_id == store_id,
            Booking.date == date_obj,
            Booking.status == status,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def find_conflict(
        self, store_id: uuid.UUID, date: str, table_id: uuid.UUID, time_slot: str | None = None
    ) -> Booking | None:
        """查找指定桌位在指定日期的冲突预约。"""
        date_obj = date_type.fromisoformat(date) if isinstance(date, str) else date
        stmt = select(Booking).where(
            Booking.store_id == store_id,
            Booking.date == date_obj,
            Booking.table_id == table_id,
            Booking.status == "confirmed",
        )
        if time_slot:
            # 冲突条件：已有预约(同时段 或 全天) → 都视为冲突
            start_time_str = time_slot.split("-")[0] if "-" in time_slot else time_slot
            start_time_obj = time_type.fromisoformat(start_time_str.strip())
            stmt = stmt.where(
                or_(
                    Booking.start_time == start_time_obj,
                    Booking.start_time.is_(None),
                )
            )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()
