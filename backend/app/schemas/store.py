"""门店配置 Pydantic Schema"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any


class StoreSettingsUpdate(BaseModel):
    """PUT /api/v1/stores/settings 请求体"""
    rest_days_per_month: Optional[int] = Field(None, ge=0, le=10)
    rest_allowed_weekdays: Optional[str] = None
    rest_forbidden_weekdays: Optional[str] = None
    max_same_position_off: Optional[int] = Field(None, ge=0, le=10)
    min_position_coverage_percent: Optional[int] = Field(None, ge=0, le=100)
    manager_order_constraint: Optional[bool] = None
    holiday_policy: Optional[str] = None
    auto_schedule_enabled: Optional[bool] = None
    schedule_lock_after_publish: Optional[bool] = None
    payroll_day_of_month: Optional[int] = Field(None, ge=1, le=28)
    kpi_coefficient_min: Optional[float] = Field(None, ge=0, le=1)
    kpi_coefficient_max: Optional[float] = Field(None, ge=1, le=5)
    contract_initiator_ids: Optional[str] = None
    contract_company_name: Optional[str] = None
    contract_company_phone: Optional[str] = None
    contract_company_address: Optional[str] = None
    contract_base_salary: Optional[float] = Field(None, ge=0)
    contract_probation_months: Optional[int] = Field(None, ge=0, le=12)
    contract_notice_days: Optional[int] = Field(None, ge=0, le=90)
    contract_duration_years: Optional[int] = Field(None, ge=1, le=10)
    ai_api_url: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = Field(None, ge=0, le=2)
    printer_enabled: Optional[bool] = None
    label_printer_enabled: Optional[bool] = None
    receipt_printer_enabled: Optional[bool] = None
    printer_brand: Optional[str] = None
    printer_api_url: Optional[str] = None
    printer_sn: Optional[str] = None
    printer_user: Optional[str] = None
    printer_ukey: Optional[str] = None
    printer_label_width: Optional[int] = Field(None, ge=20, le=200)
    printer_label_height: Optional[int] = Field(None, ge=10, le=200)
    wecom_bot_enabled: Optional[bool] = None
    wecom_webhook_url: Optional[str] = None
    # 扩展配置：订桌规则/评分码/存酒配置/防飞单规则等，平铺字段放不下的业务配置
    extra_config: Optional[Dict[str, Any]] = None


class WeworkConfigUpdate(BaseModel):
    """PUT /api/v1/stores/wework 请求体"""
    wework_corp_id: Optional[str] = None
    wework_agent_id: Optional[int] = None
    wework_secret: Optional[str] = None
    wework_token: Optional[str] = None
    wework_aes_key: Optional[str] = None
    wework_department_id: Optional[int] = None
    wework_externalpay_secret: Optional[str] = None


class EmployeeRoleUpdate(BaseModel):
    """PUT /api/v1/stores/employees/{id}/role 请求体"""
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        valid = {"boss", "store_manager", "accountant", "bar_manager", "service_manager", "kitchen_manager", "staff"}
        if v not in valid:
            raise ValueError(f"无效角色: {v}")
        return v
