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


class ModulePrintConfig(Base):
    """模块打印配置表（sys_module_print_configs）

    让老板自己选择哪些场景需要打印，哪些不需要。
    例如：有的店没有标签打印机，就不需要打印存酒标签。
    """
    __tablename__ = "sys_module_print_configs"

    config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False)  # 模块代码：wine_storage/pos/kitchen等
    scene_code: Mapped[str] = mapped_column(String(50), nullable=False)   # 场景代码：store_label/take_receipt/order_slip等
    scene_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 场景名称：存酒标签/取酒小票/厨房出单等
    description: Mapped[Optional[str]] = mapped_column(Text)              # 场景描述
    document_type: Mapped[str] = mapped_column(String(20), default="order")  # 文档类型：label/receipt/order
    trigger_event: Mapped[str] = mapped_column(String(50), default="order_created")  # 触发时机
    printer_type: Mapped[str] = mapped_column(String(20), default="order")  # 需要的打印机类型
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)          # 是否启用
    printer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))  # 指定打印机（可选）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
