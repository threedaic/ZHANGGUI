"""shared 模块 ORM 模型（门店/员工/会员/商品/桌台/设备/配置）

依据 SPEC 2.0 §3.4.1
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, Boolean, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# P2-2 修复：Store/Employee/StoreSetting 已迁移到独立模块，
# 这里直接 re-export 避免空壳类导致元数据冲突
from app.models.store import Store, StoreSettings  # noqa: F401, E402
from app.models.employee import Employee  # noqa: F401, E402
# 保持向后兼容的别名
StoreSetting = StoreSettings  # noqa: F401


class Franchisee(Base):
    """加盟商表（shared_franchisees）"""
    __tablename__ = "shared_franchisees"

    franchisee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(64))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32))
    brand_fee_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.05)
    contract_start: Mapped[Optional[date]] = mapped_column(Date)
    contract_end: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Member(Base, TimestampMixin):
    """会员表（shared_members）"""
    __tablename__ = "shared_members"

    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(64))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    openid: Mapped[Optional[str]] = mapped_column(String(255))
    wecom_user_id: Mapped[Optional[str]] = mapped_column(String(64))
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    growth: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(20), default="silver")
    total_consumption: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")


class MemberLevel(Base):
    """会员等级配置表（shared_member_levels）"""
    __tablename__ = "shared_member_levels"

    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    level_code: Mapped[str] = mapped_column(String(20), nullable=False)
    level_name: Mapped[str] = mapped_column(String(50), nullable=False)
    growth_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=1.00)
    benefits: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Category(Base):
    """商品分类表（shared_categories）"""
    __tablename__ = "shared_categories"

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    commission_rule: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    # 打印机绑定（简单模式）
    printer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))  # 出单打印机
    backup_printer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))  # 备用打印机


class Product(Base, TimestampMixin):
    """商品表（shared_products）"""
    __tablename__ = "shared_products"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_categories.category_id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(32))
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(16), default="杯")
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    stock: Mapped[Optional[int]] = mapped_column(Integer)
    stock_warn: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# Table 已迁移到 booking.py，这里 re-export 避免元数据冲突
from app.models.booking import Table  # noqa: F401, E402


class Device(Base):
    """设备注册表（shared_devices）"""
    __tablename__ = "shared_devices"

    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)
    device_sn: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_tables.table_id"))
    status: Mapped[str] = mapped_column(String(20), default="online")
    firmware_version: Mapped[Optional[str]] = mapped_column(String(20))
    last_seen: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# StoreSetting 已 re-export 为 StoreSettings 的别名（见文件顶部）
