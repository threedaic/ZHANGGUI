"""
KPI 考核模块 Pydantic 模型
- 模板 (KPITemplate)
- 评分 (KPIScore)
- 结果 (KPIResult)
- 申诉 (KPIAppeal)
"""
import uuid
from pydantic import BaseModel, field_validator
from datetime import datetime


# ==================== KPI 模板 ====================

class KPITemplateResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID | None = None
    role: str
    dimension: str
    dimension_label: str
    weight: float
    formula_type: str = "ratio"
    formula_config: str = "{}"
    data_source: str
    is_active: bool

    model_config = {"from_attributes": True}


# ==================== KPI 评分 ====================

class KPIScoreCreate(BaseModel):
    employee_id: uuid.UUID
    period: str  # 2026-06
    dimension: str
    raw_value: float | None = None
    raw_description: str | None = None
    data_source: str | None = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}$", v):
            raise ValueError("period 格式必须为 YYYY-MM")
        return v


class KPIScoreResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    store_id: uuid.UUID
    period: str
    dimension: str
    raw_value: float | None = None
    raw_description: str | None = None
    normalized_score: float
    weight: float
    weighted_score: float
    data_source: str | None = None
    source_reference: str | None = None
    calculated_at: str | None = None

    model_config = {"from_attributes": True}


class KPIScoreBatchCreate(BaseModel):
    period: str
    scores: list[KPIScoreCreate]

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}$", v):
            raise ValueError("period 格式必须为 YYYY-MM")
        return v


# ==================== KPI 结果 ====================

class KPIResultResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    store_id: uuid.UUID
    period: str
    total_score: float
    coefficient: float
    coefficient_reason: str | None = None
    rank_in_store: int | None = None
    status: str
    confirmed_by: uuid.UUID | None = None
    confirmed_at: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class KPIResultDetail(KPIResultResponse):
    """含员工信息和各维度分项"""
    employee_name: str = ""
    employee_role: str = ""
    dimensions: list[KPIScoreResponse] = []


class KPIResultSummary(BaseModel):
    period: str
    store_avg: float
    store_count: int
    results: list[KPIResultDetail]


class KPICalculateRequest(BaseModel):
    employee_ids: list[uuid.UUID] | None = None  # None = 全员
    period: str

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}$", v):
            raise ValueError("period 格式必须为 YYYY-MM")
        return v


class KPIConfirmRequest(BaseModel):
    coefficient: float | None = None
    coefficient_reason: str | None = None


# ==================== KPI 申诉 ====================

class KPIAppealCreate(BaseModel):
    result_id: uuid.UUID
    dimension: str | None = None
    reason: str
    evidence: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("申诉原因不能为空")
        if len(v) > 500:
            raise ValueError("申诉原因不能超过500字")
        return v.strip()


class KPIAppealReview(BaseModel):
    action: str  # approved / rejected
    resolution: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("action 必须是 approved 或 rejected")
        return v


class KPIAppealResponse(BaseModel):
    id: uuid.UUID
    result_id: uuid.UUID
    employee_id: uuid.UUID
    dimension: str | None = None
    reason: str
    evidence: str | None = None
    status: str
    reviewed_by: uuid.UUID | None = None
    resolution: str | None = None
    resolved_at: str | None = None
    created_at: str | None = None
    # 关联信息
    employee_name: str = ""
    period: str = ""
    current_score: float = 0.0

    model_config = {"from_attributes": True}
