"""
考勤与排班一体化 Service
- 排班批量保存
- 考勤状态判定（基于班次配置和打卡时间）
- 企微打卡同步
"""
from datetime import date, datetime, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.attendance import AttendanceRecord, ShiftConfig
from app.models.employee import Employee
from app.repositories.attendance import AttendanceRepository
from app.utils.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    ValidationError,
    ForbiddenError,
)


LATE_DEDUCTION_RULES = [
    (10, 10.0),
    (30, 30.0),
    (60, 50.0),
]


def time_to_minutes(t: str) -> int:
    """HH:MM -> 分钟数"""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """分钟数 -> HH:MM"""
    minutes = minutes % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_clock(clock: str | None) -> datetime | None:
    """解析打卡时间，支持多种格式"""
    if not clock:
        return None
    formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%H:%M:%S", "%H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(clock, fmt)
        except ValueError:
            continue
    return None


class AttendanceService:
    """考勤 Service。每个请求创建新实例。"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.repo = AttendanceRepository(session, store_id)
        self.session = session
        self.store_id = store_id

    # ==================== 排班管理 ====================

    async def get_schedule_table(
        self,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """获取指定日期范围内的全员排班考勤表（仅显示需要排班的人员）"""
        records = await self.repo.get_records_by_date_range(date_from, date_to)
        # 排班表仅显示需要排班的角色：员工、店长，排除老板/加盟商/区域经理
        # 同时兼容历史数据中可能存在的角色中文值
        employees = await self.repo.get_active_employees(
            roles=["staff", "store_manager", "店长", "员工"]
        )
        shifts = await self.repo.get_shift_configs(active_only=True)

        # 按 (employee_id, date) 索引
        record_map: dict[tuple[int, str], AttendanceRecord] = {
            (r.employee_id, str(r.date)): r for r in records
        }

        date_list = []
        current = date_from
        while current <= date_to:
            date_list.append(str(current))
            current += timedelta(days=1)

        role_label_map = {
            "staff": "员工", "store_manager": "店长",
            "boss": "老板", "regional_manager": "区域经理", "franchisee": "加盟商",
            # 兼容历史数据中可能存在的角色中文值
            "店长": "店长", "员工": "员工", "老板": "老板",
        }

        rows = []
        for emp in employees:
            emp_id = emp["id"]
            cells = []
            for d in date_list:
                record = record_map.get((emp_id, d))
                cells.append(self._record_to_cell(record, d))
            rows.append({
                "employee_id": emp_id,
                "employee_name": emp["name"],
                "employee_role": emp["role"],
                "employee_role_label": role_label_map.get(emp["role"], emp["role"]),
                "shift_group": emp.get("shift_group"),
                "is_first_manager": emp.get("is_first_manager", False),
                "is_second_manager": emp.get("is_second_manager", False),
                "is_third_manager": emp.get("is_third_manager", False),
                "cells": cells,
            })

        return {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "shifts": [
                {
                    "shift_code": s.shift_code,
                    "shift_name": s.shift_name,
                    "color": s.color,
                }
                for s in shifts
            ],
            "employees": rows,
        }

    async def get_my_schedule(
        self,
        employee_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        """获取当前员工的排班考勤"""
        records = await self.repo.get_records_by_date_range(date_from, date_to, employee_id)
        shifts = await self.repo.get_shift_configs(active_only=True)

        record_map = {str(r.date): r for r in records}

        date_list = []
        current = date_from
        while current <= date_to:
            date_list.append(str(current))
            current += timedelta(days=1)

        cells = [self._record_to_cell(record_map.get(d), d) for d in date_list]

        # 本月统计
        summary = await self.repo.get_monthly_summary(
            f"{date_from.year}-{date_from.month:02d}", employee_id
        )
        stats = summary[0] if summary else {
            "total_days": 0, "present_days": 0, "late_days": 0,
            "leave_days": 0, "absent_days": 0,
        }

        return {
            "employee_id": employee_id,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "shifts": [
                {
                    "shift_code": s.shift_code,
                    "shift_name": s.shift_name,
                    "color": s.color,
                }
                for s in shifts
            ],
            "cells": cells,
            "stats": {
                "work_days": stats.get("total_days", 0),
                "present_days": stats.get("present_days", 0),
                "late_days": stats.get("late_days", 0),
                "leave_days": stats.get("leave_days", 0),
                "absent_days": stats.get("absent_days", 0),
            },
        }

    async def batch_save_schedules(
        self,
        schedules: list[dict[str, Any]],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """批量保存排班"""
        # 获取所有班次配置
        shift_configs = await self.repo.get_shift_configs(active_only=True)
        shift_map = {s.shift_code: s for s in shift_configs}
        shift_name_map = {s.shift_name: s for s in shift_configs}

        updated_count = 0
        created_count = 0

        for item in schedules:
            employee_id = item["employee_id"]
            record_date = item["date"]
            shift_value = item["scheduled_shift"]

            # 支持传入 shift_code 或 shift_name
            shift_config = shift_map.get(shift_value) or shift_name_map.get(shift_value)

            if shift_value in ("休息", "请假"):
                scheduled_shift = shift_value
                start_time = None
                end_time = None
                is_overnight = False
            elif shift_config:
                scheduled_shift = shift_config.shift_name
                start_time = shift_config.start_time
                end_time = shift_config.end_time
                is_overnight = shift_config.is_overnight
            else:
                raise ValidationError(f"未知班次: {shift_value}")

            existing = await self.repo.get_record_by_employee_date(employee_id, record_date)
            if existing:
                existing.scheduled_shift = scheduled_shift
                existing.shift_start_time = start_time
                existing.shift_end_time = end_time
                existing.is_overnight = is_overnight
                # 如果已有打卡，重新判定状态
                if existing.clock_in:
                    self._evaluate_status(existing)
                updated_count += 1
            else:
                new_record = AttendanceRecord(
                    store_id=self.store_id,
                    employee_id=employee_id,
                    date=record_date,
                    scheduled_shift=scheduled_shift,
                    shift_start_time=start_time,
                    shift_end_time=end_time,
                    is_overnight=is_overnight,
                    status="unknown",
                    source="manual",
                )
                self.session.add(new_record)
                created_count += 1

        await self.session.flush()

        return {
            "created": created_count,
            "updated": updated_count,
        }

    def _record_to_cell(self, record: AttendanceRecord | None, date_str: str) -> dict[str, Any]:
        """将记录转换为前端单元格展示格式"""
        if not record:
            return {
                "date": date_str,
                "scheduled_shift": None,
                "status": "unknown",
                "clock_in": None,
                "clock_out": None,
                "late_minutes": 0,
                "early_minutes": 0,
                "shift_start_time": None,
                "shift_end_time": None,
                "is_overnight": False,
            }
        return {
            "date": date_str,
            "scheduled_shift": record.scheduled_shift,
            "status": record.status,
            "clock_in": record.clock_in,
            "clock_out": record.clock_out,
            "late_minutes": record.late_minutes,
            "early_minutes": record.early_minutes,
            "shift_start_time": record.shift_start_time,
            "shift_end_time": record.shift_end_time,
            "is_overnight": record.is_overnight,
        }

    # ==================== 班次配置 ====================

    async def get_shift_configs(self) -> list[ShiftConfig]:
        return await self.repo.get_shift_configs()

    async def save_shift_config(self, data: dict[str, Any]) -> ShiftConfig:
        shift_code = data["shift_code"]
        existing = await self.repo.get_shift_config_by_code(shift_code)
        if existing:
            for key in ["shift_name", "start_time", "end_time", "is_overnight", "color", "sort_order", "is_active"]:
                if key in data:
                    setattr(existing, key, data[key])
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        new_config = ShiftConfig(store_id=self.store_id, **data)
        return await self.repo.save_shift_config(new_config)

    # ==================== 考勤状态判定 ====================

    def _evaluate_status(self, record: AttendanceRecord) -> None:
        """根据班次和打卡时间判定考勤状态"""
        if record.scheduled_shift in ("休息", "请假"):
            record.status = "leave" if record.scheduled_shift == "请假" else "rest"
            record.late_minutes = 0
            record.early_minutes = 0
            return

        if not record.shift_start_time or not record.shift_end_time:
            record.status = "unknown"
            return

        clock_in_dt = parse_clock(record.clock_in)
        clock_out_dt = parse_clock(record.clock_out)

        if not clock_in_dt:
            record.status = "absent"
            record.late_minutes = 0
            record.early_minutes = 0
            return

        start_minutes = time_to_minutes(record.shift_start_time)
        end_minutes = time_to_minutes(record.shift_end_time)

        if record.is_overnight and end_minutes <= start_minutes:
            end_minutes += 1440

        # 默认宽限 5 分钟（后续可配置）
        grace_minutes = 5

        clock_in_minutes = clock_in_dt.hour * 60 + clock_in_dt.minute
        # 如果跨天且打卡时间较早，视为前一天夜班下班，这里简化处理
        if record.is_overnight and clock_in_minutes < start_minutes - 120:
            clock_in_minutes += 1440

        late_minutes = max(0, clock_in_minutes - start_minutes - grace_minutes)

        early_minutes = 0
        if clock_out_dt:
            clock_out_minutes = clock_out_dt.hour * 60 + clock_out_dt.minute
            if record.is_overnight and clock_out_minutes < end_minutes - 120:
                clock_out_minutes += 1440
            early_minutes = max(0, end_minutes - clock_out_minutes - grace_minutes)

        if late_minutes > 0:
            record.status = "late"
        elif early_minutes > 0:
            record.status = "early"
        else:
            record.status = "present"

        record.late_minutes = late_minutes
        record.early_minutes = early_minutes

    # ==================== 企微打卡同步 ====================

    async def sync_from_wework(self, target_date: str | None = None) -> dict[str, Any]:
        """从企业微信拉取打卡数据。"""
        if target_date is None:
            target_date = date.today().isoformat()

        from app.services.wework import fetch_checkin_data
        result = await fetch_checkin_data(self.session, self.store_id, target_date)
        return {
            "synced_count": result.get("synced", 0),
            "errors": result.get("errors", []),
        }

    # ==================== 迟到扣款计算 ====================

    @staticmethod
    def calculate_late_deduction(late_minutes: int, daily_salary: float = 0) -> tuple[float, str]:
        """根据迟到分钟数计算扣款金额"""
        if late_minutes <= 0:
            return 0.0, ""

        if late_minutes > 60:
            return daily_salary, f"迟到{late_minutes}分钟，扣除全天工资"

        for threshold, fee in LATE_DEDUCTION_RULES:
            if late_minutes <= threshold:
                return fee, f"迟到{late_minutes}分钟（≤{threshold}分钟），扣款{fee}元"

        return 50.0, f"迟到{late_minutes}分钟（≤60分钟），扣款50元"

    # ==================== 今日打卡状态 ====================

    async def get_today_status(self, employee_id: int | None = None) -> list[dict[str, Any]]:
        """获取今日打卡状态"""
        today = date.today().isoformat()
        records = await self.repo.get_today_records(today)

        if employee_id:
            records = [r for r in records if r.employee_id == employee_id]

        emp_ids = list(set(r.employee_id for r in records))
        emp_info = await self.repo._get_employee_info(emp_ids)

        result = []
        for r in records:
            emp = emp_info.get(r.employee_id, {})
            deduction, reason = self.calculate_late_deduction(r.late_minutes)
            result.append({
                "employee_id": r.employee_id,
                "employee_name": emp.get("name", ""),
                "role": emp.get("role", ""),
                "scheduled_shift": r.scheduled_shift,
                "clock_in": r.clock_in,
                "clock_out": r.clock_out,
                "status": r.status,
                "late_minutes": r.late_minutes,
                "deduction": deduction,
                "deduction_reason": reason,
            })
        return result

    async def get_monthly_summary(self, period: str) -> list[dict[str, Any]]:
        """月度考勤汇总（转发到 Repository）"""
        return await self.repo.get_monthly_summary(period)
