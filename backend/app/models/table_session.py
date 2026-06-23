"""
桌台会话数据模型

pos_table_sessions: 桌台消费会话（开台到结账的完整周期）

业绩闭环关键表:
  - commission_employee_id: 识别提成分配员工
  - wework_pay_amount: 企微收款金额（业绩闭环数据源）
  - commission_amount: 计算后的提成金额

字段类型规范:
  - 金额: Numeric(12,2)
  - 时间: DateTime(timezone=True)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class TableSession(TimestampMixin, Base):
    __tablename__ = "pos_table_sessions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "session_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_tables.table_id")
    )
    table_no: Mapped[str] = mapped_column(String(16))
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_orders.order_id")
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    guest_count: Mapped[int] = mapped_column(Integer, default=1)
    crmeb_order_count: Mapped[int] = mapped_column(Integer, default=0)
    crmeb_total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    wework_pay_count: Mapped[int] = mapped_column(Integer, default=0)
    wework_pay_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    commission_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    commission_base: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    notes: Mapped[str | None] = mapped_column(Text)
