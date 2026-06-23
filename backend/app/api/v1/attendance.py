"""
考勤与排班一体化 API

路由映射：
GET    /schedule          全员排班考勤表
GET    /schedule/my       个人排班考勤
POST   /schedule/batch    批量保存排班
GET    /shifts            班次配置列表
POST   /shifts            保存班次配置
POST   /sync              同步企微打卡
GET    /monthly           月末汇总
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.attendance import AttendanceService
from app.repositories.attendance import AttendanceRepository
from app.schemas.attendance import (
    ScheduleBatchRequest,
    ShiftConfigSaveRequest,
    SyncRequest,
    ScheduleGenerateRequest,
    EmployeeRuleUpdateRequest,
)
from app.utils.deps import get_store_id, get_user_id, get_employee_id, require_role, make_response
from app.utils.pagination import PageParams, paginate
from app.utils.exceptions import ValidationError, NotFoundError

router = APIRouter()


def _parse_date(v: str) -> date:
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise ValidationError(f"日期格式错误: {v}")


# ==================== 排班考勤表 ====================

@router.get("/schedule")
async def get_schedule(
    request: Request,
    date_from: str = Query(..., description="起始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """获取全员排班考勤表（店长/老板）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    svc = AttendanceService(db, store_id)
    data = await svc.get_schedule_table(_parse_date(date_from), _parse_date(date_to))
    return make_response(request=request, data=data)


@router.get("/schedule/my")
async def get_my_schedule(
    request: Request,
    date_from: str = Query(..., description="起始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """获取当前员工个人排班考勤"""
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)
    svc = AttendanceService(db, store_id)
    data = await svc.get_my_schedule(employee_id, _parse_date(date_from), _parse_date(date_to))
    return make_response(request=request, data=data)


@router.post("/schedule/batch")
async def batch_save_schedule(
    request: Request,
    body: ScheduleBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量保存排班（店长/老板）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    svc = AttendanceService(db, store_id)
    result = await svc.batch_save_schedules(
        [s.model_dump() for s in body.schedules],
        user_id=user_id,
    )
    return make_response(request=request, message="排班保存成功", data=result)


@router.post("/schedule/generate")
async def generate_schedule(
    request: Request,
    body: ScheduleGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """智能排班生成：根据约束自动排班（仅老板）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    repo = AttendanceRepository(db, store_id)

    # 获取员工（仅排班人员：员工+店长，排除老板）
    employees = await repo.get_active_employees(roles=["staff", "store_manager"])
    # 完善员工信息（管理标志、班组）
    from sqlalchemy import select
    from app.models.employee import Employee
    emp_result = await db.execute(
        select(Employee).where(Employee.id.in_([e["id"] for e in employees]))
    )
    emp_map = {e.id: e for e in emp_result.scalars().all()}
    emp_data = []
    for e in employees:
        emp_obj = emp_map.get(e["id"])
        emp_data.append({
            "id": e["id"],
            "name": e["name"],
            "role": e["role"],
            "shift_group": emp_obj.shift_group if emp_obj else None,
            "is_first_manager": emp_obj.is_first_manager if emp_obj else False,
            "is_second_manager": emp_obj.is_second_manager if emp_obj else False,
            "is_third_manager": emp_obj.is_third_manager if emp_obj else False,
        })

    # 获取班次
    shifts = await repo.get_shift_configs(active_only=True)
    shift_data = [{"shift_code": s.shift_code, "shift_name": s.shift_name,
                   "start_time": s.start_time, "end_time": s.end_time} for s in shifts]

    # 获取休息天数
    from app.models.store import StoreSettings
    settings_result = await db.execute(
        select(StoreSettings).where(StoreSettings.store_id == store_id)
    )
    settings = settings_result.scalar_one_or_none()
    rest_days = settings.rest_days_per_month if settings else 4

    # 生成
    from app.services.schedule_generator import generate_schedule as do_generate
    schedules = do_generate(emp_data, shift_data, body.year, body.month, rest_days=rest_days)

    # 补充员工姓名
    name_map = {e["id"]: e["name"] for e in emp_data}
    for s in schedules:
        s["employee_name"] = name_map.get(s["employee_id"], "")

    # 统计
    stats = {"total_entries": len(schedules),
             "employees": len(emp_data),
             "rest_days": rest_days}

    return make_response(request=request, data={
        "schedules": schedules,
        "stats": stats,
    })


# ==================== 员工排班规则 ====================

@router.put("/employee-rules")
async def update_employee_rules(
    request: Request,
    body: "EmployeeRuleUpdateRequest",
    db: AsyncSession = Depends(get_db),
):
    """批量更新员工排班规则：班组、管理顺位（仅老板）"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    from sqlalchemy import select, and_
    from app.models.employee import Employee
    updated = 0
    for item in body.employees:
        stmt = select(Employee).where(
            and_(Employee.id == item.employee_id, Employee.store_id == store_id)
        )
        emp_result = await db.execute(stmt)
        emp = emp_result.scalar_one_or_none()
        if emp:
            emp.shift_group = item.shift_group
            emp.is_first_manager = item.is_first_manager
            emp.is_second_manager = item.is_second_manager
            emp.is_third_manager = item.is_third_manager
            updated += 1

    await db.commit()
    return make_response(request=request, data={"updated": updated})


# ==================== 班次配置 ====================

@router.get("/shifts")
async def list_shifts(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取门店班次配置"""
    store_id = get_store_id(request)
    repo = AttendanceRepository(db, store_id)
    shifts = await repo.get_shift_configs()
    return make_response(
        request=request,
        data=[
            {
                "id": s.id,
                "shift_code": s.shift_code,
                "shift_name": s.shift_name,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "is_overnight": s.is_overnight,
                "color": s.color,
                "sort_order": s.sort_order,
                "is_active": s.is_active,
            }
            for s in shifts
        ],
    )


@router.post("/shifts")
async def save_shift(
    request: Request,
    body: ShiftConfigSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存/更新班次配置（仅老板）"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    svc = AttendanceService(db, store_id)
    config = await svc.save_shift_config(body.model_dump())

    # 实时更新到岗检查调度任务
    from app.tasks.scheduler import schedule_shift_check
    schedule_shift_check(config.shift_code, config.start_time, config.shift_name)

    return make_response(request=request, data={
        "id": config.id,
        "shift_code": config.shift_code,
        "shift_name": config.shift_name,
        "start_time": config.start_time,
        "end_time": config.end_time,
        "is_overnight": config.is_overnight,
        "color": config.color,
        "sort_order": config.sort_order,
        "is_active": config.is_active,
    })


# ==================== 企微打卡同步 ====================

@router.post("/sync")
async def sync_checkin(
    request: Request,
    body: SyncRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """手动同步企微打卡"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    svc = AttendanceService(db, store_id)
    target_date = body.target_date if body else None
    result = await svc.sync_from_wework(target_date)
    return make_response(request=request, data=result)


# ==================== 打卡记录列表 ====================

@router.get("/records")
async def get_records(
    request: Request,
    employee_id: uuid.UUID | None = Query(None),
    date_from: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    status: str | None = Query(None, description="状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """查询打卡记录列表"""
    store_id = get_store_id(request)
    repo = AttendanceRepository(db, store_id)
    params = PageParams(page=page, page_size=page_size)

    records, total = await repo.get_records(
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        page=params,
    )

    emp_ids = list(set(r.employee_id for r in records))
    emp_info = await repo._get_employee_info(emp_ids)

    items = []
    for r in records:
        emp = emp_info.get(r.employee_id, {})
        deduction, reason = AttendanceService.calculate_late_deduction(
            r.late_minutes, emp.get("base_salary", 0) / 22
        )
        items.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "store_id": r.store_id,
            "date": str(r.date),
            "scheduled_shift": r.scheduled_shift,
            "clock_in": r.clock_in,
            "clock_out": r.clock_out,
            "status": r.status,
            "late_minutes": r.late_minutes,
            "early_minutes": r.early_minutes,
            "source": r.source,
            "note": r.note,
            "employee_name": emp.get("name", ""),
            "deduction": deduction,
            "deduction_reason": reason,
        })

    result = paginate(items, total, params)
    return make_response(request=request, data=result.model_dump())


# ==================== 月末汇总 ====================

@router.get("/monthly")
async def get_monthly_summary(
    request: Request,
    period: str = Query(..., description="月份，如 2026-06"),
    db: AsyncSession = Depends(get_db),
):
    """月末考勤汇总"""
    store_id = get_store_id(request)
    svc = AttendanceService(db, store_id)
    result = await svc.get_monthly_summary(period=period)
    return make_response(request=request, data={"period": period, "store_id": store_id, "items": result})
