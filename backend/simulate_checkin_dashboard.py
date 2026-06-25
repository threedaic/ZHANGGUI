"""模拟打卡数据 → 验证日常页数据看板显示

场景：5个员工今日排班
  - emp0/emp1/emp2：夜班（应到）
  - emp3：请假
  - emp4：休息

打卡模拟：
  - emp0：正常打卡 17:55（实到）
  - emp1：迟到打卡 18:30（迟到30分钟）
  - emp2：不打卡（旷工）

期望看板结果：
  应到=3  实到=2  迟到=1  早退=0  旷工=1  请假=1
"""
import asyncio
import uuid
from datetime import datetime, date, timedelta, timezone
from app.database import AsyncSessionLocal
from sqlalchemy import select, and_, delete, text
from app.models.employee import Employee
from app.models.store import Store
from app.models.attendance import AttendanceRecord
from app.models.schedule import Schedule
from app.repositories.dashboard import DashboardRepository

# 用固定 UUID 标记本次模拟数据，便于清理
SIM_TAG = "SIM_CHECKIN_DASHBOARD_TEST"
TODAY = date.today()


def _ts(hour: int, minute: int) -> datetime:
    """构造今日某时区的 datetime（UTC+8）"""
    return datetime(TODAY.year, TODAY.month, TODAY.day, hour, minute, tzinfo=timezone(timedelta(hours=8)))


async def main():
    async with AsyncSessionLocal() as session:
        # 1. 找一家门店 + 5个员工
        store = (await session.execute(select(Store).order_by(Store.created_at).limit(1))).scalar_one_or_none()
        if not store:
            print("❌ 没有门店，先 init_test_data")
            return
        store_id = store.id

        emp_result = await session.execute(
            select(Employee).where(Employee.store_id == store_id).order_by(Employee.created_at).limit(5)
        )
        employees = list(emp_result.scalars().all())
        if len(employees) < 5:
            print(f"❌ 员工不足5人，当前 {len(employees)} 人")
            return

        print(f"门店: {store.name} ({store_id})")
        print(f"今日: {TODAY}")
        print(f"员工: {[e.name for e in employees[:5]]}")
        print("=" * 60)

        # 2. 清理今日可能存在的旧数据（避免唯一约束冲突）
        await session.execute(
            delete(Schedule).where(
                and_(Schedule.store_id == store_id, Schedule.date == TODAY)
            )
        )
        await session.execute(
            delete(AttendanceRecord).where(
                and_(AttendanceRecord.store_id == store_id, AttendanceRecord.date == TODAY)
            )
        )
        await session.commit()

        # 3. 插入假排班
        schedules = [
            Schedule(employee_id=employees[0].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=employees[1].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=employees[2].id, store_id=store_id, date=TODAY, shift_type="night", note=SIM_TAG),
            Schedule(employee_id=employees[3].id, store_id=store_id, date=TODAY, shift_type="leave", note=SIM_TAG),
            Schedule(employee_id=employees[4].id, store_id=store_id, date=TODAY, shift_type="rest", note=SIM_TAG),
        ]
        session.add_all(schedules)
        await session.commit()
        print("✅ 排班已插入：3夜班 + 1请假 + 1休息")

        # 4. 插入假打卡
        records = [
            # emp0 正常打卡 17:55
            AttendanceRecord(
                store_id=store_id, employee_id=employees[0].id, date=TODAY,
                scheduled_shift="night", shift_start_time="18:00", shift_end_time="02:00", is_overnight=True,
                clock_in=_ts(17, 55), clock_out=None,
                status="normal", late_minutes=0, early_minutes=0, source="manual", note=SIM_TAG,
            ),
            # emp1 迟到打卡 18:30（迟到30分钟）
            AttendanceRecord(
                store_id=store_id, employee_id=employees[1].id, date=TODAY,
                scheduled_shift="night", shift_start_time="18:00", shift_end_time="02:00", is_overnight=True,
                clock_in=_ts(18, 30), clock_out=None,
                status="late", late_minutes=30, early_minutes=0, source="manual", note=SIM_TAG,
            ),
            # emp2 不打卡 → 旷工
        ]
        session.add_all(records)
        await session.commit()
        print("✅ 打卡已插入：emp0 正常 / emp1 迟到30分钟 / emp2 不打卡")
        print("=" * 60)

        # 5. 调用看板 Repository 验证
        repo = DashboardRepository(session, store_id)
        summary = await repo.get_attendance_summary()

        print("📊 数据看板返回结果：")
        print(f"  应到 (scheduled_count): {summary.scheduled_count}")
        print(f"  实到 (actual_count)   : {summary.actual_count}")
        print(f"  迟到 (late_count)     : {summary.late_count}")
        print(f"  早退 (early_count)    : {summary.early_count}")
        print(f"  旷工 (absent_count)   : {summary.absent_count}")
        print(f"  请假 (leave_count)    : {summary.leave_count}")
        print("=" * 60)

        # 6. 期望值校验
        expected = {
            "应到": 3, "实到": 2, "迟到": 1, "早退": 0, "旷工": 1, "请假": 1,
        }
        actual = {
            "应到": summary.scheduled_count, "实到": summary.actual_count,
            "迟到": summary.late_count, "早退": summary.early_count,
            "旷工": summary.absent_count, "请假": summary.leave_count,
        }
        all_ok = True
        for k, exp in expected.items():
            got = actual[k]
            mark = "✅" if got == exp else "❌"
            if got != exp:
                all_ok = False
            print(f"  {mark} {k}: 期望={exp} 实际={got}")

        print("=" * 60)
        if all_ok:
            print("🎉 全部通过！打卡数据已正确显示到日常页数据看板")
        else:
            print("⚠️ 有数据不匹配，请检查")

        # 7. 清理假数据
        await session.execute(
            delete(Schedule).where(
                and_(Schedule.store_id == store_id, Schedule.date == TODAY, Schedule.note == SIM_TAG)
            )
        )
        await session.execute(
            delete(AttendanceRecord).where(
                and_(AttendanceRecord.store_id == store_id, AttendanceRecord.date == TODAY, AttendanceRecord.note == SIM_TAG)
            )
        )
        await session.commit()
        print("🧹 已清理模拟数据")


if __name__ == "__main__":
    asyncio.run(main())
