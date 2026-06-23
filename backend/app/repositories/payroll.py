"""
工资计算数据访问层
封装 SQL 查询，返回 ORM 对象。
"""
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from app.utils.pagination import PageParams


class PayrollRepository:
    """工资计算 Repository。每个请求创建新实例。"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    # ==================== 工资记录 CRUD ====================

    async def get_records(
        self,
        employee_id: int | None = None,
        period: str | None = None,
        status: str | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[PayrollRecord], int]:
        stmt = select(PayrollRecord).where(PayrollRecord.store_id == self.store_id)
        if employee_id:
            stmt = stmt.where(PayrollRecord.employee_id == employee_id)
        if period:
            stmt = stmt.where(PayrollRecord.period == period)
        if status:
            stmt = stmt.where(PayrollRecord.status == status)
        stmt = stmt.order_by(PayrollRecord.employee_id)

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_record_by_id(self, record_id: int) -> PayrollRecord | None:
        stmt = select(PayrollRecord).where(
            and_(PayrollRecord.id == record_id, PayrollRecord.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_records_by_ids(self, record_ids: list[int]) -> list[PayrollRecord]:
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.id.in_(record_ids),
                PayrollRecord.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_record_by_employee_period(
        self, employee_id: int, period: str
    ) -> PayrollRecord | None:
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.employee_id == employee_id,
                PayrollRecord.period == period,
                PayrollRecord.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_record(self, record: PayrollRecord) -> PayrollRecord:
        """存在则更新，不存在则插入"""
        existing = await self.get_record_by_employee_period(
            record.employee_id, record.period
        )
        if existing:
            existing.base_salary = record.base_salary
            existing.kpi_coefficient = record.kpi_coefficient
            existing.commission_bottle = record.commission_bottle
            existing.commission_card = record.commission_card
            existing.commission_total = record.commission_total
            existing.deduction_late = record.deduction_late
            existing.deduction_absent = record.deduction_absent
            existing.deduction_other = record.deduction_other
            existing.deduction_total = record.deduction_total
            existing.net_pay = record.net_pay
            existing.status = record.status
            existing.generated_at = record.generated_at
            existing.notes = record.notes
            return existing
        else:
            self.session.add(record)
            return record

    async def batch_update_status(
        self, record_ids: list[int], status: str, **kwargs
    ) -> int:
        """批量更新状态，返回影响行数"""
        stmt = (
            update(PayrollRecord)
            .where(
                and_(
                    PayrollRecord.id.in_(record_ids),
                    PayrollRecord.store_id == self.store_id,
                )
            )
            .values(status=status, **kwargs)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    # ==================== 辅助查询 ====================

    async def get_active_employees(self) -> list[Employee]:
        """获取门店所有在职员工"""
        stmt = select(Employee).where(
            and_(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_employee_info(self, employee_ids: list[int]) -> dict[int, dict]:
        """批量获取员工信息 {employee_id: {name, role, base_salary}}"""
        stmt = select(Employee).where(
            and_(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return {
            e.id: {
                "name": e.name,
                "role": e.role,
                "base_salary": e.base_salary,
            }
            for e in result.scalars().all()
        }

    async def get_monthly_attendance_summary(
        self, employee_id: int, period: str
    ) -> dict:
        """
        获取员工月度考勤扣款汇总。
        占位实现：从 attendance_records 表拉取迟到/缺勤扣款数据。
        后续由考勤模块提供标准 API 后对接。
        """
        from sqlalchemy import text
        year, month = int(period[:4]), int(period[5:7])
        month_str = f"{year}-{month:02d}"

        result = await self.session.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE status = 'late') AS late_count, "
                "  COALESCE(SUM(late_minutes), 0) AS total_late_minutes, "
                "  COUNT(*) FILTER (WHERE status = 'absent') AS absent_count, "
                "  COUNT(*) FILTER (WHERE status = 'early') AS early_count "
                "FROM attendance_records "
                "WHERE employee_id = :eid "
                "  AND store_id = :sid "
                "  AND date_trunc('month', date) = :month"
            ),
            {"eid": employee_id, "sid": self.store_id, "month": f"{month_str}-01"},
        )
        row = result.mappings().first()
        return dict(row) if row else {"late_count": 0, "total_late_minutes": 0, "absent_count": 0, "early_count": 0}

    async def get_monthly_kpi_coefficient(
        self, employee_id: int, period: str
    ) -> float:
        """
        获取员工月度 KPI 系数。
        占位实现：从 kpi_results 表取已确认的系数。
        后续 KPI 模块完善后对接。
        """
        from app.models.kpi import KPIResult
        stmt = select(KPIResult.coefficient).where(
            and_(
                KPIResult.employee_id == employee_id,
                KPIResult.store_id == self.store_id,
                KPIResult.period == period,
                KPIResult.status == "confirmed",
            )
        )
        result = await self.session.execute(stmt)
        coefficient = result.scalar_one_or_none()
        return float(coefficient) if coefficient else 1.00
