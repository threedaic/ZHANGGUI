"""
工资申诉数据模型

wage_disputes: 员工对工资有异议时提交的申诉记录
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Numeric, DateTime, Text, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class WageDispute(TimestampMixin, Base):
    """工资申诉表：员工对工资有异议时提交"""

    __tablename__ = "wage_disputes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "dispute_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    wage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wage_records.wage_id"), comment="关联工资记录"
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"), comment="申诉员工"
    )
    period: Mapped[str] = mapped_column(String(7), comment="申诉的工资月份 YYYY-MM")
    dispute_type: Mapped[str] = mapped_column(
        String(20), comment="申诉类型：less/more/wrong_formula/other"
    )
    original_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), comment="原工资金额"
    )
    expected_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), comment="员工认为正确的金额"
    )
    reason: Mapped[str] = mapped_column(Text, comment="申诉原因")
    evidence: Mapped[dict | None] = mapped_column(JSONB, comment="证据（截图URL等）")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="状态：pending/confirmed/rejected/adjusted"
    )
    resolution: Mapped[str | None] = mapped_column(Text, comment="处理结果说明")
    adjusted_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), comment="调整金额"
    )
    adjusted_in_period: Mapped[str | None] = mapped_column(
        String(7), comment="在哪个月调整 YYYY-MM"
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"), comment="处理人"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
