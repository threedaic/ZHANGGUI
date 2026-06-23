"""
合同系统 Pydantic 模型

请求/响应校验。
"""
import uuid
from datetime import date as _date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ---- 常量 ----
VALID_POSITIONS = ["店长", "吧员", "服务员", "厨师", "保洁"]
VALID_GRADES = ["学徒", "正式", "副职", "正职"]
VALID_STATUSES = ["draft", "pending_sign", "signed", "expired", "terminated"]


# ---- 薪资矩阵 ----

class SalaryMatrixResponse(BaseModel):
    id: uuid.UUID
    position: str
    grade: str
    monthly_salary: float
    base_salary: float
    meal_allowance: float
    is_active: bool

    model_config = {"from_attributes": True}


class SalaryMatrixUpdate(BaseModel):
    monthly_salary: Optional[float] = Field(None, ge=0, description="月薪总额")
    is_active: Optional[bool] = Field(None, description="是否启用")

    @field_validator("monthly_salary")
    @classmethod
    def validate_salary(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 3000:
            raise ValueError("月薪不得低于基本工资 3000 元")
        return v


# ---- 合同 ----

class ContractCreate(BaseModel):
    employee_id: uuid.UUID = Field(..., description="员工 ID")
    position: str = Field(..., description="岗位")
    grade: str = Field(..., description="职档")
    monthly_salary: float = Field(..., ge=3000, description="月薪总额（>= 3000）")
    start_date: _date = Field(..., description="合同开始日期")
    end_date: Optional[_date] = Field(None, description="合同结束日期")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        if v not in VALID_POSITIONS:
            raise ValueError(f"岗位必须为 {VALID_POSITIONS} 之一，当前值: {v}")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: str) -> str:
        if v not in VALID_GRADES:
            raise ValueError(f"职档必须为 {VALID_GRADES} 之一，当前值: {v}")
        return v

    @field_validator("monthly_salary")
    @classmethod
    def validate_monthly_salary(cls, v: float) -> float:
        if v < 3000:
            raise ValueError("月薪不得低于基本工资 3000 元")
        return v


class ContractUpdate(BaseModel):
    position: Optional[str] = None
    grade: Optional[str] = None
    monthly_salary: Optional[float] = Field(None, ge=3000)
    start_date: Optional[_date] = None
    end_date: Optional[_date] = None
    status: Optional[str] = None

    @field_validator("position")
    @classmethod
    def check_position(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_POSITIONS:
            raise ValueError(f"岗位必须为 {VALID_POSITIONS} 之一")
        return v

    @field_validator("grade")
    @classmethod
    def check_grade(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_GRADES:
            raise ValueError(f"职档必须为 {VALID_GRADES} 之一")
        return v

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"状态必须为 {VALID_STATUSES} 之一")
        return v


class SendSignRequest(BaseModel):
    """发起电子签请求"""
    pass  # 参数由后端从合同记录中自动提取


class ContractResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str = ""
    contract_no: str
    position: str
    grade: str
    monthly_salary: float
    base_salary: float
    meal_allowance: float
    allowance: float
    start_date: str
    end_date: Optional[str] = None
    status: str
    esign_flow_id: Optional[str] = None
    signed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ContractDetailResponse(ContractResponse):
    template_data: Optional[dict] = None

    model_config = {"from_attributes": True}


class ContractListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: Optional[str] = None
    employee_id: Optional[uuid.UUID] = None
    position: Optional[str] = None
