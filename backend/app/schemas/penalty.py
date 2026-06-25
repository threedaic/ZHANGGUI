"""
奖惩通知 Pydantic Schema
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# 奖惩类型：penalty_ 前缀=惩罚，reward_ 前缀=奖励
NOTICE_TYPES = {
    # 惩罚（考勤类迟到/旷工/早退由考勤模块自动计算，不在此手动开具）
    "penalty_complaint": "服务投诉",
    "penalty_antifraud": "飞单处罚",
    "penalty_other": "严重违纪",
    # 奖励
    "reward_performance": "业绩奖励",
    "reward_overtime": "加班奖励",
    "reward_good_service": "服务奖励",
    "reward_other": "其他奖励",
}

# 兼容旧值
PENALTY_TYPES = NOTICE_TYPES


def is_reward(notice_type: str) -> bool:
    return notice_type.startswith("reward_")


class PenaltyCreateRequest(BaseModel):
    employee_id: uuid.UUID
    penalty_type: str = Field(..., description="奖惩类型")
    amount: float = Field(..., ge=0, description="金额")
    reason: str = Field(..., min_length=1, max_length=2000)


class PenaltyUpdateRequest(BaseModel):
    employee_id: uuid.UUID | None = None
    penalty_type: str | None = None
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
