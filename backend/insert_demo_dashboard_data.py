"""插入模拟打卡+排班数据（不清理），并清 Redis 看板缓存，让日常页能显示数据"""
import asyncio
from datetime import datetime, date, timedelta, timezone
from app.database import AsyncSessionLocal
from sqlalchemy import select, and_, delete, text
from app.models.employee import Employee
from app.models.store import Store
from app.models.attendance import AttendanceRecord
from app.models.schedule import Schedule
from app.utils.redis_client import get_redis

SIM_TAG = "SIM_SHOW_ON_DASHBOARD"
TODAY = date.today()


def _ts(hour: int, minute: int) -> datetime:
    return datetime(TODAY.year, TODAY.month, TODAY.day, hour, minute, tzinfo=timezone(timedelta(hours=8)))


async def main():
    async with AsyncSessionLocal() as session:
        store = (await session.execute(select(Store).order_by(Store.created_at).limit(1))).scalar_one()
        store_id = store.id
        emps = list((await session.execute(
            select(Employee).where(Employee.store_id == store_id).order_by(Employee.created_at).limit(5)
        )).scalars().all())

        print(f"门店: {store.name}  今日: {TODAY}  员工: {[e.name for e in emps[:5]]}")

        # 清今日旧模拟数据
        await session.execute(delete(Schedule).where(and_(
            Schedule.store_id == store_id, Schedule.date == TODAY, Schedule.note == SIM_TAG)))
        await session.execute(delete(AttendanceRecord).where(and_(
            AttendanceRecord.store_id == store_id, AttendanceRecord.date == TODAY, AttendanceRecord.note == SIM_TAG)))
        await session.commit()

        # 插入排班：3夜班 + 1请假 + 1休息
        session.add_all([
            Schedule(employee_id=emps[0].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=emps[1].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=emps[2].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=emps[3].id, store_id=store_id, date=TODAY, shift_type="leave", note=SIM_TAG),
            Schedule(employee_id=emps[4].id, store_id=store_id, date=TODAY, shift_type="rest", note=SIM_TAG),
        ])
        # 插入打卡：emp0正常 / emp1迟到30分钟 / emp2不打卡(旷工)
        session.add_all([
            AttendanceRecord(
                store_id=store_id, employee_id=emps[0].id, date=TODAY,
                scheduled_shift="night", shift_start_time="18:00", shift_end_time="02:00", is_overnight=True,
                clock_in=_ts(17, 55), clock_out=None,
                status="normal", late_minutes=0, early_minutes=0, source="manual", note=SIM_TAG),
            AttendanceRecord(
                store_id=store_id, employee_id=emps[1].id, date=TODAY,
                scheduled_shift="night", shift_start_time="18:00", shift_end_time="02:00", is_overnight=True,
                clock_in=_ts(18, 30), clock_out=None,
                status="late", late_minutes=30, early_minutes=0, source="manual", note=SIM_TAG),
        ])
        await session.commit()
        print("✅ 已插入模拟排班+打卡数据（不清理）")

        # 清 Redis 看板缓存
        redis = await get_redis()
        await redis.delete(f"dashboard:{store_id}")
        print("✅ 已清 Redis 看板缓存")

        print("\n现在去首页刷新，应该能看到：")
        print("  应到/实到 = 3/2")
        print("  迟到/早退 = 1/0")
        print("  请假/旷工 = 1/1")


if __name__ == "__main__":
    asyncio.run(main())
