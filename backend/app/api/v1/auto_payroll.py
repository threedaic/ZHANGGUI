"""
自动发薪 API 路由
/api/v1/auto-payroll/

GET    /              获取工资大表格
POST   /calculate     重新计算（自动触发）
PUT    /modules       设置模块开关
GET    /modules       获取模块开关
PUT    /rules         更新薪资规则
GET    /rules         获取薪资规则
PUT    /cell          更新单元格（手动调整）
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auto_payroll import AutoPayrollService, MODULES
from app.utils.deps import require_role, get_store_id, make_response, require_employee_id

router = APIRouter()


def _get_service(request: Request, db: AsyncSession) -> AutoPayrollService:
    store_id = get_store_id(request)
    return AutoPayrollService(db, store_id)


# ==================== 大表格 ====================

@router.get("", summary="获取工资大表格")
async def get_table(
    request: Request,
    period: str = Query(..., description="账期 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    service = _get_service(request, db)
    data = await service.get_table(period)
    return make_response(data=data, request=request)


@router.post("/calculate", summary="重新计算工资")
async def calculate(
    request: Request,
    period: str = Query(..., description="账期 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    service = _get_service(request, db)
    data = await service.calculate(period)
    await db.commit()
    return make_response(message="计算完成", data=data, request=request)


@router.post("/finalize", summary="一键发薪（算完存档+推送签收）")
async def finalize(
    request: Request,
    period: str = Query(..., description="账期 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    """一键发薪：自动计算 → 存档到 wage_records → 推送签收任务到员工收件箱"""
    require_role(request, ["boss"])
    issued_by = require_employee_id(request)
    service = _get_service(request, db)
    data = await service.finalize(period, issued_by)
    return make_response(
        message=f"已发薪 {data['count']} 人，推送 {data['tasks_created']} 个签收任务",
        data=data,
        request=request,
    )


# ==================== 模块开关 ====================

@router.get("/modules", summary="获取模块开关")
async def get_modules(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    service = _get_service(request, db)
    modules = await service.get_modules()
    return make_response(data={"modules": modules, "module_info": MODULES}, request=request)


class ModulesUpdateRequest(BaseModel):
    performance: bool | None = None
    kpi: bool | None = None
    reward_penalty: bool | None = None
    overtime: bool | None = None


@router.put("/modules", summary="设置模块开关")
async def set_modules(
    request: Request,
    body: ModulesUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    service = _get_service(request, db)
    modules = await service.set_modules(body.model_dump(exclude_none=True))
    await db.commit()
    return make_response(message="模块设置已更新", data=modules, request=request)


# ==================== 薪资规则 ====================

@router.get("/rules", summary="获取薪资规则")
async def get_rules(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    service = _get_service(request, db)
    rules = await service.get_rules()
    return make_response(data=rules, request=request)


class RulesUpdateRequest(BaseModel):
    commission_rate: float | None = None
    commission_mode: str | None = None  # fixed / by_role / tiered
    commission_rates_by_role: dict | None = None  # {"bar_manager": 0.10, ...}
    commission_tiers: list | None = None  # [{"min": 0, "rate": 0.05}, ...]
    late_deduction_per_minute: float | None = None
    absent_factor: float | None = None
    early_deduction_per_time: float | None = None
    rest_days_per_month: int | None = None
    overtime_multiplier: float | None = None
    base_salary: float | None = None
    late_to_absent_minutes: int | None = None  # 迟到多久算旷工


@router.put("/rules", summary="更新薪资规则")
async def set_rules(
    request: Request,
    body: RulesUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    service = _get_service(request, db)
    rules = await service.set_rules(body.model_dump(exclude_none=True))
    await db.commit()
    return make_response(message="规则已更新", data=rules, request=request)


# ==================== 单元格编辑 ====================

class CellUpdateRequest(BaseModel):
    employee_id: uuid.UUID
    period: str
    module: str
    amount: float


@router.put("/cell", summary="更新单元格（手动调整）")
async def update_cell(
    request: Request,
    body: CellUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    service = _get_service(request, db)
    data = await service.update_cell(body.employee_id, body.period, body.module, body.amount)
    await db.commit()
    return make_response(message="已更新", data=data, request=request)


# ==================== 加班费日历 ====================

@router.get("/overtime-days", summary="获取某月三薪日期")
async def get_overtime_days(
    request: Request,
    period: str = Query(..., description="账期 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss", "accountant"])
    service = _get_service(request, db)
    days = await service.get_overtime_days(period)
    return make_response(data=days, request=request)


class OvertimeDaysRequest(BaseModel):
    period: str
    days: dict  # {"2026-06-01": 3, "2026-06-02": 2}


@router.put("/overtime-days", summary="保存某月三薪日期")
async def set_overtime_days(
    request: Request,
    body: OvertimeDaysRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    service = _get_service(request, db)
    days = await service.set_overtime_days(body.period, body.days)
    await db.commit()
    return make_response(message="三薪日期已保存", data=days, request=request)
