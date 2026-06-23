"""
工资计算模块 Pydantic 模型（重构版）

公式: 实发 = 收入项合计 - 扣款项合计
工资项由 payroll_items_config 配置驱动，支持灵活扩展。
"""
import uuid
from pydantic import BaseModel, field_validator


# ==================== 工资记录 ====================

class PayrollRecordResponse(BaseModel):
    """工资记录响应（重构版：汇总金额 + 明细子表）"""
    id: uuid.UUID
    employee_id: uuid.UUID
    store_id: uuid.UUID
    period: str
    total_income: float = 0.0
    total_deduction: float = 0.0
    net_pay: float
    kpi_coefficient: float = 1.00
    status: str = "draft"
    generated_at: str | None = None
    finalized_at: str | None = None
    paid_at: str | None = None
    notes: str | None = None
    # 展示用关联字段
    employee_name: str = ""
    employee_role: str = ""

    model_config = {"from_attributes": True}


class PayrollRecordItemResponse(BaseModel):
    """工资明细项响应"""
    item_code: str
    item_name: str
    item_type: str  # income / deduction
    amount: float
    data_source: str
    sort_order: int
    detail: dict | None = None


class PayrollRecordDetail(PayrollRecordResponse):
    """工资记录详情，含明细项和数据源快照"""
    items: list[PayrollRecordItemResponse] = []
    snapshot: dict | None = None


# ==================== 生成/确认请求 ====================

class PayrollGenerateRequest(BaseModel):
    """触发工资生成"""
    period: str
    employee_ids: list[uuid.UUID] | None = None  # None = 全员

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}$", v):
            raise ValueError("period 格式必须为 YYYY-MM")
        return v


class PayrollFinalizeRequest(BaseModel):
    """确认工资条"""
    record_ids: list[uuid.UUID]
    notes: str | None = None


class PayrollMarkPaidRequest(BaseModel):
    """标记已发放"""
    record_ids: list[uuid.UUID]
    paid_at: str | None = None


# ==================== 月度汇总 ====================

class PayrollMonthlyItem(BaseModel):
    """月度工资汇总行（重构版）"""
    record_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    employee_role: str
    total_income: float = 0.0
    total_deduction: float = 0.0
    net_pay: float
    status: str


class PayrollMonthlySummary(BaseModel):
    """门店月度工资汇总（重构版）"""
    period: str
    store_id: uuid.UUID
    items: list[PayrollMonthlyItem]
    total_income: float = 0.0
    total_deduction: float = 0.0
    total_net_pay: float = 0.0
    status_summary: dict = {}
