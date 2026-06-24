"""
排班数据访问层

封装 SQL 查询，返回 ORM 对象。
所有查询强制带上 store_id（RLS 应用层兜底）。
"""
import uuid
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schedule import Schedule, ScheduleSnapshot, ScheduleRule, ShiftSwapRequest
from app.models.employee import Employee


class ScheduleRepository:
    """排班相关数据访问。每个请求实例化一次，绑定 store_id。"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # -- Schedule CRUD --

    async def get_by_id(self, schedule_id: uuid.UUID) -> Schedule | None:
        result = await self.session.execute(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.store_id == self.store_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_employee_date(
        self, employee_id: uuid.UUID, schedule_date: date
    ) -> Schedule | None:
        result = await self.session.execute(
            select(Schedule).where(
                Schedule.store_id == self.store_id,
                Schedule.employee_id == employee_id,
                Schedule.date == schedule_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_week(
        self, start_date: date, end_date: date
    ) -> list[Schedule]:
        result = await self.session.execute(
            select(Schedule)
            .where(
                Schedule.store_id == self.store_id,
                Schedule.date >= start_date,
                Schedule.date <= end_date,
            )
            .order_by(Schedule.date, Schedule.employee_id)
        )
        return list(result.scalars().all())

    async def create(self, schedule: Schedule) -> Schedule:
        self.session.add(schedule)
        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def update(self, schedule: Schedule, **kwargs) -> Schedule:
        for key, value in kwargs.items():
            if value is not None:
                setattr(schedule, key, value)
        schedule.version = (schedule.version or 0) + 1
        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def delete(self, schedule: Schedule) -> None:
        await self.session.delete(schedule)
        await self.session.flush()

    # -- 编制统计 --

    async def count_by_shift_date(
        self, schedule_date: date, shift_type: str
    ) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Schedule.store_id == self.store_id,
                Schedule.date == schedule_date,
                Schedule.shift_type == shift_type,
            )
        )
        return result.scalar() or 0

    async def get_headcount_stats(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        result = await self.session.execute(
            select(
                Schedule.date,
                func.count().label("total"),
                func.count()
                .filter(Schedule.shift_type == "白班")
                .label("day_count"),
                func.count()
                .filter(Schedule.shift_type == "晚班")
                .label("night_count"),
                func.count()
                .filter(Schedule.shift_type == "休息")
                .label("rest_count"),
            )
            .where(
                Schedule.store_id == self.store_id,
                Schedule.date >= start_date,
                Schedule.date <= end_date,
            )
            .group_by(Schedule.date)
            .order_by(Schedule.date)
        )
        rows = result.all()
        return [
            {
                "date": row.date,
                "total_scheduled": row.total,
                "day_count": row.day_count or 0,
                "night_count": row.night_count or 0,
                "rest_count": row.rest_count or 0,
            }
            for row in rows
        ]

    # -- 员工 -- 

    async def get_active_employees(self) -> list[Employee]:
        result = await self.session.execute(
            select(Employee).where(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            ).order_by(Employee.id)
        )
        return list(result.scalars().all())

    async def get_by_employee_week(
        self, employee_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[Schedule]:
        """获取指定员工在日期范围内的排班。用于员工个人视图。"""
        result = await self.session.execute(
            select(Schedule)
            .where(
                Schedule.store_id == self.store_id,
                Schedule.employee_id == employee_id,
                Schedule.date >= start_date,
                Schedule.date <= end_date,
            )
            .order_by(Schedule.date)
        )
        return list(result.scalars().all())
