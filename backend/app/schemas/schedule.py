"""
排班管理 Pydantic 模型

请求/响应校验，所有字段不可随意扩缩。
"""
import uuid
from datetime import date as _date
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ---- 常量 ----
SHIFT_TYPES = ["白班", "晚班", "休息"]
MAX_HEADCOUNT_PER_SHIFT = 15


# ---- 请求 ----

class ScheduleCreate(BaseModel):
    employee_id: uuid.UUID = Field(..., description="员工 ID")
    date: _date = Field(..., description="排班日期")
    shift_type: str = Field(..., description="班次类型: 白班/晚班/休息")
    note: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator("shift_type")
    @classmethod
    def validate_shift(cls, v: str) -> str:
        if v not in SHIFT_TYPES:
            raise ValueError(f"班次类型必须为 {SHIFT_TYPES} 之一，当前值: {v}")
        return v


class ScheduleBatchCreate(BaseModel):
    schedules: list[ScheduleCreate] = Field(..., description="批量排班列表")


class ScheduleUpdate(BaseModel):
    shift_type: Optional[str] = Field(None, description="班次类型")
    note: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator("shift_type")
    @classmethod
    def validate_shift(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SHIFT_TYPES:
            raise ValueError(f"班次类型必须为 {SHIFT_TYPES} 之一，当前值: {v}")
        return v


# ---- 响应 ----

class ScheduleResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str = ""
    date: _date
    shift_type: str
    note: Optional[str] = None
    version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ScheduleStatsItem(BaseModel):
    date: _date
    total_scheduled: int
    day_shift_count: int = Field(..., alias="day_count")
    night_shift_count: int = Field(..., alias="night_count")
    rest_count: int

    model_config = {"from_attributes": True}


class EmployeeBrief(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}
