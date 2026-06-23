"""
桌面评分码 Pydantic 模型
"""
import uuid
from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    """客人扫码提交评分（无需登录）"""
    store_id: uuid.UUID
    table_no: str = Field(..., min_length=1, max_length=10)
    food_quality: int = Field(..., ge=1, le=5)
    food_speed: int = Field(..., ge=1, le=5)
    drink_quality: int = Field(..., ge=1, le=5)
    drink_speed: int = Field(..., ge=1, le=5)
    service_attitude: int = Field(..., ge=1, le=5)
    service_speed: int = Field(..., ge=1, le=5)
    cleanliness: int = Field(..., ge=1, le=5)
    comment: str | None = None
    source: str = "qr_code"


class RatingItem(BaseModel):
    """评分记录列表项"""
    id: uuid.UUID
    store_id: uuid.UUID
    table_no: str
    food_quality: int | None
    food_speed: int | None
    drink_quality: int | None
    drink_speed: int | None
    service_attitude: int | None
    service_speed: int | None
    cleanliness: int | None
    overall_score: float
    comment: str | None
    is_low_score: bool
    notified: bool
    store_response: str | None
    created_at: str

    model_config = {"from_attributes": True}


class RatingSummary(BaseModel):
    """评分汇总统计"""
    total_count: int
    avg_overall: float
    low_score_count: int
    dimension_scores: dict[str, float]


class RatingAlert(BaseModel):
    """低分告警记录"""
    id: uuid.UUID
    table_no: str
    overall_score: float
    comment: str | None
    notified: bool
    created_at: str
    store_response: str | None
    food_quality: int | None = None
    food_speed: int | None = None
    drink_quality: int | None = None
    drink_speed: int | None = None
    service_attitude: int | None = None
    service_speed: int | None = None
    cleanliness: int | None = None

    model_config = {"from_attributes": True}
