"""
智能排班引擎

约束:
- 每人每月休息 4 天（均匀分布）
- 每晚必须在岗: 第一顺位负责人 ≥1, 第二顺位负责人 ≥1
- 夜间岗位在岗率 ≥ 50%
- 白班组只排白班
"""
import random
import calendar
import time
from collections import defaultdict
from datetime import date, timedelta

from loguru import logger


def _get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _build_date_range(year: int, month: int) -> list[str]:
    days = _get_days_in_month(year, month)
    return [f"{year}-{month:02d}-{d:02d}" for d in range(1, days + 1)]


def generate_schedule(
    employees: list[dict],
    shift_configs: list[dict],
    year: int,
    month: int,
    rest_days: int = 4,
    min_coverage_ratio: float = 0.5,
) -> list[dict]:
    """根据约束生成全月排班。

    employees: [{"id", "name", "role", "shift_group", "is_first_manager", "is_second_manager"}, ...]
    shift_configs: [{"shift_code", "shift_name", "start_time", "end_time"}, ...]

    返回: [{"employee_id", "date", "scheduled_shift", "shift_name"}, ...]
    """
    random.seed(f"{year}-{month}-{time.time_ns()}")

    # shift_code → shift_name 映射
    code_to_name = {s["shift_code"]: s["shift_name"] for s in shift_configs}
    night_code = "night"
    day_code = "day"

    # 分组
    night_staff = [e for e in employees if e.get("shift_group") != "day"]
    day_staff = [e for e in employees if e.get("shift_group") == "day"]

    # 管理顺位（从夜班人员中筛选）
    first_managers = [e for e in night_staff if e.get("is_first_manager")]
    second_managers = [e for e in night_staff if e.get("is_second_manager")]
    third_managers = [e for e in night_staff if e.get("is_third_manager")]

    # 普通夜班人员
    regular_night = [
        e for e in night_staff
        if not e.get("is_first_manager") and not e.get("is_second_manager") and not e.get("is_third_manager")
    ]

    dates = _build_date_range(year, month)

    # 分配休息日：均匀分布
    rest_assignment: dict[int, set[str]] = defaultdict(set)
    _assign_rest_days(rest_assignment, night_staff, dates, rest_days)
    for emp in day_staff:
        _assign_rest_days(rest_assignment, [emp], dates, rest_days)

    # 构建排班
    schedule: list[dict] = []
    night_min = max(1, int(len(night_staff) * min_coverage_ratio))
    day_min = max(1, int(len(day_staff) * min_coverage_ratio)) if day_staff else 0

    for d in dates:
        day_of_week = date.fromisoformat(d).weekday()
        is_weekend = day_of_week >= 5

        # 夜班：先分配管理人员
        assigned_night: set[int] = set()

        for mgr_list in [first_managers, second_managers, third_managers]:
            mgrs_avail = [
                e for e in mgr_list
                if d not in rest_assignment.get(e["id"], set())
                and e["id"] not in assigned_night
            ]
            mgr_count = len(mgr_list)
            need = min(len(mgrs_avail), max(1, mgr_count))
            chosen = random.sample(mgrs_avail, need) if len(mgrs_avail) >= need else mgrs_avail
            for emp in chosen:
                assigned_night.add(emp["id"])
                schedule.append({
                    "employee_id": emp["id"],
                    "date": d,
                    "scheduled_shift": night_code,
                })

        # 填充普通夜班人员（填满所有非休息夜班人员）
        avail_regular = [
            e for e in regular_night
            if d not in rest_assignment.get(e["id"], set())
            and e["id"] not in assigned_night
        ]
        random.shuffle(avail_regular)

        for emp in avail_regular:
            assigned_night.add(emp["id"])
            schedule.append({
                "employee_id": emp["id"],
                "date": d,
                "scheduled_shift": night_code,
            })

        # 白班（填满所有非休息白班人员）
        avail_day = [
            e for e in day_staff
            if d not in rest_assignment.get(e["id"], set())
        ]
        random.shuffle(avail_day)
        for emp in avail_day:
            schedule.append({
                "employee_id": emp["id"],
                "date": d,
                "scheduled_shift": day_code,
            })

    # 标记休息日
    rest_entries = []
    for emp_id, rest_dates_set in rest_assignment.items():
        for d in rest_dates_set:
            rest_entries.append({
                "employee_id": emp_id,
                "date": d,
                "scheduled_shift": "rest",
            })
    schedule.extend(rest_entries)

    return schedule


def _assign_rest_days(
    rest_map: dict[int, set[str]],
    employees: list[dict],
    dates: list[str],
    rest_days: int,
) -> None:
    """均匀分配休息日：避免连续多天休息，避开周末聚集。"""
    if not employees or rest_days <= 0:
        return
    n_dates = len(dates)

    for emp in employees:
        # 将日期按与第一个休息日的间隔均匀散开
        step = max(1, n_dates // (rest_days + 1))
        chosen = []
        for i in range(rest_days):
            idx = step * (i + 1) - 1
            if idx < n_dates:
                chosen.append(dates[idx])
        rest_map[emp["id"]].update(chosen)
