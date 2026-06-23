"""
处罚通知 Pydantic Schema
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


PENALTY_TYPES = {
    "late_fine": "迟到罚款",
    "absent_fine": "旷工罚款",
    "early_fine": "早退罚款",
    "complaint": "服务投诉",
    "antifraud": "飞单处罚",
    "other": "其他违规",
}


class PenaltyCreateRequest(BaseModel):
    employee_id: uuid.UUID
    penalty_type: str = Field(..., pattern="^(late_fine|absent_fine|early_fine|complaint|antifraud|other)$")
    amount: float = Field(..., ge=0, description="罚款金额")
    reason: str = Field(..., min_length=1, max_length=2000)


class PenaltyUpdateRequest(BaseModel):
    employee_id: uuid.UUID | None = None
    penalty_type: str | None = Field(None, pattern="^(late_fine|absent_fine|early_fine|complaint|antifraud|other)$")
    amount: float | None = Field(None, ge=0)
    reason: str | None = Field(None, min_length=1, max_length=2000)


class PenaltyResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    employee_id: uuid.UUID
    penalty_type: str
    amount: float
    reason: str
    issued_by: uuid.UUID
    issued_at: datetime
    status: str
    extra: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # 展示用
    employee_name: str | None = None
    issued_by_name: str | None = None
    penalty_type_name: str | None = None
    sign_task_id: uuid.UUID | None = None
    sign_task_status: str | None = None

    model_config = {"from_attributes": True}


class PenaltyListQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    penalty_type: str | None = None
    status: str | None = None
    employee_id: uuid.UUID | None = None
