"""验证看板 API 实际返回的数据 + 查订桌/桌台数据"""
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select, func, and_, text
from app.models.store import Store
from app.models.booking import Booking, Table
from app.repositories.dashboard import DashboardRepository

async def main():
    async with AsyncSessionLocal() as session:
        store = (await session.execute(select(Store).order_by(Store.created_at).limit(1))).scalar_one()
        store_id = store.id

        # 查桌台
        t_cnt = (await session.execute(select(func.count()).select_from(Table).where(Table.store_id == store_id))).scalar()
        t_active = (await session.execute(select(func.count()).select_from(Table).where(and_(Table.store_id == store_id, Table.status == "active")))).scalar()
        print(f"桌台总数: {t_cnt}  启用中: {t_active}")

        # 查今日订桌
        from datetime import date
        b_cnt = (await session.execute(select(func.count()).select_from(Booking).where(and_(Booking.store_id == store_id, Booking.date == date.today(), Booking.status == "confirmed")))).scalar()
        print(f"今日已确认订桌: {b_cnt}")

        # 调看板 repository
        repo = DashboardRepository(session, store_id)
        att = await repo.get_attendance_summary()
        bk = await repo.get_booking_summary()
        print(f"\n考勤: 应到={att.scheduled_count} 实到={att.actual_count} 迟到={att.late_count} 早退={att.early_count} 旷工={att.absent_count} 请假={att.leave_count}")
        print(f"订桌: 已订={bk.confirmed} 总桌={bk.total_tables} 可用={bk.available}")

asyncio.run(main())
