"""
考勤相关推送组装
"""
from datetime import date, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import NotificationService
from app.repositories.attendance import AttendanceRepository


async def push_daily_report(session: AsyncSession, store_id: int, target_date: date | None = None) -> None:
    """每日考勤日报"""
    if target_date is None:
        target_date = date.today()

    repo = AttendanceRepository(session, store_id)
    records = await repo.get_today_records(target_date.isoformat())

    total = len(records)
    present = sum(1 for r in records if r.status in ("present", "early"))
    late = [r for r in records if r.status == "late"]
    absent = [r for r in records if r.status == "absent"]
    leave = [r for r in records if r.status == "leave"]

    emp_ids = list(set(r.employee_id for r in records))
    emp_info = await repo._get_employee_info(emp_ids)

    late_text = "\n".join(
        f"- {emp_info.get(r.employee_id, {}).get('name', '')} 迟到 {r.late_minutes} 分钟"
        for r in late
    ) or "无"
    absent_text = "\n".join(
        f"- {emp_info.get(r.employee_id, {}).get('name', '')}"
        for r in absent
    ) or "无"
    leave_text = "\n".join(
        f"- {emp_info.get(r.employee_id, {}).get('name', '')}"
        for r in leave
    ) or "无"

    title = f"考勤日报 {target_date.isoformat()}"
    content = (
        f"应到 {total} 人，实到 {present} 人\n\n"
        f"迟到 ({len(late)}):\n{late_text}\n\n"
        f"旷工 ({len(absent)}):\n{absent_text}\n\n"
        f"请假 ({len(leave)}):\n{leave_text}"
    )

    service = NotificationService(session, store_id)
    await service.send("daily_report", title, content)


async def push_attendance_alert(
    session: AsyncSession,
    store_id: int,
    employee_name: str,
    alert_type: str,
    detail: str,
) -> None:
    """考勤异常实时推送"""
    title = f"考勤异常：{employee_name}"
    content = f"{alert_type}\n{detail}"
    service = NotificationService(session, store_id)
    await service.send("attendance_alert", title, content)


async def push_shift_status(
    session: AsyncSession,
    store_id: int,
    target_date: str,
    shift_code: str,
) -> None:
    """班次到岗检查：统计白班/晚班的打卡情况并推送。

    shift_code: 'day' 或 'night'，对应 shift_configs 中的 shift_code
    """
    repo = AttendanceRepository(session, store_id)
    records = await repo.get_today_records(target_date)
    employees = await repo.get_active_employees()
    configs = await repo.get_shift_configs(active_only=True)
    config_by_code = {c.shift_code: c for c in configs}

    target_config = config_by_code.get(shift_code)
    if not target_config:
        return

    shift_label = target_config.shift_name
    start_h, start_m = map(int, target_config.start_time.split(":"))

    clocked_in: list[str] = []
    not_clocked: list[str] = []
    late_list: list[str] = []

    emp_map = {e["id"]: e["name"] for e in employees}
    clocked_ids: set[int] = set()

    for r in records:
        if not r.clock_in:
            continue
        # 根据打卡时间匹配班次：打卡时间在上班时间前后 4 小时内算该班次
        try:
            ci_h, ci_m = map(int, r.clock_in.split(":"))
            ci_minutes = ci_h * 60 + ci_m
        except (ValueError, AttributeError):
            continue
        shift_start = start_h * 60 + start_m
        if abs(ci_minutes - shift_start) <= 240:  # 4 小时窗口
            clocked_ids.add(r.employee_id)
            name = emp_map.get(r.employee_id, f"#{r.employee_id}")
            clocked_in.append(f"{name} ({r.clock_in})")
            if r.status == "late":
                late_list.append(f"{name} 迟到{r.late_minutes}分钟")

    # 未打卡的活跃员工
    for emp in employees:
        if emp["id"] not in clocked_ids:
            not_clocked.append(emp["name"])

    title = f"{shift_label}到岗检查 {target_date}"
    content = (
        f"已到岗 ({len(clocked_in)}):\n"
        + "\n".join(f"- {c}" for c in clocked_in)
        + f"\n\n未到岗 ({len(not_clocked)}):\n"
        + "\n".join(f"- {n}" for n in not_clocked)
    )
    if late_list:
        content += f"\n\n迟到:\n" + "\n".join(f"- {l}" for l in late_list)

    from app.services.notification_service import NotificationService
    service = NotificationService(session, store_id)
    await service.send("shift_status", title, content)


async def push_shift_change(
    session: AsyncSession,
    store_id: int,
    employee_id: int,
    employee_name: str,
    old_shift: str | None,
    new_shift: str | None,
    target_date: date,
) -> None:
    """排班变更通知"""
    title = "排班变更通知"
    content = f"您 {target_date.isoformat()} 的班次由「{old_shift or '无'}」调整为「{new_shift or '无'}」"
    service = NotificationService(session, store_id)
    await service.send(
        "shift_change",
        title,
        content,
        target_user_ids=[employee_id],
    )


async def push_approval_notification(
    session: AsyncSession,
    store_id: int,
    notification_type: str,
    title: str,
    content: str,
    target_user_ids: list[int] | None = None,
) -> None:
    """审批相关通知"""
    service = NotificationService(session, store_id)
    await service.send(notification_type, title, content, target_user_ids=target_user_ids)
