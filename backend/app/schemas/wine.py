"""
存酒管理模块 Pydantic 模型
- 存酒 (WineCreate / WineResponse)
- 取酒（服务员）(WineStaffRetrieve)
- 取酒（客人自助）(WineSelfRetrieve)
- 盘点 (InventorySummary / InventoryCheckItem)
"""
import uuid
from pydantic import BaseModel, field_validator


# ==================== 存酒 ====================

class WineCreate(BaseModel):
    customer_name: str
    phone: str
    wine_name: str
    remaining_ml: int  # 750(满) / 562(3/4) / 375(1/2) / 187(1/4)
    quantity: int = 1  # 瓶数，默认 1
    cabinet_no: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 1 or v > 99:
            raise ValueError("瓶数必须为 1~99")
        return v

    @field_validator("customer_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("客人姓名不能为空")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^1[3-9]\d{9}$", v.strip()):
            raise ValueError("手机号格式不正确")
        return v.strip()

    @field_validator("wine_name")
    @classmethod
    def validate_wine_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("酒名不能为空")
        return v.strip()

    @field_validator("remaining_ml")
    @classmethod
    def validate_remaining_ml(cls, v: int) -> int:
        if v not in {750, 562, 375, 187}:
            raise ValueError("容量必须为 750/562/375/187")
        return v


class WineBatchItem(BaseModel):
    """单种酒条目"""
    wine_name: str
    remaining_ml: int  # 750/562/375/187
    quantity: int = 1

    @field_validator("wine_name")
    @classmethod
    def validate_wn(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("酒名不能为空")
        return v.strip()

    @field_validator("remaining_ml")
    @classmethod
    def validate_rml(cls, v: int) -> int:
        if v not in {750, 562, 375, 187}:
            raise ValueError("容量必须为 750/562/375/187")
        return v


class WineBatchCreate(BaseModel):
    """客人一次存多种酒"""
    customer_name: str
    phone: str
    wines: list[WineBatchItem]
    notes: str | None = None

    @field_validator("customer_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("客人姓名不能为空")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^1[3-9]\d{9}$", v.strip()):
            raise ValueError("手机号格式不正确")
        return v.strip()


# ==================== 取酒 ====================

class WineStaffRetrieve(BaseModel):
    """服务员取酒请求"""
    bottle_label: str
    retrieve_ml: int  # 取出量 ml
    table_no: str | None = None

    @field_validator("bottle_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("瓶身码不能为空")
        return v.strip()

    @field_validator("retrieve_ml")
    @classmethod
    def validate_retrieve_ml(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("取酒量必须大于 0")
        return v


class WineSelfRetrieve(BaseModel):
    """客人自助取酒请求（H5 提交）"""
    bottle_label: str   # URL 自带
    retrieve_ml: int     # 取出量 ml
    table_no: str | None = None

    @field_validator("bottle_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("瓶身码不能为空")
        return v.strip()

    @field_validator("retrieve_ml")
    @classmethod
    def validate_retrieve_ml(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("取酒量必须大于 0")
        return v


class WineRetrieveResponse(BaseModel):
    id: uuid.UUID
    bottle_label: str | None = None
    status: str
    remaining_ml: int | None = None
    retrieved_at: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("retrieved_at", mode="before")
    @classmethod
    def dt_to_str(cls, v):
        if v is None: return None
        if hasattr(v, "isoformat"): return v.isoformat()
        return str(v)


# ==================== H5 ====================

class WineH5Info(BaseModel):
    """顾客扫短信链接 H5 页面展示的信息"""
    bottle_label: str
    wine_name: str
    date_stored: str
    initial_ml: int | None = None
    remaining_ml: int | None = None
    status: str

    model_config = {"from_attributes": True}

    @field_validator("date_stored", mode="before")
    @classmethod
    def date_to_str(cls, v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)


class WineH5ConfirmRequest(BaseModel):
    """客人自助取酒提交"""
    bottle_label: str
    retrieve_ml: int
    table_no: str | None = None

    @field_validator("bottle_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("瓶身码不能为空")
        return v.strip()

    @field_validator("retrieve_ml")
    @classmethod
    def validate_retrieve_ml(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("取酒量必须大于 0")
        return v


# ==================== 响应 ====================

class WineResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    customer_name: str
    phone: str
    wine_name: str
    bottle_label: str | None = None
    date_stored: str
    initial_ml: int | None = None
    remaining_ml: int | None = None
    cabinet_no: str | None = None
    table_no: str | None = None
    status: str
    expiry_date: str | None = None
    retrieved_at: str | None = None
    retrieved_by: uuid.UUID | None = None
    retriever_name: str | None = None
    retriever_employee_code: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at", "retrieved_at", "date_stored", "expiry_date", mode="before")
    @classmethod
    def datetime_to_str(cls, v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)


# ==================== 盘点 ====================

class InventorySummary(BaseModel):
    total: int
    stored: int
    retrieved: int


class InventoryCheckItem(BaseModel):
    bottle_label: str | None = None
    customer_name: str
    wine_name: str
    remaining_ml: int | None = None
    status: str


# ==================== 列表查询 ====================

class WineListQuery(BaseModel):
    status: str | None = None      # stored / retrieved
    keyword: str | None = None     # 搜索姓名/手机号/酒名
    page: int = 1
    page_size: int = 20
