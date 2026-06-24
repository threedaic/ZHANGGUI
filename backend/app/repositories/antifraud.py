"""
防飞单数据访问层
封装 table_sessions / bookings / daily_revenue 查询。
"""
import uuid
from datetime import date, timedelta
from sqlalchemy import select, func, and_, or_, extract, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.table_session import TableSession
from app.models.booking import Booking
from app.models.revenue import DailyRevenue
from app.models.employee import Employee
from app.utils.pagination import PageParams, paginate


class AntiFraudRepository:
    """防飞单 Repository。每个请求新实例。"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ==================== 会话查询 ====================

    async def get_sessions_by_date(
        self, scan_date: str
    ) -> list[TableSession]:
        """获取指定日期的所有开台会话"""
        d = date.fromisoformat(scan_date) if isinstance(scan_date, str) else scan_date
        stmt = (
            select(TableSession)
            .where(
                and_(
                    TableSession.store_id == self.store_id,
                    cast(TableSession.opened_at, Date) == d,
                )
            )
            .order_by(TableSession.opened_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_sessions_in_range(
        self, date_from: str, date_to: str
    ) -> list[TableSession]:
        """获取日期范围内的所有会话"""
        d_from = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
        d_to = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
        stmt = (
            select(TableSession)
            .where(
                and_(
                    TableSession.store_id == self.store_id,
                    cast(TableSession.opened_at, Date) >= d_from,
                    cast(TableSession.opened_at, Date) <= d_to,
                )
            )
            .order_by(TableSession.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_session_by_id(self, session_id: uuid.UUID) -> TableSession | None:
        stmt = select(TableSession).where(
            and_(
                TableSession.id == session_id,
                TableSession.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_anomaly_sessions(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        risk_level: str | None = None,
        employee_id: uuid.UUID | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[TableSession], int]:
        """查询异常会话列表（分页）"""
        stmt = select(TableSession).where(
            and_(
                TableSession.store_id == self.store_id,
                TableSession.is_anomaly == True,
            )
        )
        if date_from:
            d = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
            stmt = stmt.where(cast(TableSession.opened_at, Date) >= d)
        if date_to:
            d = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
            stmt = stmt.where(cast(TableSession.opened_at, Date) <= d)
        if employee_id:
            stmt = stmt.where(TableSession.opened_by == employee_id)

        stmt = stmt.order_by(TableSession.opened_at.desc())

        # Count
        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        sessions = list(result.scalars().all())

        # 按 risk_level 过滤（从 anomaly_reason JSON 中提取）
        if risk_level:
            import json
            filtered = []
            for s in sessions:
                try:
                    detail = json.loads(s.anomaly_reason or "{}")
                    if detail.get("risk_level") == risk_level:
                        filtered.append(s)
                except (json.JSONDecodeError, TypeError):
                    pass
            sessions = filtered

        return sessions, total

    # ==================== 营收查询 ====================

    async def get_daily_revenue(self, scan_date: str) -> DailyRevenue | None:
        stmt = select(DailyRevenue).where(
            and_(
                DailyRevenue.store_id == self.store_id,
                DailyRevenue.date == scan_date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_revenue_range(
        self, date_from: str, date_to: str
    ) -> list[DailyRevenue]:
        stmt = (
            select(DailyRevenue)
            .where(
                and_(
                    DailyRevenue.store_id == self.store_id,
                    DailyRevenue.date >= date_from,
                    DailyRevenue.date <= date_to,
                )
            )
            .order_by(DailyRevenue.date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 员工查询 ====================

    async def get_employee_names(
        self, employee_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict]:
        """批量获取员工信息（仅本店）"""
        if not employee_ids:
            return {}
        stmt = select(Employee).where(
            and_(Employee.id.in_(employee_ids), Employee.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return {
            e.id: {"name": e.name, "role": e.role}
            for e in result.scalars().all()
        }

    async def get_employee_anomaly_history(
        self, employee_id: uuid.UUID, days: int = 30
    ) -> int:
        """获取员工近 N 天的异常会话数"""
        since = date.today() - timedelta(days=days)
        stmt = (
            select(func.count())
            .select_from(TableSession)
            .where(
                and_(
                    TableSession.store_id == self.store_id,
                    TableSession.opened_by == employee_id,
                    TableSession.is_anomaly == True,
                    cast(TableSession.opened_at, Date) >= since,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_employee_anomaly_history_batch(
        self, employee_ids: list[uuid.UUID], days: int = 30
    ) -> dict[uuid.UUID, int]:
        """批量获取员工近 N 天的异常会话数，返回 {employee_id: count}"""
        if not employee_ids:
            return {}
        since = date.today() - timedelta(days=days)
        stmt = (
            select(TableSession.opened_by, func.count())
            .select_from(TableSession)
            .where(
                and_(
                    TableSession.store_id == self.store_id,
                    TableSession.opened_by.in_(employee_ids),
                    TableSession.is_anomaly == True,
                    cast(TableSession.opened_at, Date) >= since,
                )
            )
            .group_by(TableSession.opened_by)
        )
        result = await self.session.execute(stmt)
        counts = {eid: 0 for eid in employee_ids}
        for row in result.all():
            counts[row[0]] = row[1] or 0
        return counts

    # ==================== 存储均值的辅助 ====================

    async def get_store_avg_per_guest(
        self, scan_date: str, days: int = 7
    ) -> float:
        """获取门店近 N 天人均消费均值（使用 avg_spend 字段）"""
        end_date = scan_date
        start_date = (date.fromisoformat(scan_date) - timedelta(days=days)).isoformat()

        stmt = (
            select(func.avg(DailyRevenue.avg_spend))
            .where(
                and_(
                    DailyRevenue.store_id == self.store_id,
                    DailyRevenue.date >= start_date,
                    DailyRevenue.date <= end_date,
                    DailyRevenue.avg_spend.isnot(None),
                )
            )
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return float(row[0] or 0)

    # ==================== 更新会话标记 ====================

    async def update_session_anomaly(
        self, session_id: uuid.UUID, is_anomaly: bool, anomaly_reason: str | None = None
    ) -> TableSession | None:
        session = await self.get_session_by_id(session_id)
        if not session:
            return None
        session.is_anomaly = is_anomaly
        session.anomaly_reason = anomaly_reason
        await self.session.flush()
        return session

    async def bulk_update_anomalies(
        self, updates: list[dict]
    ) -> int:
        """批量更新异常标记。updates: [{session_id, is_anomaly, anomaly_reason}]"""
        if not updates:
            return 0
        # 一次查回所有 session，避免逐条查询
        session_ids = [u["session_id"] for u in updates]
        stmt = select(TableSession).where(
            and_(
                TableSession.id.in_(session_ids),
                TableSession.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        session_map = {s.id: s for s in result.scalars().all()}

        count = 0
        for u in updates:
            session = session_map.get(u["session_id"])
            if session:
                session.is_anomaly = u["is_anomaly"]
                session.anomaly_reason = u.get("anomaly_reason")
                count += 1
        if count:
            await self.session.flush()
        return count
