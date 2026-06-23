"""
员工业绩汇总服务

业绩闭环:
  1. 订桌系统识别员工 (table_sessions.commission_employee_id)
  2. 企微收款 API 拉取个人收款 → 写入 wework_payment_sync
  3. 本服务汇总到 employee_monthly_performance（按员工×月份×业绩类型）
  4. KPI 和工资计算从 employee_monthly_performance 取数

业绩类型(performance_type):
  - booking        订桌业绩（来自 table_sessions.commission_base）
  - wework_payment 企微收款业绩（来自 wework_payment_sync.amount）
"""
from datetime import datetime
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.performance import EmployeeMonthlyPerformance
from app.models.table_session import TableSession
from app.models.wework_payment import WeworkPaymentSync


class PerformanceService:
    """员工业绩汇总 Service"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    async def sync_monthly_performance(
        self, period: str, employee_ids: list[int] | None = None
    ) -> list[EmployeeMonthlyPerformance]:
        """
        汇总指定月份的员工业绩到 employee_monthly_performance 表。

        流程:
          1. 清理该月旧的汇总数据（支持重算）
          2. 从 table_sessions 汇总订桌业绩
          3. 从 wework_payment_sync 汇总企微收款业绩
          4. 写入 employee_monthly_performance

        Args:
            period: 账期 YYYY-MM
            employee_ids: 指定员工，None=全员
        """
        year, month = int(period[:4]), int(period[5:7])
        month_start = datetime(year, month, 1)
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime(year, month + 1, 1)

        # 1. 清理旧数据（支持重算）
        del_stmt = delete(EmployeeMonthlyPerformance).where(
            and_(
                EmployeeMonthlyPerformance.store_id == self.store_id,
                EmployeeMonthlyPerformance.period == period,
                EmployeeMonthlyPerformance.source == "auto",
            )
        )
        if employee_ids:
            del_stmt = del_stmt.where(
                EmployeeMonthlyPerformance.employee_id.in_(employee_ids)
            )
        await self.session.execute(del_stmt)

        records: list[EmployeeMonthlyPerformance] = []
        now = datetime.now()

        # 2. 汇总订桌业绩（来自 table_sessions.commission_employee_id）
        booking_records = await self._aggregate_booking_performance(
            month_start, next_month_start, period, now
        )
        records.extend(booking_records)

        # 3. 汇总企微收款业绩（来自 wework_payment_sync）
        wework_records = await self._aggregate_wework_performance(
            month_start, next_month_start, period, now
        )
        records.extend(wework_records)

        # 4. 写入
        for record in records:
            self.session.add(record)

        await self.session.flush()
        logger.info(
            f"[Performance] {self.store_id} {period} 汇总 {len(records)} 条业绩记录"
        )
        return records

    async def _aggregate_booking_performance(
        self,
        month_start: datetime,
        next_month_start: datetime,
        period: str,
        now: datetime,
    ) -> list[EmployeeMonthlyPerformance]:
        """汇总订桌业绩

        按 commission_employee_id 聚合 table_sessions 的 commission_base（业绩基数）
        和订单数。
        """
        stmt = (
            select(
                TableSession.commission_employee_id.label("employee_id"),
                func.sum(TableSession.commission_base).label("total_amount"),
                func.count(TableSession.id).label("detail_count"),
            )
            .where(
                and_(
                    TableSession.store_id == self.store_id,
                    TableSession.commission_employee_id.isnot(None),
                    TableSession.opened_at >= month_start,
                    TableSession.opened_at < next_month_start,
                    TableSession.status == "closed",
                )
            )
            .group_by(TableSession.commission_employee_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            EmployeeMonthlyPerformance(
                store_id=self.store_id,
                employee_id=row.employee_id,
                period=period,
                performance_type="booking",
                total_amount=row.total_amount or 0,
                detail_count=row.detail_count or 0,
                source="auto",
                calculated_at=now,
            )
            for row in rows
            if row.employee_id is not None
        ]

    async def _aggregate_wework_performance(
        self,
        month_start: datetime,
        next_month_start: datetime,
        period: str,
        now: datetime,
    ) -> list[EmployeeMonthlyPerformance]:
        """汇总企微收款业绩

        按 employee_id 聚合 wework_payment_sync 的 amount（收款金额）
        和笔数。
        """
        stmt = (
            select(
                WeworkPaymentSync.employee_id.label("employee_id"),
                func.sum(WeworkPaymentSync.amount).label("total_amount"),
                func.count(WeworkPaymentSync.id).label("detail_count"),
            )
            .where(
                and_(
                    WeworkPaymentSync.store_id == self.store_id,
                    WeworkPaymentSync.employee_id.isnot(None),
                    WeworkPaymentSync.pay_time >= month_start,
                    WeworkPaymentSync.pay_time < next_month_start,
                    WeworkPaymentSync.sync_status == "synced",
                )
            )
            .group_by(WeworkPaymentSync.employee_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            EmployeeMonthlyPerformance(
                store_id=self.store_id,
                employee_id=row.employee_id,
                period=period,
                performance_type="wework_payment",
                total_amount=row.total_amount or 0,
                detail_count=row.detail_count or 0,
                source="auto",
                calculated_at=now,
            )
            for row in rows
            if row.employee_id is not None
        ]

    async def get_employee_performance(
        self, employee_id: int, period: str
    ) -> dict:
        """获取员工月度业绩汇总（按业绩类型聚合）

        返回:
          {
            "total_amount": 12345.67,      # 业绩总金额
            "by_type": {                    # 按类型明细
              "booking": {"amount": 10000, "count": 20},
              "wework_payment": {"amount": 2345.67, "count": 15},
            }
          }
        """
        stmt = select(EmployeeMonthlyPerformance).where(
            and_(
                EmployeeMonthlyPerformance.store_id == self.store_id,
                EmployeeMonthlyPerformance.employee_id == employee_id,
                EmployeeMonthlyPerformance.period == period,
            )
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        by_type: dict[str, dict] = {}
        total_amount = 0.0
        for r in records:
            amount = float(r.total_amount or 0)
            by_type[r.performance_type] = {
                "amount": amount,
                "count": r.detail_count,
            }
            total_amount += amount

        return {
            "total_amount": round(total_amount, 2),
            "by_type": by_type,
        }

    async def get_store_performance_summary(self, period: str) -> list[dict]:
        """获取门店月度业绩汇总（按员工聚合，用于排行榜）

        返回: [{"employee_id": 1, "total_amount": 12345.67, "booking": 10000, "wework_payment": 2345.67}, ...]
        """
        stmt = (
            select(
                EmployeeMonthlyPerformance.employee_id,
                EmployeeMonthlyPerformance.performance_type,
                EmployeeMonthlyPerformance.total_amount,
                EmployeeMonthlyPerformance.detail_count,
            )
            .where(
                and_(
                    EmployeeMonthlyPerformance.store_id == self.store_id,
                    EmployeeMonthlyPerformance.period == period,
                )
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # 按员工聚合
        emp_map: dict[int, dict] = {}
        for row in rows:
            emp = emp_map.setdefault(
                row.employee_id,
                {
                    "employee_id": row.employee_id,
                    "total_amount": 0.0,
                    "booking": 0.0,
                    "wework_payment": 0.0,
                    "booking_count": 0,
                    "wework_payment_count": 0,
                },
            )
            amount = float(row.total_amount or 0)
            emp["total_amount"] += amount
            if row.performance_type in emp:
                emp[row.performance_type] += amount
                emp[f"{row.performance_type}_count"] = row.detail_count

        # 按总业绩降序
        sorted_list = sorted(
            emp_map.values(), key=lambda x: x["total_amount"], reverse=True
        )
        for emp in sorted_list:
            emp["total_amount"] = round(emp["total_amount"], 2)
            emp["booking"] = round(emp["booking"], 2)
            emp["wework_payment"] = round(emp["wework_payment"], 2)
        return sorted_list
