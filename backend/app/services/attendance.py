"""
考勤与排班一体化 Service
- 排班批量保存
- 考勤状态判定（基于班次配置和打卡时间）
- 企微打卡同步
- WiFi+拍照打卡（班次智能归位）
"""
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.attendance import AttendanceRecord, ShiftConfig, CheckinWifi
from app.models.employee import Employee
from app.models.store import StoreSettings
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

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
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
        # 排班表显示所有需要排班的一线角色：店长/吧台/服务员/厨师/员工
        # 排除不需要排班的管理层：老板/加盟商/区域经理/会计/admin
        # 同时兼容历史数据中可能存在的角色中文值
        employees = await self.repo.get_active_employees(
            roles=["staff", "store_manager", "bartender", "server", "chef", "店长", "员工"]
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
        employee_id: uuid.UUID,
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
        user_id: uuid.UUID | None = None,
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

    async def get_today_status(self, employee_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
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

    # ==================== WiFi+拍照打卡 ====================

    # 打卡照片存储目录
    CHECKIN_PHOTO_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "checkin"
    )

    async def _get_store_settings(self) -> StoreSettings:
        """获取门店配置（含打卡设置）"""
        result = await self.session.execute(
            select(StoreSettings).where(StoreSettings.store_id == self.store_id)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            # 自动创建默认配置
            settings = StoreSettings(store_id=self.store_id)
            self.session.add(settings)
            await self.session.flush()
        return settings

    async def _get_bound_wifis(self, active_only: bool = True) -> list[CheckinWifi]:
        """获取门店绑定的WiFi列表"""
        stmt = select(CheckinWifi).where(CheckinWifi.store_id == self.store_id)
        if active_only:
            stmt = stmt.where(CheckinWifi.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _validate_wifi(self, ssid: str | None, bssid: str | None) -> tuple[str | None, str | None]:
        """校验WiFi是否在绑定列表中。返回(ssid, bssid)或抛异常。

        H5浏览器无法获取BSSID（仅企微JS-SDK/原生App可获取），
        因此无BSSID时跳过校验，照片作为主要防代打卡手段。
        若提供了BSSID则严格校验。
        """
        bound = await self._get_bound_wifis(active_only=True)
        if not bound:
            return ssid, bssid
        if not bssid:
            # H5浏览器限制：无BSSID时跳过校验，依赖照片
            return ssid, bssid
        matched = next((w for w in bound if w.bssid.lower() == (bssid or "").lower()), None)
        if not matched:
            raise ValidationError("当前WiFi非门店绑定WiFi，无法打卡")
        return matched.ssid, matched.bssid

    def _save_photo(self, content: bytes, filename: str) -> str:
        """保存打卡照片，返回访问URL路径"""
        os.makedirs(self.CHECKIN_PHOTO_DIR, exist_ok=True)
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(self.CHECKIN_PHOTO_DIR, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)
        return f"/uploads/checkin/{safe_name}"

    # ---------- 班次智能归位算法 ----------

    def _match_shift(
        self,
        checkin_dt: datetime,
        scheduled_shift: str | None,
        shift_configs: list[ShiftConfig],
        has_clock_in: bool,
        time_window: int = 120,
    ) -> tuple[ShiftConfig | None, str, str]:
        """班次智能归位：排班优先 + 时间窗口兜底

        返回 (shift_config, action, matched_by)
        - action: clock_in / clock_out
        - matched_by: schedule / time_window
        - time_window: 时间窗口（分钟），默认120=±2h
        """
        checkin_minutes = checkin_dt.hour * 60 + checkin_dt.minute

        # 1. 排班优先：有排班直接用排班班次
        if scheduled_shift and scheduled_shift not in ("休息", "请假"):
            shift = next(
                (s for s in shift_configs if s.shift_name == scheduled_shift or s.shift_code == scheduled_shift),
                None,
            )
            if shift:
                action = "clock_out" if has_clock_in else "clock_in"
                return shift, action, "schedule"

        # 2. 时间窗口兜底：找距离最近的班次+动作组合
        best = None  # (distance, shift, action)
        for shift in shift_configs:
            if not shift.is_active:
                continue
            start = time_to_minutes(shift.start_time)
            end = time_to_minutes(shift.end_time)
            if shift.is_overnight and end <= start:
                end += 1440

            # 上班窗口：start ± time_window（不超过下班时间）
            clock_in_window_start = max(start - time_window, 0)
            clock_in_window_end = min(start + time_window, end)
            if clock_in_window_start <= checkin_minutes <= clock_in_window_end:
                dist = abs(checkin_minutes - start)
                if best is None or dist < best[0]:
                    best = (dist, shift, "clock_in")

            # 下班窗口：end ± time_window（不早于上班时间）
            clock_out_window_start = max(start, end - time_window)
            clock_out_window_end = end + time_window
            cm = checkin_minutes
            if shift.is_overnight and cm < start:
                cm += 1440
            if clock_out_window_start <= cm <= clock_out_window_end:
                dist = abs(cm - end)
                if best is None or dist < best[0]:
                    best = (dist, shift, "clock_out")

        if best:
            return best[1], best[2], "time_window"

        # 3. 兜底：无匹配，按交替逻辑判定动作
        action = "clock_out" if has_clock_in else "clock_in"
        return None, action, "none"

    # ---------- 打卡主入口 ----------

    async def checkin(
        self,
        employee_id: uuid.UUID,
        wifi_ssid: str | None,
        wifi_bssid: str | None,
        photo_content: bytes | None,
        photo_filename: str | None,
    ) -> dict[str, Any]:
        """WiFi+拍照打卡主入口

        交替打卡：无上班记录→上班打卡；有上班无下班→下班打卡
        班次归位：排班优先 + 时间窗口兜底
        """
        settings = await self._get_store_settings()
        now = datetime.now()

        # WiFi校验
        if settings.checkin_require_wifi:
            wifi_ssid, wifi_bssid = await self._validate_wifi(wifi_ssid, wifi_bssid)

        # 照片校验
        if settings.checkin_require_photo and not photo_content:
            raise ValidationError("请拍照后打卡")
        photo_url = self._save_photo(photo_content, photo_filename) if photo_content else None

        # 获取今日记录（跨天班次需查昨天）
        today = now.date()
        today_record = await self.repo.get_record_by_employee_date(employee_id, today)
        yesterday_record = None
        if not today_record or (today_record and not today_record.clock_in):
            # 今天没打卡或没上班记录，检查昨天是否有未下班的跨天班次
            yesterday_record = await self.repo.get_record_by_employee_date(employee_id, today - timedelta(days=1))

        # 判定目标记录：跨天班次下班打卡归到昨天
        target_record = today_record
        target_date = today
        # 昨天有跨天班次且已上班未下班 → 下班打卡归昨天
        if (
            yesterday_record
            and yesterday_record.is_overnight
            and yesterday_record.clock_in
            and not yesterday_record.clock_out
        ):
            target_record = yesterday_record
            target_date = today - timedelta(days=1)

        # 获取班次配置
        shift_configs = await self.repo.get_shift_configs(active_only=True)

        # 判定动作和班次
        has_clock_in = bool(target_record and target_record.clock_in)
        scheduled = target_record.scheduled_shift if target_record else None
        shift, action, matched_by = self._match_shift(
            now, scheduled, shift_configs, has_clock_in, settings.checkin_time_window_minutes
        )

        # 获取/创建记录
        if not target_record:
            target_record = AttendanceRecord(
                store_id=self.store_id,
                employee_id=employee_id,
                date=target_date,
                status="unknown",
                source="wifi_photo",
            )
            self.session.add(target_record)

        # 写入班次信息（无排班时用匹配到的班次）
        if shift and not target_record.shift_start_time:
            target_record.scheduled_shift = shift.shift_name
            target_record.shift_start_time = shift.start_time
            target_record.shift_end_time = shift.end_time
            target_record.is_overnight = shift.is_overnight

        # 写入打卡时间
        if action == "clock_in":
            target_record.clock_in = now
        else:
            target_record.clock_out = now

        # 写入证据
        target_record.source = "wifi_photo"
        if photo_url:
            target_record.photo_url = photo_url
        if wifi_ssid:
            target_record.wifi_ssid = wifi_ssid
        if wifi_bssid:
            target_record.wifi_bssid = wifi_bssid
        target_record.photo_taken_at = now

        # 重新判定状态
        self._evaluate_status(target_record)
        await self.session.flush()

        logger.info(
            f"打卡成功: emp={employee_id} date={target_date} action={action} "
            f"shift={target_record.scheduled_shift} status={target_record.status} matched_by={matched_by}"
        )

        return {
            "record_id": target_record.id,
            "date": str(target_date),
            "action": action,
            "clock_time": now.strftime("%H:%M"),
            "scheduled_shift": target_record.scheduled_shift,
            "shift_start_time": target_record.shift_start_time,
            "shift_end_time": target_record.shift_end_time,
            "status": target_record.status,
            "late_minutes": target_record.late_minutes,
            "early_minutes": target_record.early_minutes,
            "matched_by": matched_by,
            "photo_url": photo_url,
            "wifi_ssid": wifi_ssid,
        }

    async def get_checkin_status(self, employee_id: uuid.UUID) -> dict[str, Any]:
        """获取今日打卡状态 + 本周统计（前端打卡页展示用）"""
        today = date.today()
        record = await self.repo.get_record_by_employee_date(employee_id, today)

        # 检查昨天是否有未下班的跨天班次
        yesterday = today - timedelta(days=1)
        yesterday_record = await self.repo.get_record_by_employee_date(employee_id, yesterday)

        next_action = "clock_in"
        can_checkin = True
        if record and record.clock_in and record.clock_out:
            # 今天已完整打卡
            if yesterday_record and yesterday_record.is_overnight and yesterday_record.clock_in and not yesterday_record.clock_out:
                next_action = "clock_out"
            else:
                next_action = "done"
                can_checkin = False
        elif record and record.clock_in:
            next_action = "clock_out"
        elif yesterday_record and yesterday_record.is_overnight and yesterday_record.clock_in and not yesterday_record.clock_out:
            next_action = "clock_out"

        # 本周统计（周一到今天）
        weekday = today.weekday()  # 0=Monday
        week_start = today - timedelta(days=weekday)
        weekly_stats = await self._get_weekly_stats(employee_id, week_start, today)

        return {
            "date": str(today),
            "scheduled_shift": record.scheduled_shift if record else None,
            "shift_start_time": record.shift_start_time if record else None,
            "shift_end_time": record.shift_end_time if record else None,
            "is_overnight": record.is_overnight if record else False,
            "clock_in": str(record.clock_in) if record and record.clock_in else None,
            "clock_out": str(record.clock_out) if record and record.clock_out else None,
            "status": record.status if record else "unknown",
            "late_minutes": record.late_minutes if record else 0,
            "early_minutes": record.early_minutes if record else 0,
            "can_checkin": can_checkin,
            "next_action": next_action,
            "weekly_stats": weekly_stats,
        }

    async def _get_weekly_stats(self, employee_id: uuid.UUID, week_start: date, week_end: date) -> dict[str, int]:
        """统计本周（week_start ~ week_end）的考勤数据"""
        from sqlalchemy import select, and_, func
        from app.models.attendance import AttendanceRecord

        result = await self.session.execute(
            select(
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            ).where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.date >= week_start,
                    AttendanceRecord.date <= week_end,
                )
            ).group_by(AttendanceRecord.status)
        )
        rows = result.all()
        stats = {
            "present": 0,
            "late": 0,
            "early": 0,
            "absent": 0,
            "leave": 0,
            "total": 0,
        }
        for status, count in rows:
            if status in stats:
                stats[status] = count
            stats["total"] += count
        return stats

    # ---------- 打卡配置管理 ----------

    async def get_checkin_config(self) -> dict[str, Any]:
        """获取打卡配置 + WiFi绑定列表"""
        settings = await self._get_store_settings()
        wifis = await self._get_bound_wifis(active_only=False)
        return {
            "require_wifi": settings.checkin_require_wifi,
            "require_photo": settings.checkin_require_photo,
            "grace_minutes": settings.checkin_grace_minutes,
            "photo_retention_days": settings.checkin_photo_retention_days,
            "time_window_minutes": settings.checkin_time_window_minutes,
            "wifis": [
                {
                    "id": w.id,
                    "ssid": w.ssid,
                    "bssid": w.bssid,
                    "label": w.label,
                    "is_active": w.is_active,
                }
                for w in wifis
            ],
        }

    async def update_checkin_config(self, data: dict[str, Any]) -> dict[str, Any]:
        """更新打卡配置（仅老板）"""
        settings = await self._get_store_settings()
        field_map = {
            "require_wifi": "checkin_require_wifi",
            "require_photo": "checkin_require_photo",
            "grace_minutes": "checkin_grace_minutes",
            "photo_retention_days": "checkin_photo_retention_days",
            "time_window_minutes": "checkin_time_window_minutes",
        }
        for schema_key, model_key in field_map.items():
            if schema_key in data:
                setattr(settings, model_key, data[schema_key])
        await self.session.flush()
        return await self.get_checkin_config()

    async def add_checkin_wifi(self, ssid: str, bssid: str, label: str | None = None) -> dict[str, Any]:
        """添加WiFi绑定"""
        # 检查重复
        existing = await self.session.execute(
            select(CheckinWifi).where(
                and_(CheckinWifi.store_id == self.store_id, CheckinWifi.bssid == bssid)
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("该WiFi(BSSID)已绑定")
        wifi = CheckinWifi(
            store_id=self.store_id,
            ssid=ssid,
            bssid=bssid,
            label=label,
            is_active=True,
        )
        self.session.add(wifi)
        await self.session.flush()
        await self.session.refresh(wifi)
        return {
            "id": wifi.id,
            "ssid": wifi.ssid,
            "bssid": wifi.bssid,
            "label": wifi.label,
            "is_active": wifi.is_active,
        }

    async def delete_checkin_wifi(self, wifi_id: uuid.UUID) -> None:
        """删除WiFi绑定"""
        result = await self.session.execute(
            select(CheckinWifi).where(
                and_(CheckinWifi.id == wifi_id, CheckinWifi.store_id == self.store_id)
            )
        )
        wifi = result.scalar_one_or_none()
        if not wifi:
            raise NotFoundError("WiFi绑定不存在")
        await self.session.delete(wifi)
        await self.session.flush()

    # ==================== 今日考勤名单（全员可访问） ====================

    async def get_today_attendance_list(self) -> dict[str, Any]:
        """获取今日考勤名单（全员可访问，无角色限制）。

        数据源与 dashboard 完全一致：直接遍历 att_records 表。
        今日无记录时回退到最近有记录的日期。
        """
        from sqlalchemy import func as sa_func

        today = date.today()

        # 1. 查今日考勤记录
        records = await self.repo.get_records_by_date_range(today, today)

        # 今日无记录 → 回退到最近有记录的日期
        actual_date = today
        if not records:
            latest_stmt = select(sa_func.max(AttendanceRecord.date)).where(
                AttendanceRecord.store_id == self.store_id
            )
            latest_result = await self.session.execute(latest_stmt)
            latest_date = latest_result.scalar_one_or_none()
            if latest_date:
                actual_date = latest_date
                records = await self.repo.get_records_by_date_range(latest_date, latest_date)

        # 2. 批量获取员工信息（姓名、角色）
        emp_ids = [r.employee_id for r in records]
        emp_info = await self.repo._get_employee_info(emp_ids)

        role_label_map = {
            "staff": "员工", "store_manager": "店长",
            "boss": "老板", "regional_manager": "区域经理", "franchisee": "加盟商",
            "店长": "店长", "员工": "员工", "老板": "老板",
        }

        # 3. 直接遍历考勤记录组装名单（与 dashboard 逻辑一致）
        rows = []
        for r in records:
            info = emp_info.get(r.employee_id, {})
            role = info.get("role", "")
            cell = self._record_to_cell(r, str(actual_date))
            rows.append({
                "employee_id": r.employee_id,
                "employee_name": info.get("name", ""),
                "employee_role": role,
                "employee_role_label": role_label_map.get(role, role),
                "cells": [cell],
            })

        return {
            "date": str(actual_date),
            "is_today": actual_date == today,
            "employees": rows,
        }
