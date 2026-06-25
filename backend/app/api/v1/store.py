"""门店配置 API 路由。

前缀: /api/v1/store (由 main.py 提供)

端点:
  GET  ""              → 获取当前门店基本信息
  GET  "/settings"     → 获取当前门店完整设置
  PUT  "/settings"     → 更新门店设置
  PUT  "/wework"       → 更新企微配置
  POST   "/wework/sync-contacts"      → 同步企微通讯录，仅boss
  GET  "/employees"    → 获取门店员工列表
  PUT  "/employees/{id}/role" → 更新员工角色
"""

import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models.store import Store, StoreSettings
from app.models.employee import Employee
from app.utils.deps import get_store_id, require_role, make_response
from app.utils.exceptions import NotFoundError, ValidationError
from app.schemas.store import StoreSettingsUpdate, WeworkConfigUpdate, EmployeeRoleUpdate

router = APIRouter()


@router.get("")
async def get_store_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取当前门店基本信息。"""
    store_id = get_store_id(request)
    stmt = select(Store).where(Store.id == store_id)
    result = await db.execute(stmt)
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("门店不存在")

    settings = get_settings()
    return make_response(data={
        "id": store.id,
        "name": store.name,
        "store_code": store.store_code,
        "address": store.address,
        "city": store.city,
        "status": store.status,
        "daily_booking_limit": store.daily_booking_limit,
        "wework_status": store.wework_status,
        "wework_corp_id": store.wework_corp_id,
        "wework_agent_id": store.wework_agent_id,
        "wework_department_id": store.wework_department_id,
        "wework_externalpay_secret": "已配置" if store.wework_externalpay_secret else None,
        "frontend_base_url": settings.FRONTEND_BASE_URL,
    }, request=request)


@router.get("/settings")
async def get_store_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取当前门店的排班/考勤/合同/打印机等完整设置。"""
    store_id = get_store_id(request)
    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        return make_response(data={}, request=request)

    return make_response(data={
        "rest_days_per_month": settings.rest_days_per_month,
        "rest_allowed_weekdays": settings.rest_allowed_weekdays,
        "rest_forbidden_weekdays": settings.rest_forbidden_weekdays,
        "max_same_position_off": settings.max_same_position_off,
        "min_position_coverage_percent": settings.min_position_coverage_percent,
        "manager_order_constraint": settings.manager_order_constraint,
        "holiday_policy": settings.holiday_policy,
        "auto_schedule_enabled": settings.auto_schedule_enabled,
        "schedule_lock_after_publish": settings.schedule_lock_after_publish,
        "payroll_day_of_month": settings.payroll_day_of_month,
        "kpi_coefficient_min": settings.kpi_coefficient_min,
        "kpi_coefficient_max": settings.kpi_coefficient_max,
        "contract_initiator_ids": settings.contract_initiator_ids,
        "contract_company_name": settings.contract_company_name,
        "contract_company_phone": settings.contract_company_phone,
        "contract_company_address": settings.contract_company_address,
        "contract_base_salary": settings.contract_base_salary,
        "contract_probation_months": settings.contract_probation_months,
        "contract_notice_days": settings.contract_notice_days,
        "contract_duration_years": settings.contract_duration_years,
        "ai_api_url": settings.ai_api_url,
        "ai_api_key": settings.ai_api_key,
        "ai_model": settings.ai_model,
        "ai_temperature": settings.ai_temperature,
        "printer_enabled": settings.printer_enabled,
        "label_printer_enabled": settings.label_printer_enabled,
        "receipt_printer_enabled": settings.receipt_printer_enabled,
        "printer_brand": settings.printer_brand,
        "printer_api_url": settings.printer_api_url,
        "printer_sn": settings.printer_sn,
        "printer_user": settings.printer_user,
        "printer_ukey": settings.printer_ukey,
        "printer_label_width": settings.printer_label_width,
        "printer_label_height": settings.printer_label_height,
        "wecom_bot_enabled": settings.wecom_bot_enabled,
        "wecom_webhook_url": settings.wecom_webhook_url,
        "extra_config": settings.extra_config or {},
    }, request=request)


@router.put("/settings")
async def update_store_settings(
    body: StoreSettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新门店排班/考勤设置。"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    body_dict = body.model_dump(exclude_unset=True, exclude_none=True)

    # extra_config 深合并：保留未传入的子配置，避免覆盖其他模块配置
    new_extra = body_dict.pop("extra_config", None)

    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = StoreSettings(store_id=store_id)
        db.add(settings)

    for key, value in body_dict.items():
        setattr(settings, key, value)

    if new_extra:
        merged = dict(settings.extra_config or {})
        for k, v in new_extra.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        settings.extra_config = merged

    await db.commit()
    await db.refresh(settings)

    return make_response(message="门店设置已更新", data=None, request=request)


@router.put("/wework")
async def update_wework_config(
    body: WeworkConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新企微配置字段。仅老板可操作。"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)

    body_dict = body.model_dump(exclude_unset=True, exclude_none=True)
    stmt = select(Store).where(Store.id == store_id)
    result = await db.execute(stmt)
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundError("门店不存在")

    wework_fields = {"wework_corp_id", "wework_agent_id", "wework_secret", "wework_token", "wework_aes_key", "wework_department_id", "wework_externalpay_secret"}
    for key, value in body_dict.items():
        if key in wework_fields:
            # AES 加密 secret 字段
            if key in ("wework_secret", "wework_externalpay_secret") and value:
                from app.utils.security import encrypt_aes
                value = encrypt_aes(value)
            # 部门 ID 允许传空字符串清空配置
            if key == "wework_department_id":
                if value == "" or value is None:
                    value = None
                elif isinstance(value, str):
                    value = int(value)
            setattr(store, key, value)

    await db.commit()
    return make_response(message="企微配置已更新", data=None, request=request)


@router.post("/wework/sync-contacts")
async def sync_wework_contacts(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """从企微通讯录同步员工到本地 employees 表。仅老板可操作。"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)

    from app.services.wework import sync_contacts
    result = await sync_contacts(db, store_id)
    return make_response(message="通讯录同步完成", data=result, request=request)


ROLE_OPTIONS = ["boss", "store_manager", "accountant", "bar_manager", "service_manager", "kitchen_manager", "staff"]


@router.get("/employees")
async def list_employees(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取当前门店所有员工列表。"""
    store_id = get_store_id(request)
    stmt = select(Employee).where(Employee.store_id == store_id).order_by(Employee.id)
    result = await db.execute(stmt)
    employees = result.scalars().all()

    return make_response(data=[
        {
            "id": e.id,
            "name": e.name,
            "role": e.role,
            "wework_userid": e.wework_userid,
            "status": e.status,
            "phone": e.phone,
        }
        for e in employees
    ], request=request)


@router.put("/employees/{employee_id}/role")
async def update_employee_role(
    employee_id: uuid.UUID,
    body: EmployeeRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新员工角色。仅老板可操作。"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    new_role = body.role

    if new_role not in {"boss", "store_manager", "accountant", "bar_manager", "service_manager", "kitchen_manager", "staff"}:
        raise ValidationError(f"无效角色: {new_role}")

    stmt = select(Employee).where(Employee.id == employee_id, Employee.store_id == store_id)
    result = await db.execute(stmt)
    emp = result.scalar_one_or_none()
    if not emp:
        raise NotFoundError("员工不存在")

    old_role = emp.role
    emp.role = new_role
    await db.commit()

    # 同步更新关联的 User 记录角色
    from app.models.user import User
    user_result = await db.execute(select(User).where(User.employee_id == employee_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.role = new_role
        await db.commit()

    return make_response(message=f"{emp.name} 角色已从 {old_role} 更新为 {new_role}",
        data={"id": emp.id, "name": emp.name, "role": new_role}, request=request)
