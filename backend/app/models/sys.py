"""sys 模块 ORM 模型（配置/审计/打印机/路由规则）

依据 SPEC 2.0 §3.4.4
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SysConfig(Base):
    """系统配置表（sys_configs）"""
    __tablename__ = "sys_configs"
    __table_args__ = (
        UniqueConstraint('store_id', 'config_key', name='uq_sys_configs_store_key'),
    )

    config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """审计日志表（sys_audit_logs）"""
    __tablename__ = "sys_audit_logs"
    __table_args__ = {'extend_existing': True}

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Printer(Base):
    """打印机配置表（sys_printers）

    打印机类型：
    - label: 标签机（存酒标签、商品标签）
    - receipt: 小票机（收据、取酒小票）
    - order: 出单机（厨房/吧台出单）
    """
    __tablename__ = "sys_printers"

    printer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    printer_type: Mapped[str] = mapped_column(String(20), default="order")  # label/receipt/order
    brand: Mapped[Optional[str]] = mapped_column(String(50))
    device_sn: Mapped[Optional[str]] = mapped_column(String(100))
    api_url: Mapped[Optional[str]] = mapped_column(Text)
    api_key: Mapped[Optional[str]] = mapped_column(Text)
    api_user: Mapped[Optional[str]] = mapped_column(String(100))
    api_secret: Mapped[Optional[str]] = mapped_column(Text)
    paper_width: Mapped[int] = mapped_column(Integer, default=80)  # 纸宽mm
    online_status: Mapped[bool] = mapped_column(Boolean, default=False)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extra_config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PrintRoute(Base):
    """打印路由规则表（sys_print_routes）

    路由逻辑：
    1. 优先匹配自定义路由规则
    2. 其次使用分类绑定的打印机
    3. 最后按打印机类型自动路由
    """
    __tablename__ = "sys_print_routes"

    route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(50), default="order_created")  # order_created/payment_completed/manual
    document_type: Mapped[str] = mapped_column(String(50), default="order")  # order/receipt/label
    filter_type: Mapped[str] = mapped_column(String(50), default="category")  # category/product/order_type/all
    filter_value: Mapped[Optional[dict]] = mapped_column(JSONB)  # 匹配值
    printer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PrintQueue(Base):
    """打印任务队列表（sys_print_queue）

    用于故障转移和离线重试
    """
    __tablename__ = "sys_print_queue"

    queue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    route_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    printer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/printing/completed/failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
