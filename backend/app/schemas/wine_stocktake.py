"""
存酒盘点单 Pydantic 模型
"""
import uuid
from pydantic import BaseModel, field_validator
from datetime import datetime


class StocktakeItemResponse(BaseModel):
    """盘点明细响应"""
    id: uuid.UUID
    stocktake_id: uuid.UUID
    wine_id: uuid.UUID | None = None
    bottle_label: str
    customer_name: str
    phone: str
    wine_name: str
    expected_ml: int | None = None
    actual_ml: int | None = None
    check_status: str  # pending/matched/missing/mismatch
    checked_at: str | None = None
    checked_by: uuid.UUID | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("checked_at", mode="before")
    @classmethod
    def dt_to_str(cls, v):
        if v is None: return None
        if hasattr(v, "isoformat"): return v.isoformat()
        return str(v)


class StocktakeResponse(BaseModel):
    """盘点单响应"""
    id: uuid.UUID
    store_id: uuid.UUID
    period: str
    status: str  # pending/in_progress/completed
    assigned_to: str | None = None
    total_count: int
    checked_count: int
    matched_count: int
    missing_count: int
    extra_count: int
    started_at: str | None = None
    completed_at: str | None = None
    notes: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("started_at", "completed_at", "created_at", mode="before")
    @classmethod
    def dt_to_str(cls, v):
        if v is None: return None
        if hasattr(v, "isoformat"): return v.isoformat()
        return str(v)


class StocktakeScanRequest(BaseModel):
    """扫码核对请求"""
    bottle_label: str  # 扫码得到的瓶身码
    actual_ml: int | None = None  # 实际剩余量（可选，不填则不校验量）

    @field_validator("bottle_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("瓶身码不能为空")
        return v.strip()


class StocktakeScanResult(BaseModel):
    """扫码核对结果"""
    bottle_label: str
    check_status: str  # matched/missing/mismatch/extra
    wine_name: str | None = None
    customer_name: str | None = None
    expected_ml: int | None = None
    actual_ml: int | None = None
    message: str


class StocktakeCompleteRequest(BaseModel):
    """完成盘点请求"""
    notes: str | None = None


class StocktakeCreateRequest(BaseModel):
    """手动创建盘点单（测试用）"""
    period: str | None = None  # 不填则用当月
