"""
统一审批 Pydantic 模型
"""
import uuid
from pydantic import BaseModel, field_validator


class ApprovalCreateRequest(BaseModel):
    type: str  # leave / makeup / swap / expense
    start_date: str | None = None
    end_date: str | None = None
    reason: str
    extra: dict | None = None
    approver_id: uuid.UUID | None = None  # 指定审批人（可选）

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("leave", "makeup", "swap", "expense"):
            raise ValueError("审批类型必须是 leave/makeup/swap/expense")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("原因不能为空")
        return v.strip()


class ApprovalReviewRequest(BaseModel):
    action: str  # approved / rejected
    reason: str | None = None  # 驳回原因

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("action 必须是 approved 或 rejected")
        return v


class ApprovalItemResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str = ""
    type: str
    type_label: str = ""
    status: str
    start_date: str | None = None
    end_date: str | None = None
    reason: str | None = None
    extra: dict | None = None
    approver_id: uuid.UUID | None = None
    approver_name: str | None = None
    reject_reason: str | None = None
    created_at: str | None = None
