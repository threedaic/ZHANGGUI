"""
存酒盘点单模型
每月1号自动生成，会计扫码逐瓶核对。
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class WineStocktake(TimestampMixin, Base):
    """盘点单主表：每月一张"""
    __tablename__ = "wine_stocktakes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "stocktake_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM 盘点月份
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending=待盘点 / in_progress=盘点中 / completed=已完成
    assigned_to: Mapped[str | None] = mapped_column(String(50))  # 盘点人（会计）
    total_count: Mapped[int] = mapped_column(Integer, default=0)  # 应盘数量（生成时的在库瓶数）
    checked_count: Mapped[int] = mapped_column(Integer, default=0)  # 已核对数量
    matched_count: Mapped[int] = mapped_column(Integer, default=0)  # 匹配数量
    missing_count: Mapped[int] = mapped_column(Integer, default=0)  # 缺失数量（扫码时不在库）
    extra_count: Mapped[int] = mapped_column(Integer, default=0)  # 多出数量（扫码时不在盘点单上）
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class WineStocktakeItem(TimestampMixin, Base):
    """盘点明细：每瓶酒一条记录"""
    __tablename__ = "wine_stocktake_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "item_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    stocktake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wine_stocktakes.stocktake_id")
    )
    wine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wine_stored_bottles.wine_id")
    )
    bottle_label: Mapped[str] = mapped_column(String(50))  # 瓶身码
    customer_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    wine_name: Mapped[str] = mapped_column(String(100))
    expected_ml: Mapped[int | None] = mapped_column(Integer)  # 应剩余量
    actual_ml: Mapped[int | None] = mapped_column(Integer)  # 实际剩余量（扫码时填）
    check_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending=待核对 / matched=匹配 / missing=缺失 / mismatch=量不符
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id")
    )
    notes: Mapped[str | None] = mapped_column(Text)
