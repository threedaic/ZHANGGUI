"""
签收任务 Pydantic Schema
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SignTaskResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    employee_id: uuid.UUID
    type: str
    title: str
    ref_type: str
    ref_id: uuid.UUID
    status: str
    signed_at: datetime | None = None
    signature_data: str | None = None
    dispute_reason: str | None = None
    disputed_at: datetime | None = None
    issued_by: uuid.UUID
    issued_at: datetime
    notes: str | None = None
    extra: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # 展示用字段
    employee_name: str | None = None
    issued_by_name: str | None = None
    ref_data: dict | None = None  # 关联业务数据

    model_config = {"from_attributes": True}


class SignTaskDetailResponse(SignTaskResponse):
    """签收详情，包含完整签名数据和业务数据"""
    pass


class SignRequest(BaseModel):
    signature_data: str = Field(..., description="手写签名 base64 PNG")
    notes: str | None = Field(None, max_length=500)


class BatchSignRequest(BaseModel):
    task_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50, description="签收任务 ID 列表")
    signature_data: str = Field(..., description="手写签名 base64 PNG")
    notes: str | None = Field(None, max_length=500)


class DisputeRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="异议理由")


class RemindRequest(BaseModel):
    pass  # 无额外参数


class RevokeRequest(BaseModel):
    reason: str | None = Field(None, max_length=200, description="撤回原因")


class InboxQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: str | None = Field(None, pattern="^(pending|signed|disputed|revoked)$")
