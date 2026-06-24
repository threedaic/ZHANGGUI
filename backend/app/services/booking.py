"""订桌预约业务逻辑层。"""

import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.booking import TableRepo, BookingRepo
from app.models.employee import Employee
from app.schemas.booking import (
    TableCreate, TableUpdate, TableResponse,
    BookingCreate, BookingUpdate, BookingResponse, BookingStats,
)
from app.utils.exceptions import NotFoundError, ConflictError, ValidationError
from app.utils.pagination import PageParams, PageResult, paginate


async def _get_employee_name(db: AsyncSession, employee_id: uuid.UUID | None) -> str | None:
    """根据员工ID查询姓名。"""
    if not employee_id:
        return None
    result = await db.execute(select(Employee.name).where(Employee.id == employee_id))
    return result.scalar_one_or_none()


class TableService:
    """桌位管理服务。"""

    def __init__(self, db: AsyncSession):
        self.repo = TableRepo(db)
        self.db = db

    async def create(self, store_id: uuid.UUID, data: TableCreate) -> TableResponse:
        try:
            table = await self.repo.create(store_id, data.model_dump())
            return TableResponse.model_validate(table)
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError(f"桌号 {data.table_no} 已存在，每个区域/桌号只能有一个")

    async def get(self, table_id: uuid.UUID, store_id: uuid.UUID) -> TableResponse:
        table = await self.repo.get_by_id(table_id, store_id)
        if not table:
            raise NotFoundError("桌位不存在")
        return TableResponse.model_validate(table)

    async def list(
        self, store_id: uuid.UUID, *, area: str | None = None, params: PageParams | None = None
    ) -> PageResult[TableResponse]:
        items, total = await self.repo.list_by_store(store_id, area=area, params=params)
        return paginate(
            [TableResponse.model_validate(t) for t in items],
            total,
            params or PageParams(),
        )

    async def update(self, table_id: uuid.UUID, store_id: uuid.UUID, data: TableUpdate) -> TableResponse:
        table = await self.repo.get_by_id(table_id, store_id)
        if not table:
            raise NotFoundError("桌位不存在")
        table = await self.repo.update(table, data.model_dump(exclude_none=True))
        return TableResponse.model_validate(table)

    async def delete(self, table_id: uuid.UUID, store_id: uuid.UUID) -> None:
        table = await self.repo.get_by_id(table_id, store_id)
        if not table:
            raise NotFoundError("桌位不存在")
        await self.repo.delete(table)


class BookingService:
    """预约管理服务。"""

    def __init__(self, db: AsyncSession):
        self.booking_repo = BookingRepo(db)
        self.table_repo = TableRepo(db)
        self.db = db

    async def _resolve_table(self, store_id: uuid.UUID, table_id: uuid.UUID | None, guests_count: int) -> tuple[int, str]:
        if table_id:
            table = await self.table_repo.get_by_id(table_id, store_id)
            if not table or table.status != "active":
                raise ValidationError("指定桌位不存在或已停用")
            if guests_count > table.capacity:
                raise ValidationError(f"人数({guests_count})超过桌位容量({table.capacity})")
            return table.id, table.table_no
        else:
            tables, _ = await self.table_repo.list_by_store(store_id, status="active")
            available = [t for t in tables if t.capacity >= guests_count]
            if not available:
                raise ValidationError(f"暂无可用桌位容纳{guests_count}人")
            available.sort(key=lambda t: t.capacity)
            return available[0].id, available[0].table_no

    async def create(self, store_id: uuid.UUID, data: BookingCreate, created_by: uuid.UUID | None = None) -> BookingResponse:
        table_id, table_no = await self._resolve_table(store_id, data.table_id, data.guests_count)

        conflict = await self.booking_repo.find_conflict(store_id, data.date, table_id, data.time_slot)
        if conflict:
            raise ConflictError(f"桌位{table_no}在{data.date} {data.time_slot or '全天'}已被预约")

        create_dict = data.model_dump()
        create_dict["table_id"] = table_id
        create_dict["table_no"] = table_no
        create_dict["source"] = "staff"
        create_dict["created_by"] = created_by

        booking = await self.booking_repo.create(store_id, create_dict)
        resp = BookingResponse.model_validate(booking)
        resp.created_by_name = await _get_employee_name(self.db, booking.created_by)

        table = await self.table_repo.get_by_id(table_id, store_id)
        if table:
            resp.table_area = table.area
        return resp

    async def get(self, booking_id: uuid.UUID, store_id: uuid.UUID) -> BookingResponse:
        booking = await self.booking_repo.get_by_id(booking_id, store_id)
        if not booking:
            raise NotFoundError("预约不存在")
        resp = BookingResponse.model_validate(booking)
        resp.created_by_name = await _get_employee_name(self.db, booking.created_by)
        if booking.table_id:
            table = await self.table_repo.get_by_id(booking.table_id, store_id)
            if table:
                resp.table_area = table.area
        return resp

    async def list(
        self, store_id: uuid.UUID, *, date: str | None = None, status: str | None = None,
        params: PageParams | None = None,
    ) -> PageResult[BookingResponse]:
        items, total = await self.booking_repo.list_by_date(store_id, date=date, status=status, params=params)

        # 批量收集 created_by 和 table_id，避免循环内 N+1 查询
        employee_ids = list({b.created_by for b in items if b.created_by})
        table_ids = list({b.table_id for b in items if b.table_id})

        name_map = (
            await self.table_repo.get_employee_name_map(employee_ids)
            if employee_ids else {}
        )
        tables = (
            await self.table_repo.get_by_ids(table_ids, store_id)
            if table_ids else []
        )
        table_map = {t.id: t for t in tables}

        responses = []
        for b in items:
            resp = BookingResponse.model_validate(b)
            resp.created_by_name = name_map.get(b.created_by) if b.created_by else None
            if b.table_id:
                table = table_map.get(b.table_id)
                if table:
                    resp.table_area = table.area
            responses.append(resp)
        return paginate(responses, total, params or PageParams())

    async def update(self, booking_id: uuid.UUID, store_id: uuid.UUID, data: BookingUpdate) -> BookingResponse:
        booking = await self.booking_repo.get_by_id(booking_id, store_id)
        if not booking:
            raise NotFoundError("预约不存在")

        update_dict = data.model_dump(exclude_none=True)

        if "table_id" in update_dict and update_dict["table_id"] is not None:
            new_table_id = update_dict["table_id"]
            table = await self.table_repo.get_by_id(new_table_id, store_id)
            if not table or table.status != "active":
                raise ValidationError("指定桌位不存在或已停用")
            update_dict["table_no"] = table.table_no

            guests = update_dict.get("guests_count", booking.guests_count)
            if guests > table.capacity:
                raise ValidationError(f"人数({guests})超过桌位容量({table.capacity})")

        booking = await self.booking_repo.update(booking, update_dict)
        resp = BookingResponse.model_validate(booking)
        if booking.table_id:
            table = await self.table_repo.get_by_id(booking.table_id, store_id)
            if table:
                resp.table_area = table.area
        return resp

    async def cancel(self, booking_id: uuid.UUID, store_id: uuid.UUID) -> BookingResponse:
        booking = await self.booking_repo.get_by_id(booking_id, store_id)
        if not booking:
            raise NotFoundError("预约不存在")
        booking = await self.booking_repo.update(booking, {"status": "cancelled"})
        return BookingResponse.model_validate(booking)

    async def stats(self, store_id: uuid.UUID, date: str) -> BookingStats:
        total = await self.table_repo.count_active(store_id)
        booked = await self.booking_repo.count_by_date_status(store_id, date, "confirmed")
        return BookingStats(
            date=date, total_tables=total, booked=booked, free=total - booked,
        )
