"""
企微收款同步数据模型

wage_wework_payments: 企微个人收款同步记录表

业绩闭环:
  1. 订桌系统识别员工 (pos_table_sessions.commission_employee_id)
  2. 企微收款 API 拉取个人收款 → 写入 wage_wework_payments
  3. 汇总到员工月度业绩（按员工×月份×wework_payment类型）
  4. KPI 和工资计算从月度业绩取数

设计要点:
  - 每笔企微收款一条记录，支持去重（transaction_id 唯一）
  - 关联订桌订单（table_session_id），形成"订桌→收款→提成"闭环
  - 同步状态追踪（synced/failed），便于重试
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Numeric, DateTime, ForeignKey, UniqueConstraint, Text, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class WeworkPaymentSync(TimestampMixin, Base):
    """企微个人收款同步记录

    每笔企微收款一条记录，transaction_id 全局唯一防重。
    通过 table_session_id 关联订桌订单，形成业绩闭环。
    """

    __tablename__ = "wage_wework_payments"
    __table_args__ = (
        UniqueConstraint("store_id", "transaction_id", name="uq_wework_pay_store_txn"),
        {'extend_existing': True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "payment_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE")
    )
    transaction_id: Mapped[str] = mapped_column(String(100))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"), nullable=True
    )
    table_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_table_sessions.session_id"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    pay_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payer_account: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="synced")
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
