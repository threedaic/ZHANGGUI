"""
数据看板数据访问层
封装聚合 SQL 查询，返回 ORM 对象 / 原始数据。
依赖: DailyRevenue, GuestRating, Booking, Table, AttendanceRecord
"""
import uuid
from datetime import date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.revenue import DailyRevenue
from app.models.rating import GuestRating
from app.models.booking import Booking, Table
from app.models.attendance import AttendanceRecord
from app.models.table_session import TableSession
from app.schemas.dashboard import (
    RevenueBlock, RevenueBreakdown, ChartPoint,
    RatingSummary, LowScoreAlert, BookingSummary, AttendanceSummary,
    MyPerformance,
)


class DashboardRepository:
    """数据看板 Repository"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ==================== 营收概览 ====================

    async def _latest_revenue_date(self) -> date | None:
        """获取最近有营收数据的日期（用于今日无数据时回退）"""
        stmt = select(func.max(DailyRevenue.date)).where(
            DailyRevenue.store_id == self.store_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_revenue_block(self) -> RevenueBlock | None:
        """获取今日营收概览，含昨日对比。今日无数据时回退到最近有数据的日期。"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 先查今日和昨日（用 date 对象，避免 PG 类型错误）
        stmt = select(DailyRevenue).where(
            and_(
                DailyRevenue.store_id == self.store_id,
                DailyRevenue.date.in_([today, yesterday]),
            )
        )
        result = await self.session.execute(stmt)
        rows = {r.date: r for r in result.scalars().all()}

        today_row = rows.get(today)
        yesterday_row = rows.get(yesterday)

        # 今日无数据 → 回退到最近有数据的日期
        if not today_row:
            latest = await self._latest_revenue_date()
            if not latest:
                return None
            # 用最近日期作为"今日"，其前一天作为"昨日"
            prev = latest - timedelta(days=1)
            stmt2 = select(DailyRevenue).where(
                and_(
                    DailyRevenue.store_id == self.store_id,
                    DailyRevenue.date.in_([latest, prev]),
                )
            )
            result2 = await self.session.execute(stmt2)
            rows2 = {r.date: r for r in result2.scalars().all()}
            today_row = rows2.get(latest)
            yesterday_row = rows2.get(prev)

        if not today_row and not yesterday_row:
            return None

        today_revenue = today_row.total_revenue if today_row else 0.0
        yesterday_revenue = yesterday_row.total_revenue if yesterday_row else 0.0
        today_orders = 0  # fin_daily_revenue 无订单数列
        today_guests = 0  # fin_daily_revenue 无客人数列
        today_avg = float(today_row.avg_spend or 0) if today_row else 0.0

        if yesterday_revenue > 0:
            growth_rate = round((today_revenue - yesterday_revenue) / yesterday_revenue, 4)
        elif today_revenue > 0:
            growth_rate = 1.0
        else:
            growth_rate = 0.0

        return RevenueBlock(
            today_revenue=today_revenue,
            yesterday_revenue=yesterday_revenue,
            growth_rate=growth_rate,
            total_orders=today_orders,
            total_guests=today_guests,
            avg_order_value=today_avg,
        )

    # ==================== 营收构成 ====================

    async def get_revenue_breakdown(self) -> RevenueBreakdown | None:
        """获取今日营收构成。今日无数据时回退到最近有数据的日期。"""
        today = date.today()

        stmt = select(DailyRevenue).where(
            and_(
                DailyRevenue.store_id == self.store_id,
                DailyRevenue.date == today,
            )
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        # 今日无数据 → 回退到最近有数据的日期
        if not row:
            latest = await self._latest_revenue_date()
            if not latest:
                return None
            stmt2 = select(DailyRevenue).where(
                and_(
                    DailyRevenue.store_id == self.store_id,
                    DailyRevenue.date == latest,
                )
            )
            result2 = await self.session.execute(stmt2)
            row = result2.scalar_one_or_none()

        if not row:
            return None

        total = row.total_revenue
        bottle = float(row.pos_revenue or 0)      # POS 营收
        card = float(row.wecom_revenue or 0)       # 企微营收
        other = float(row.cash_revenue or 0) + float(row.member_revenue or 0)

        return RevenueBreakdown(
            bottle_sales=bottle,
            card_sales=card,
            other_sales=other,
            total=total,
            bottle_pct=round(bottle / total, 4) if total > 0 else 0.0,
            card_pct=round(card / total, 4) if total > 0 else 0.0,
            other_pct=round(other / total, 4) if total > 0 else 0.0,
        )

    # ==================== 7天趋势 ====================

    async def get_7day_revenue(self) -> list[ChartPoint]:
        """获取最近 7 天营收趋势"""
        today = date.today()
        dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

        stmt = select(DailyRevenue).where(
            and_(
                DailyRevenue.store_id == self.store_id,
                DailyRevenue.date.in_(dates),
            )
        )
        result = await self.session.execute(stmt)
        rows = {r.date: r for r in result.scalars().all()}

        weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        chart = []
        for d in dates:
            day_label = d.isoformat()[-5:]  # MM-DD
            wd = weekday_map[d.weekday()]
            row = rows.get(d)
            chart.append(ChartPoint(
                date=day_label,
                weekday=wd,
                revenue=row.total_revenue if row else 0.0,
                orders=0,  # fin_daily_revenue 无订单数列
            ))

        return chart

    # ==================== 顾客评分 ====================

    async def get_ratings_summary(self) -> RatingSummary:
        """获取今日评分汇总 + 低分预警"""
        today = date.today()

        # 今日评分
        stmt = select(GuestRating).where(
            and_(
                GuestRating.store_id == self.store_id,
                GuestRating.created_at >= today,
            )
        ).order_by(GuestRating.overall_score.asc())

        result = await self.session.execute(stmt)
        ratings = list(result.scalars().all())

        if not ratings:
            # 查询近 7 天数据作为 fallback
            seven_days_ago = today - timedelta(days=7)
            stmt = select(GuestRating).where(
                and_(
                    GuestRating.store_id == self.store_id,
                    GuestRating.created_at >= seven_days_ago,
                )
            ).order_by(GuestRating.overall_score.asc())
            result = await self.session.execute(stmt)
            ratings = list(result.scalars().all())

        if not ratings:
            return RatingSummary()

        total = len(ratings)
        avg = round(sum(r.overall_score for r in ratings) / total, 2)

        low_scores = [r for r in ratings if r.is_low_score or r.overall_score < 3.0]
        low_score_alerts = [
            LowScoreAlert(
                id=r.id,
                table_no=r.table_no,
                overall_score=r.overall_score,
                comment=r.comment or "",
                created_at=r.created_at,
            )
            for r in low_scores[:5]
        ]

        return RatingSummary(
            avg_score=avg,
            total_ratings=total,
            low_score_count=len(low_scores),
            alerts=low_score_alerts,
        )

    # ==================== 订桌概况 ====================

    async def get_booking_summary(self) -> BookingSummary:
        """获取今日订桌概况。今日无 confirmed 预订时回退到最近有预订的日期。"""
        today = date.today()

        # 总桌数（所有桌台）
        table_stmt = select(func.count()).select_from(Table).where(
            Table.store_id == self.store_id
        )
        table_result = await self.session.execute(table_stmt)
        total_tables = table_result.scalar() or 0

        # 今日已确认预订
        booking_stmt = select(func.count()).select_from(Booking).where(
            and_(
                Booking.store_id == self.store_id,
                Booking.date == today,
                Booking.status == "confirmed",
            )
        )
        booking_result = await self.session.execute(booking_stmt)
        confirmed = booking_result.scalar() or 0

        # 今日无 confirmed 预订 → 回退到最近有 confirmed 的日期
        if confirmed == 0:
            latest_booking_stmt = select(func.max(Booking.date)).where(
                and_(
                    Booking.store_id == self.store_id,
                    Booking.status == "confirmed",
                )
            )
            latest_booking_result = await self.session.execute(latest_booking_stmt)
            latest_booking_date = latest_booking_result.scalar_one_or_none()
            if latest_booking_date:
                fallback_stmt = select(func.count()).select_from(Booking).where(
                    and_(
                        Booking.store_id == self.store_id,
                        Booking.date == latest_booking_date,
                        Booking.status == "confirmed",
                    )
                )
                fallback_result = await self.session.execute(fallback_stmt)
                confirmed = fallback_result.scalar() or 0

        available = max(0, total_tables - confirmed)

        return BookingSummary(
            confirmed=confirmed,
            total_tables=total_tables,
            available=available,
        )

    # ==================== 今日考勤 ====================

    async def get_attendance_summary(self) -> AttendanceSummary:
        """获取今日考勤汇总。今日无数据时回退到最近有考勤的日期。"""
        today = date.today()

        # 查询今日考勤记录
        stmt = select(AttendanceRecord).where(
            and_(
                AttendanceRecord.store_id == self.store_id,
                AttendanceRecord.date == today,
            )
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        # 今日无数据 → 回退到最近有考勤的日期
        if not rows:
            latest_stmt = select(func.max(AttendanceRecord.date)).where(
                AttendanceRecord.store_id == self.store_id
            )
            latest_result = await self.session.execute(latest_stmt)
            latest_date = latest_result.scalar_one_or_none()
            if latest_date:
                stmt2 = select(AttendanceRecord).where(
                    and_(
                        AttendanceRecord.store_id == self.store_id,
                        AttendanceRecord.date == latest_date,
                    )
                )
                result2 = await self.session.execute(stmt2)
                rows = list(result2.scalars().all())

        scheduled_count = 0
        actual_count = 0
        late_count = 0
        absent_count = 0
        early_count = 0
        leave_count = 0

        for r in rows:
            # 应出勤：有排班且非休息/请假
            if r.scheduled_shift and r.scheduled_shift not in ("rest", "leave", "休息", "请假"):
                scheduled_count += 1
            # 请假
            if r.scheduled_shift in ("leave", "请假"):
                leave_count += 1
            # 实际出勤：有打卡记录（clock_in 非空）
            if r.clock_in:
                actual_count += 1
            # 迟到
            if r.late_minutes and r.late_minutes > 0:
                late_count += 1
            # 旷工
            if r.status == "absent":
                absent_count += 1
            # 早退
            if r.early_minutes and r.early_minutes > 0:
                early_count += 1

        return AttendanceSummary(
            scheduled_count=scheduled_count,
            actual_count=actual_count,
            late_count=late_count,
            absent_count=absent_count,
            early_count=early_count,
            leave_count=leave_count,
        )

    # ==================== 我的业绩 ====================

    async def get_my_performance(self, employee_id: uuid.UUID) -> MyPerformance:
        """获取当前员工本月累计企微个人收款"""
        now = date.today()
        month_start = date(now.year, now.month, 1)
        period = f"{now.year}-{now.month:02d}"

        stmt = select(func.coalesce(func.sum(TableSession.wework_pay_amount), 0)).where(
            and_(
                TableSession.store_id == self.store_id,
                TableSession.commission_employee_id == employee_id,
                TableSession.opened_at >= month_start,
            )
        )
        result = await self.session.execute(stmt)
        total = result.scalar() or 0

        return MyPerformance(
            total_wework_pay=round(float(total), 2),
            period=period,
        )

    async def get_my_performance_detail(self, employee_id: uuid.UUID) -> list[dict]:
        """获取当前员工本月每日企微收款明细"""
        from sqlalchemy import cast, Date
        from sqlalchemy.dialects.postgresql import TEXT

        now = date.today()
        month_start = date(now.year, now.month, 1)
        day_expr = func.to_char(TableSession.opened_at, 'YYYY-MM-DD').label("day")

        stmt = select(
            day_expr,
            func.coalesce(func.sum(TableSession.wework_pay_amount), 0).label("amount"),
        ).where(
            and_(
                TableSession.store_id == self.store_id,
                TableSession.commission_employee_id == employee_id,
                TableSession.opened_at >= month_start,
            )
        ).group_by(
            day_expr
        ).order_by(
            day_expr
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # 填充整个月的每一天
        row_map = {row.day: float(row.amount) for row in rows}
        days_in_month = _days_in_month(now.year, now.month)
        detail = []
        total = 0
        for d in range(1, days_in_month + 1):
            day_str = f"{now.year}-{now.month:02d}-{d:02d}"
            amt = row_map.get(day_str, 0)
            total += amt
            detail.append({
                "date": day_str,
                "amount": round(amt, 2),
                "cumulative": round(total, 2),
            })

        return detail


def _days_in_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]
