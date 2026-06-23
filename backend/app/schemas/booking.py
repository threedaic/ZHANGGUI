"""订桌预约 Pydantic 模型。"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ==================== Table ====================

class TableCreate(BaseModel):
    area: str = Field(default="大厅", max_length=50)
    table_no: str = Field(..., max_length=10, description="桌号, 如 A1")
    capacity: int = Field(default=4, ge=1, le=20)


class TableUpdate(BaseModel):
    area: str | None = Field(default=None, max_length=50)
    table_no: str | None = Field(default=None, max_length=10)
    capacity: int | None = Field(default=None, ge=1, le=20)
    status: str | None = Field(default=None, pattern="^(idle|occupied|reserved)$")


class TableResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    area: str
    table_no: str
    capacity: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ==================== Booking ====================

class BookingCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    time_slot: str | None = Field(default=None, max_length=20, description="时段, 如 19:00-21:00")
    guests_count: int = Field(default=1, ge=1, le=50)
    table_id: uuid.UUID | None = Field(default=None, description="指定桌位ID, 不填则自动分配")
    notes: str | None = Field(default=None, max_length=500)


class BookingUpdate(BaseModel):
    time_slot: str | None = Field(default=None, max_length=20)
    guests_count: int | None = Field(default=None, ge=1, le=50)
    table_id: uuid.UUID | None = None
    status: str | None = Field(default=None, pattern="^(confirmed|cancelled|completed|no_show)$")
    notes: str | None = Field(default=None, max_length=500)


class BookingResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    customer_name: str
    phone: str | None = None
    date: str
    time_slot: str | None = None
    guests_count: int
    table_id: uuid.UUID | None = None
    table_no: str | None = None
    table_area: str | None = None
    source: str | None = None
    status: str
    notes: str | None
    created_by: uuid.UUID | None = None
    created_by_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("date", mode="before")
    @classmethod
    def date_to_str(cls, v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Stats ====================

class BookingStats(BaseModel):
    date: str
    total_tables: int = 0
    booked: int = 0
    free: int = 0
