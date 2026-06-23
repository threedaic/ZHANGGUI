"""Debug script for fetch_checkin_data"""
import asyncio
from datetime import datetime, date, timedelta
from app.database import AsyncSessionLocal
from sqlalchemy import select, and_
from app.models.employee import Employee
from app.models.attendance import ShiftConfig, AttendanceRecord
from app.repositories.attendance import AttendanceRepository
from app.services.attendance import AttendanceService
from app.services.wework import get_access_token
from app.utils.http_client import http_client

WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin"


async def main():
    async with AsyncSessionLocal() as session:
        store_id = 1
        target_date = "2026-06-16"

        # Step 1: Load employees
        stmt = select(Employee).where(
            and_(Employee.store_id == store_id, Employee.status == "active", Employee.wework_userid.isnot(None))
        )
        emp_result = await session.execute(stmt)
        employees = {e.wework_userid: e for e in emp_result.scalars().all()}

        # Step 2: Load shift configs
        shift_stmt = select(ShiftConfig).where(
            and_(ShiftConfig.store_id == store_id, ShiftConfig.is_active.is_(True))
        )
        shift_result = await session.execute(shift_stmt)
        shift_configs = {sc.shift_code: sc for sc in shift_result.scalars().all()}
        group_to_code = {"day": "day", "白班": "day", "night": "night", "夜班": "night"}

        # Step 3: Load existing records
        repo = AttendanceRepository(session, store_id)
        dt = date.fromisoformat(target_date)
        existing_records = await repo.get_records_by_date_range(dt, dt)
        existing_map = {r.employee_id: r for r in existing_records}
        print(f"existing_map size: {len(existing_map)}")

        # Step 4: Fetch API data
        token = await get_access_token(session, store_id)
        next_dt = dt + timedelta(days=1)
        start_ts = int(datetime(dt.year, dt.month, dt.day, 10, 0, 0).timestamp())
        end_ts = int(datetime(next_dt.year, next_dt.month, next_dt.day, 10, 0, 0).timestamp())
        userid_list = list(employees.keys())
        url = f"{WECOM_API}/checkin/getcheckindata?access_token={token}"
        body = {"opencheckindatatype": 3, "starttime": start_ts, "endtime": end_ts, "useridlist": userid_list}
        resp = await http_client.post(url, json_body=body)
        data = resp.json()
        print(f"API returned {len(data.get('checkindata', []))} records")

        # Step 5: Process data with debug
        user_day_data = {}
        for item in data.get("checkindata", []):
            userid = item.get("userid")
            checkin_ts = item.get("checkin_time")
            if not userid or not checkin_ts:
                continue
            checkin_dt = datetime.fromtimestamp(checkin_ts)
            shift_date = target_date
            key = (userid, shift_date)
            if key not in user_day_data:
                user_day_data[key] = {
                    "clock_in_items": [],
                    "clock_out_items": [],
                    "all_items": [],
                    "exceptions": set(),
                }
            checkin_type = item.get("checkin_type", "")
            time_entry = {
                "timestamp": checkin_ts,
                "hour_str": checkin_dt.strftime("%H:%M"),
                "type": checkin_type,
            }
            if "上班" in checkin_type:
                user_day_data[key]["clock_in_items"].append(time_entry)
                print(f"  Found 上班打卡: userid={userid} time={checkin_dt.strftime('%H:%M')}")
            elif "下班" in checkin_type:
                user_day_data[key]["clock_out_items"].append(time_entry)
                print(f"  Found 下班打卡: userid={userid} time={checkin_dt.strftime('%H:%M')}")
            else:
                user_day_data[key]["all_items"].append(time_entry)
            exc = item.get("exception_type", "")
            if exc:
                user_day_data[key]["exceptions"].add(exc)

        # Step 6: Write records with debug
        service = AttendanceService(session, store_id)
        for (userid, shift_date), day_data in user_day_data.items():
            emp = employees.get(userid)
            if not emp:
                continue
            clock_in_items = day_data["clock_in_items"]
            clock_out_items = day_data["clock_out_items"]
            all_items = day_data["all_items"]

            if clock_in_items or clock_out_items:
                clock_in_items.sort(key=lambda t: t["timestamp"])
                clock_out_items.sort(key=lambda t: t["timestamp"])
                clock_in = clock_in_items[0]["hour_str"] if clock_in_items else None
                clock_out = clock_out_items[-1]["hour_str"] if clock_out_items else None
                print(f"  {emp.name}: clock_in={clock_in} clock_out={clock_out} (new rule)")
            elif all_items:
                all_items.sort(key=lambda t: t["timestamp"])
                clock_in = all_items[0]["hour_str"]
                clock_out = all_items[-1]["hour_str"] if len(all_items) > 1 else None
                print(f"  {emp.name}: clock_in={clock_in} clock_out={clock_out} (old rule)")
            else:
                continue

            # Shift inference
            existing = existing_map.get(emp.id)
            print(
                f"  {emp.name}: existing={existing is not None} existing.scheduled_shift={existing.scheduled_shift if existing else 'no record'}"
            )
            if existing and existing.scheduled_shift and existing.scheduled_shift not in ("休息", "请假", "unknown"):
                scheduled_shift = existing.scheduled_shift
                shift_start_time = existing.shift_start_time
                shift_end_time = existing.shift_end_time
                is_overnight = existing.is_overnight or False
            else:
                shift_code = group_to_code.get(emp.shift_group or "", "night")
                shift_config = shift_configs.get(shift_code)
                print(
                    f"  {emp.name}: shift_group={emp.shift_group} -> shift_code={shift_code} -> shift_config={shift_config.shift_name if shift_config else None}"
                )
                if shift_config:
                    scheduled_shift = shift_config.shift_name
                    shift_start_time = shift_config.start_time
                    shift_end_time = shift_config.end_time
                    is_overnight = shift_config.is_overnight
                else:
                    scheduled_shift = None
                    shift_start_time = None
                    shift_end_time = None
                    is_overnight = False
            print(
                f"  {emp.name}: scheduled_shift={scheduled_shift} shift_start={shift_start_time} shift_end={shift_end_time} is_overnight={is_overnight}"
            )

            record = AttendanceRecord(
                store_id=store_id,
                employee_id=emp.id,
                date=shift_date,
                scheduled_shift=scheduled_shift,
                shift_start_time=shift_start_time,
                shift_end_time=shift_end_time,
                is_overnight=is_overnight,
                clock_in=clock_in,
                clock_out=clock_out,
                status="unknown",
                late_minutes=0,
                early_minutes=0,
                source="wecom",
                note="",
            )
            print(
                f"  Record before upsert: shift={record.scheduled_shift} start={record.shift_start_time} end={record.shift_end_time} clock_in={record.clock_in} clock_out={record.clock_out}"
            )

            target = await repo.upsert_record(record)
            print(
                f"  Record after upsert: shift={target.scheduled_shift} start={target.shift_start_time} end={target.shift_end_time} clock_in={target.clock_in} clock_out={target.clock_out}"
            )

            if target.shift_start_time and target.shift_end_time and target.clock_in:
                service._evaluate_status(target)
                print(f"  After evaluate: status={target.status} late={target.late_minutes} early={target.early_minutes}")

        await session.commit()

        # Verify in DB
        verify_records = await repo.get_records_by_date_range(dt, dt)
        for r in verify_records:
            print(f"  DB verify: emp_id={r.employee_id} shift={r.scheduled_shift} start={r.shift_start_time} end={r.shift_end_time} clock_in={r.clock_in} clock_out={r.clock_out} status={r.status} late={r.late_minutes}")

        print("Done!")


asyncio.run(main())