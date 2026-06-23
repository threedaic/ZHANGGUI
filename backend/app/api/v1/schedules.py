"""
排班管理 API

端点（前缀 /api/v1/schedules）:
  GET  ""                       周表（start_date / end_date）
  GET  "/weeks/{week}"          ISO 周格式
  GET  "/stats"                 编制统计
  GET  "/employees"             可排班员工列表
  POST ""                       创建单条
  POST "/batch"                 批量创建
  PUT  "/{schedule_id}"          更新
  DELETE "/{schedule_id}"        删除
"""
import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.schedule import Schedule
from app.repositories.schedule import ScheduleRepository
from app.services.schedule_checker import ScheduleChecker
from app.schemas.schedule import (
    ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate,
    ScheduleResponse, ScheduleStatsItem, EmployeeBrief,
)
from app.utils.exceptions import NotFoundError, ConflictError, ValidationError
from app.utils.deps import get_store_id, require_role, make_response

router = APIRouter()


# ---- 依赖注入 ----

async def get_repo(request: Request, db: AsyncSession = Depends(get_db)):
    store_id = get_store_id(request)
    return ScheduleRepository(db, store_id)


# ---- 辅助 ----

def _parse_iso_week(week_str: str) -> tuple[date, date]:
    """将 ISO week 字符串 "2026-W24" 解析为该周的周一和周日。"""
    from datetime import timedelta
    year_str, week_str_part = week_str.split("-W")
    year = int(year_str)
    week_num = int(week_str_part)
    # 找到该年 1 月 4 日（总是 ISO 第 1 周内）
    jan4 = date(year, 1, 4)
    # 周一 = jan4 - (jan4.isoweekday() - 1) + (week_num - 1) * 7
    monday = jan4 - timedelta(days=jan4.isoweekday() - 1) + timedelta(weeks=week_num - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _enrich_with_names(schedules: list[Schedule], emp_map: dict[int, str]) -> list[dict]:
    return [
        {
            "id": s.id,
            "store_id": s.store_id,
            "employee_id": s.employee_id,
            "employee_name": emp_map.get(s.employee_id, ""),
            "date": str(s.date),
            "shift_type": s.shift_type,
            "note": s.note,
            "version": s.version,
        }
        for s in schedules
    ]


# ---- 端点 ----

@router.get("", response_model=dict)
async def list_schedules(
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
    start_date: date = Query(..., description="起始日期 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="结束日期 (YYYY-MM-DD)"),
):
    """获取指定日期范围的排班表。"""
    schedules = await repo.get_by_week(start_date, end_date)
    active_emps = await repo.get_active_employees()
    emp_map = {e.id: e.name for e in active_emps}

    return make_response(data=_enrich_with_names(schedules, emp_map), request=request)


@router.get("/weeks/{week_str}", response_model=dict)
async def list_schedules_by_week(
    week_str: str,
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """按 ISO 周获取排班表。例如: /weeks/2026-W24"""
    try:
        start_date, end_date = _parse_iso_week(week_str)
    except (ValueError, IndexError):
        raise ValidationError(f"无效的周格式: {week_str}，应为 'YYYY-Www'")

    schedules = await repo.get_by_week(start_date, end_date)
    active_emps = await repo.get_active_employees()
    emp_map = {e.id: e.name for e in active_emps}

    return make_response(data={
        "week": week_str,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "schedules": _enrich_with_names(schedules, emp_map),
    }, request=request)


@router.get("/stats", response_model=dict)
async def get_schedule_stats(
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
    start_date: date = Query(..., description="起始日期"),
    end_date: date = Query(..., description="结束日期"),
):
    """获取编制统计：每日白班/晚班/休息人数。"""
    stats = await repo.get_headcount_stats(start_date, end_date)
    return make_response(data=stats, request=request)


@router.get("/employees", response_model=dict)
async def list_schedulable_employees(
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """获取当前门店在职员工列表（用于排班选择器）。"""
    employees = await repo.get_active_employees()
    return make_response(data=[
        {"id": e.id, "name": e.name, "role": e.role, "phone": e.phone}
        for e in employees
    ], request=request)


@router.get("/my", response_model=dict)
async def get_my_schedules(
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
    employee_id: uuid.UUID = Query(..., description="当前员工的 ID"),
    start_date: date = Query(..., description="起始日期 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="结束日期 (YYYY-MM-DD)"),
):
    """获取指定员工个人的排班（员工视图。管理视图用 GET / 查全员）。
    
    员工只能查看自己的排班，前端从 auth.user.employee_id 传入。
    """
    schedules = await repo.get_by_employee_week(employee_id, start_date, end_date)
    # 查员工姓名
    employees = await repo.get_active_employees()
    emp_map = {e.id: e.name for e in employees}
    emp_name = emp_map.get(employee_id, "")

    return make_response(data={
        "employee_id": employee_id,
        "employee_name": emp_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "schedules": [
            {
                "id": s.id,
                "date": str(s.date),
                "shift_type": s.shift_type,
                "note": s.note,
            }
            for s in schedules
        ],
    }, request=request)


@router.post("", response_model=dict, status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """创建单条排班。存在冲突时返回 409。"""
    require_role(request, ["boss", "store_manager"])
    user_id = getattr(request.state, "user_id", None)
    checker = ScheduleChecker(repo)
    await checker.check_create(body.employee_id, body.date, body.shift_type)

    schedule = Schedule(
        store_id=repo.store_id,
        employee_id=body.employee_id,
        date=body.date,
        shift_type=body.shift_type,
        note=body.note,
        created_by=user_id,
    )
    created = await repo.create(schedule)
    return make_response(message="排班创建成功", data={
        "id": created.id,
        "store_id": created.store_id,
        "employee_id": created.employee_id,
        "date": str(created.date),
        "shift_type": created.shift_type,
        "note": created.note,
        "version": created.version,
    }, request=request)


@router.post("/batch", response_model=dict, status_code=201)
async def batch_create_schedules(
    body: ScheduleBatchCreate,
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """批量创建/更新一周排班。存在冲突时整体失败。"""
    require_role(request, ["boss", "store_manager"])
    user_id = getattr(request.state, "user_id", None)
    checker = ScheduleChecker(repo)

    # 1. 检查重复排班（同一员工同一天有不同排班 = 冲突）
    for s in body.schedules:
        existing = await repo.get_by_employee_date(s.employee_id, s.date)
        if existing and existing.shift_type != s.shift_type:
            raise ConflictError(
                f"排班冲突：员工 #{s.employee_id} 在 {s.date} "
                f"已有「{existing.shift_type}」，与「{s.shift_type}」不一致"
            )

    # 2. 统计新增编制
    new_entries = []
    for s in body.schedules:
        existing = await repo.get_by_employee_date(s.employee_id, s.date)
        if not existing and s.shift_type != "休息":
            new_entries.append((s.employee_id, s.date, s.shift_type))

    await checker.check_batch_headcount(new_entries)

    # 3. 写入
    created_count = 0
    updated_count = 0
    for s in body.schedules:
        existing = await repo.get_by_employee_date(s.employee_id, s.date)
        if existing:
            await repo.update(
                existing,
                shift_type=s.shift_type,
                note=s.note or existing.note,
            )
            updated_count += 1
        else:
            schedule = Schedule(
                store_id=repo.store_id,
                employee_id=s.employee_id,
                date=s.date,
                shift_type=s.shift_type,
                note=s.note,
                created_by=user_id,
            )
            await repo.create(schedule)
            created_count += 1

    return make_response(message=f"排班完成：新增 {created_count} 条，更新 {updated_count} 条", data={"created": created_count, "updated": updated_count}, request=request)


@router.put("/{schedule_id}", response_model=dict)
async def update_schedule(
    schedule_id: uuid.UUID,
    body: ScheduleUpdate,
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """更新单条排班。"""
    require_role(request, ["boss", "store_manager"])
    schedule = await repo.get_by_id(schedule_id)
    if not schedule:
        raise NotFoundError(f"排班 #{schedule_id} 不存在")

    update_data = body.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        return make_response(data={
            "id": schedule.id,
            "shift_type": schedule.shift_type,
            "note": schedule.note,
            "version": schedule.version,
        }, request=request)

    # 如果换班次，检查新班次编制
    new_shift = update_data.get("shift_type")
    if new_shift and new_shift != schedule.shift_type and new_shift != "休息":
        checker = ScheduleChecker(repo)
        await checker.ensure_headcount(schedule.date, new_shift)

    updated = await repo.update(schedule, **update_data)
    return make_response(message="排班更新成功", data={
        "id": updated.id,
        "shift_type": updated.shift_type,
        "note": updated.note,
        "version": updated.version,
    }, request=request)


@router.delete("/{schedule_id}", response_model=dict)
async def delete_schedule(
    schedule_id: uuid.UUID,
    request: Request,
    repo: ScheduleRepository = Depends(get_repo),
):
    """删除单条排班。"""
    require_role(request, ["boss", "store_manager"])
    schedule = await repo.get_by_id(schedule_id)
    if not schedule:
        raise NotFoundError(f"排班 #{schedule_id} 不存在")

    await repo.delete(schedule)
    return make_response(message="排班已删除", data=None, request=request)
