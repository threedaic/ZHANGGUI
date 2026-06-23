"""
排班冲突检测服务

规则：
1. 同一员工同一天不能有重复排班
2. 单个班次每日期上限 15 人
3. 每员工每 7 天至少 1 天休息
4. 连续工作不超过 6 天

所有违规统一抛 ConflictError（code=40900）。
"""
from datetime import date, timedelta
from collections import defaultdict
from app.repositories.schedule import ScheduleRepository
from app.utils.exceptions import ConflictError

MAX_HEADCOUNT = 15
MIN_REST_DAYS = 1
MAX_CONSECUTIVE_WORK = 6


class ScheduleChecker:
    """排班冲突检测器。接收已绑定 store_id 的 Repository 实例。"""

    def __init__(self, repo: ScheduleRepository):
        self.repo = repo

    async def check_create(
        self, employee_id: int, schedule_date: date, shift_type: str
    ) -> None:
        """校验单条排班创建，不通过抛 ConflictError。"""
        # 1. 重复排班
        existing = await self.repo.get_by_employee_date(employee_id, schedule_date)
        if existing:
            raise ConflictError(
                f"排班冲突：员工 #{employee_id} 在 {schedule_date} "
                f"已有「{existing.shift_type}」排班，不允许重复"
            )

        # 2. 编制上限（休息不占编制）
        if shift_type != "休息":
            await self.ensure_headcount(schedule_date, shift_type)

    async def ensure_headcount(self, schedule_date: date, shift_type: str) -> None:
        current = await self.repo.count_by_shift_date(schedule_date, shift_type)
        if current >= MAX_HEADCOUNT:
            raise ConflictError(
                f"编制超限：{schedule_date}「{shift_type}」已排 {current} 人，"
                f"达到上限 {MAX_HEADCOUNT} 人"
            )

    async def check_batch_headcount(
        self, entries: list[tuple[int, date, str]]
    ) -> None:
        """批量校验编制上限（仅统计非休息的新增）。"""
        # 按日期+班次聚合新增人数
        additions: dict[tuple[date, str], int] = defaultdict(int)
        for _, sched_date, shift in entries:
            if shift != "休息":
                additions[(sched_date, shift)] += 1

        for (sched_date, shift), new_count in additions.items():
            current = await self.repo.count_by_shift_date(sched_date, shift)
            total = current + new_count
            if total > MAX_HEADCOUNT:
                raise ConflictError(
                    f"编制超限：{sched_date}「{shift}」已有 {current} 人，"
                    f"新增 {new_count} 人后 {total} 人，超出上限 {MAX_HEADCOUNT} 人"
                )

    async def check_rest_compliance(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """检查指定日期范围内每名员工的休息合规情况。
        
        返回违规列表：[{"employee_id": int, "rest_days": int}, ...]
        """
        schedules = await self.repo.get_by_week(start_date, end_date)
        by_employee: dict[int, list[str]] = defaultdict(list)
        for s in schedules:
            by_employee[s.employee_id].append(s.shift_type)

        active_employees = await self.repo.get_active_employees()
        active_ids = {e.id for e in active_employees}

        violations = []
        for emp_id in active_ids:
            shifts = by_employee.get(emp_id, [])
            rest_days = sum(1 for s in shifts if s == "休息")
            if rest_days < MIN_REST_DAYS:
                violations.append({
                    "employee_id": emp_id,
                    "rest_days": rest_days,
                    "message": f"员工 #{emp_id} 本周仅有 {rest_days} 天休息，"
                               f"最少需要 {MIN_REST_DAYS} 天",
                })
        return violations
