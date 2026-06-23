"""
智能管家模块 Pydantic 模型
- 清单模板 CRUD
- 会话管理
- 检查项结果
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


# ==================== 清单模板 ====================

class ChecklistTemplateCreate(BaseModel):
    name: str
    session_type: str           # opening / closing
    role_tag: str = "all"       # store_manager / bartender / server / all
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("模板名称不能为空")
        return v.strip()

    @field_validator("session_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"opening", "closing"}:
            raise ValueError("类型必须为 opening 或 closing")
        return v


class ChecklistTemplateUpdate(BaseModel):
    name: str | None = None
    role_tag: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ChecklistTemplateResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    session_type: str
    role_tag: str
    sort_order: int
    is_active: bool
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    items: list["ChecklistItemResponse"] = []

    model_config = {"from_attributes": True}


# ==================== 清单项 ====================

class ChecklistItemRequest(BaseModel):
    id: uuid.UUID | None = None       # 更新时传 id，新建时 None
    item_name: str
    item_type: str = "checkbox"  # checkbox / photo
    required_photo: bool = False
    sort_order: int = 0
    ai_prompt: str | None = None  # AI 判定提示词（仅 photo 类型有效）

    @field_validator("item_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("检查项名称不能为空")
        return v.strip()

    @field_validator("item_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"checkbox", "photo"}:
            raise ValueError("验证方式必须为 checkbox 或 photo")
        return v


class ChecklistItemsBatchRequest(BaseModel):
    """批量保存模板的清单项（全量替换）"""
    items: list[ChecklistItemRequest]


class ChecklistItemResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    item_name: str
    item_type: str
    required_photo: bool
    sort_order: int
    ai_prompt: str | None = None

    model_config = {"from_attributes": True}


# ==================== 会话 ====================

class SessionStartRequest(BaseModel):
    session_type: str           # opening / closing

    @field_validator("session_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"opening", "closing"}:
            raise ValueError("类型必须为 opening 或 closing")
        return v


class SessionResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    session_type: str
    operator_user_id: uuid.UUID
    status: str
    started_at: datetime | str | None = None
    completed_at: datetime | str | None = None
    total_items: int
    completed_items: int
    templates: list[ChecklistTemplateResponse] = []
    results: list["ItemResultResponse"] = []

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    session_type: str
    status: str
    started_at: datetime | str | None = None
    completed_at: datetime | str | None = None
    total_items: int
    completed_items: int

    model_config = {"from_attributes": True}


# ==================== 检查项结果 ====================

class ItemConfirmRequest(BaseModel):
    """打勾确认请求"""
    comment: str | None = None


class AdHocItemRequest(BaseModel):
    """临时加项请求"""
    item_name: str
    item_type: str = "checkbox"

    @field_validator("item_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("检查项名称不能为空")
        return v.strip()

    @field_validator("item_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"checkbox", "photo"}:
            raise ValueError("验证方式必须为 checkbox 或 photo")
        return v


class ItemResultResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    template_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    item_name: str | None = None
    item_type: str | None = None
    completed_by: uuid.UUID | None = None
    photo_url: str | None = None
    ai_result: dict | None = None
    review_status: str
    review_user_id: uuid.UUID | None = None
    review_comment: str | None = None
    completed_at: datetime | str | None = None

    model_config = {"from_attributes": True}


class ManualReviewRequest(BaseModel):
    """人工复核请求"""
    action: str  # pass / reject
    comment: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in {"pass", "reject"}:
            raise ValueError("action 必须为 pass 或 reject")
        return v


# ==================== 看板 ====================

class StoreClosingStatus(BaseModel):
    store_id: uuid.UUID
    store_name: str
    has_active_session: bool
    session_type: str | None = None
    session_id: uuid.UUID | None = None
    session_status: str | None = None
    total_items: int = 0
    completed_items: int = 0
    started_at: str | None = None
