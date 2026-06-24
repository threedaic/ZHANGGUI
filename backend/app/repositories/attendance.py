"""
考勤与排班一体化数据访问层
"""
import uuid
from datetime import date
from sqlalchemy import select, func, and_, update, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.attendance import AttendanceRecord, ShiftConfig
from app.models.employee import Employee
from app.utils.pagination import PageParams, paginate


class AttendanceRepository:
    """考勤 Repository"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ==================== 打卡记录 CRUD ====================

    async def get_records(
        self,
        employee_id: uuid.UUID | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[AttendanceRecord], int]:
        """查询打卡记录列表，支持分页"""
        stmt = select(AttendanceRecord).where(AttendanceRecord.store_id == self.store_id)

        if employee_id:
            stmt = stmt.where(AttendanceRecord.employee_id == employee_id)
        if date_from:
            stmt = stmt.where(AttendanceRecord.date >= date_from)
        if date_to:
            stmt = stmt.where(AttendanceRecord.date <= date_to)
        if status:
            stmt = stmt.where(AttendanceRecord.status == status)

        stmt = stmt.order_by(AttendanceRecord.date.desc(), AttendanceRecord.employee_id)

        # Count
        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_record_by_id(self, record_id: uuid.UUID) -> AttendanceRecord | None:
        stmt = select(AttendanceRecord).where(
            and_(AttendanceRecord.id == record_id, AttendanceRecord.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_record_by_employee_date(
        self, employee_id: uuid.UUID, date_str: str | date
    ) -> AttendanceRecord | None:
        # 确保 date 比较使用 Python date 对象，避免 PG date vs varchar 报错
        if isinstance(date_str, str):
            date_str = date.fromisoformat(date_str)
        stmt = select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == date_str,
                AttendanceRecord.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_records_by_date_range(
        self,
        date_from: date,
        date_to: date,
        employee_id: uuid.UUID | None = None,
    ) -> list[AttendanceRecord]:
        """按日期范围查询考勤记录，用于排班表"""
        stmt = (
            select(AttendanceRecord)
            .where(
                and_(
                    AttendanceRecord.store_id == self.store_id,
                    AttendanceRecord.date >= date_from,
                    AttendanceRecord.date <= date_to,
                )
            )
            .order_by(AttendanceRecord.date, AttendanceRecord.employee_id)
        )
        if employee_id:
            stmt = stmt.where(AttendanceRecord.employee_id == employee_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_today_records(self, today: str | date) -> list[AttendanceRecord]:
        """获取今日所有员工打卡记录"""
        # 确保 date 比较使用 Python date 对象，避免 PG date vs varchar 报错
        if isinstance(today, str):
            today = date.fromisoformat(today)
        stmt = (
            select(AttendanceRecord)
            .where(
                and_(
                    AttendanceRecord.store_id == self.store_id,
                    AttendanceRecord.date == today,
                )
            )
            .order_by(AttendanceRecord.employee_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_record(self, record: AttendanceRecord) -> AttendanceRecord:
        """存在则更新，不存在则插入"""
        # 兼容 date 列为 DATE 类型但传入 str 的情况，显式转为 Python date
        from datetime import date as date_cls
        if isinstance(record.date, str):
            record.date = date_cls.fromisoformat(record.date)
        record_date = record.date

        existing = await self.session.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.employee_id == record.employee_id,
                    AttendanceRecord.date == record_date,
                )
            )
        )
        existing_obj = existing.scalar_one_or_none()
        if existing_obj:
            # 仅更新非空字段，避免后续同步覆盖已有数据
            if record.clock_in is not None:
                existing_obj.clock_in = record.clock_in
            if record.clock_out is not None:
                existing_obj.clock_out = record.clock_out
            if record.status is not None:
                existing_obj.status = record.status
            if record.late_minutes is not None:
                existing_obj.late_minutes = record.late_minutes
            if record.early_minutes is not None:
                existing_obj.early_minutes = record.early_minutes
            if record.source is not None:
                existing_obj.source = record.source
            if record.note is not None:
                existing_obj.note = record.note
            if record.scheduled_shift is not None:
                existing_obj.scheduled_shift = record.scheduled_shift
            if record.shift_start_time is not None:
                existing_obj.shift_start_time = record.shift_start_time
            if record.shift_end_time is not None:
                existing_obj.shift_end_time = record.shift_end_time
            if record.is_overnight is not None:
                existing_obj.is_overnight = record.is_overnight
            target = existing_obj
        else:
            self.session.add(record)
            target = record
        await self.session.flush()
        return target

    async def upsert_schedule(
        self,
        employee_id: uuid.UUID,
        record_date: date,
        scheduled_shift: str,
        shift_start_time: str | None,
        shift_end_time: str | None,
        is_overnight: bool,
    ) -> AttendanceRecord:
        """ Upsert 排班信息，保留已有打卡数据 """
        existing = await self.get_record_by_employee_date(employee_id, record_date)
        if existing:
            existing.scheduled_shift = scheduled_shift
            existing.shift_start_time = shift_start_time
            existing.shift_end_time = shift_end_time
            existing.is_overnight = is_overnight
            await self.session.flush()
            return existing

        new_record = AttendanceRecord(
            store_id=self.store_id,
            employee_id=employee_id,
            date=record_date,
            scheduled_shift=scheduled_shift,
            shift_start_time=shift_start_time,
            shift_end_time=shift_end_time,
            is_overnight=is_overnight,
            status="unknown",
        )
        self.session.add(new_record)
        await self.session.flush()
        return new_record

    async def update_record(self, record_id: uuid.UUID, **kwargs) -> AttendanceRecord | None:
        record = await self.get_record_by_id(record_id)
        if not record:
            return None
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        await self.session.flush()
        return record

    # ==================== 月度汇总 ====================

    async def get_monthly_summary(
        self, period: str, employee_id: uuid.UUID | None = None
    ) -> list[dict]:
        """
        按月聚合考勤数据。
        period: 2026-06
        返回 [{employee_id, employee_name, employee_role, ...}]
        """
        year, month = int(period[:4]), int(period[5:7])
        import calendar
        from datetime import date as date_type
        last_day = calendar.monthrange(year, month)[1]
        date_from = date_type(year, month, 1)
        date_to = date_type(year, month, last_day)

        stmt = (
            select(
                AttendanceRecord.employee_id,
                func.count().label("total_records"),
                func.sum(
                    case((AttendanceRecord.status == "present", 1), else_=0)
                ).label("present_days"),
                func.sum(
                    case((AttendanceRecord.status == "late", 1), else_=0)
                ).label("late_days"),
                func.sum(
                    case((AttendanceRecord.status == "early", 1), else_=0)
                ).label("early_days"),
                func.sum(
                    case((AttendanceRecord.status == "leave", 1), else_=0)
                ).label("leave_days"),
                func.sum(
                    case((AttendanceRecord.status == "absent", 1), else_=0)
                ).label("absent_days"),
                func.sum(AttendanceRecord.late_minutes).label("total_late_minutes"),
                func.sum(
                    case((AttendanceRecord.source == "makeup", 1), else_=0)
                ).label("makeup_count"),
            )
            .where(
                and_(
                    AttendanceRecord.store_id == self.store_id,
                    AttendanceRecord.date >= date_from,
                    AttendanceRecord.date <= date_to,
                )
            )
            .group_by(AttendanceRecord.employee_id)
            .order_by(AttendanceRecord.employee_id)
        )

        if employee_id:
            stmt = stmt.where(AttendanceRecord.employee_id == employee_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        emp_info = await self._get_employee_info([row.employee_id for row in rows])

        return [
            {
                "employee_id": row.employee_id,
                "employee_name": emp_info.get(row.employee_id, {}).get("name", ""),
                "employee_role": emp_info.get(row.employee_id, {}).get("role", ""),
                "total_days": row.total_records or 0,
                "present_days": row.present_days or 0,
                "late_days": row.late_days or 0,
                "early_days": row.early_days or 0,
                "leave_days": row.leave_days or 0,
                "absent_days": row.absent_days or 0,
                "makeup_count": row.makeup_count or 0,
                "total_late_minutes": row.total_late_minutes or 0,
            }
            for row in rows
        ]

    async def get_monthly_makeup_count(self, employee_id: uuid.UUID, period: str) -> int:
        """查询某员工当月补卡次数"""
        year, month = int(period[:4]), int(period[5:7])
        import calendar
        from datetime import date as date_type
        last_day = calendar.monthrange(year, month)[1]
        date_from = date_type(year, month, 1)
        date_to = date_type(year, month, last_day)

        stmt = (
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.store_id == self.store_id,
                    AttendanceRecord.source == "makeup",
                    AttendanceRecord.date >= date_from,
                    AttendanceRecord.date <= date_to,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ==================== 班次配置 ====================

    async def get_shift_configs(self, active_only: bool = False) -> list[ShiftConfig]:
        stmt = select(ShiftConfig).where(ShiftConfig.store_id == self.store_id)
        if active_only:
            stmt = stmt.where(ShiftConfig.is_active.is_(True))
        stmt = stmt.order_by(ShiftConfig.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_shift_config_by_code(self, shift_code: str) -> ShiftConfig | None:
        stmt = select(ShiftConfig).where(
            and_(
                ShiftConfig.store_id == self.store_id,
                ShiftConfig.shift_code == shift_code,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_shift_config(self, config: ShiftConfig) -> ShiftConfig:
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def delete_shift_config(self, config: ShiftConfig) -> None:
        await self.session.delete(config)
        await self.session.flush()

    # ==================== 员工信息 ====================

    async def _get_employee_info(self, employee_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
        """批量获取员工信息"""
        if not employee_ids:
            return {}
        stmt = select(Employee).where(
            and_(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return {
            e.id: {"name": e.name, "role": e.role, "base_salary": e.base_salary}
            for e in result.scalars().all()
        }

    async def get_active_employees(self, roles: list[str] | None = None) -> list[dict]:
        """获取门店在职员工列表。
        
        Args:
            roles: 可选的角色过滤，如 ['staff', 'store_manager'] 仅返回排班人员
        """
        stmt = select(Employee).where(
            and_(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            )
        )
        if roles:
            stmt = stmt.where(Employee.role.in_(roles))
        result = await self.session.execute(stmt)
        return [
            {
                "id": e.id, "name": e.name, "role": e.role,
                "shift_group": e.shift_group,
                "is_first_manager": e.is_first_manager,
                "is_second_manager": e.is_second_manager,
                "is_third_manager": e.is_third_manager,
            }
            for e in result.scalars().all()
        ]

    # ==================== 批量写入（指纹机同步用） ====================

    async def bulk_upsert_records(self, records: list[AttendanceRecord]) -> int:
        """批量 upsert，返回成功数量"""
        count = 0
        for record in records:
            await self.upsert_record(record)
            count += 1
        return count

    async def get_monthly_attendance_stats(
        self, employee_id: uuid.UUID, year: int, month: int
    ) -> dict:
        """获取员工月度考勤统计，供 KPI/工资模块调用。"""
        from datetime import datetime
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        stmt = select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.store_id == self.store_id,
                AttendanceRecord.date >= start,
                AttendanceRecord.date < end,
            )
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        present = sum(1 for r in rows if r.clock_in)
        late = sum(1 for r in rows if r.late_minutes and r.late_minutes > 0)
        absent = sum(1 for r in rows if r.status == "absent")
        leave = sum(1 for r in rows if r.scheduled_shift in ("leave", "请假"))
        return {
            "total_days": len(rows),
            "present_days": present,
            "late_count": late,
            "absent_count": absent,
            "leave_days": leave,
        }
