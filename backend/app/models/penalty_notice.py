"""
处罚通知单业务模型 — 独立于签收任务

处罚类型: penalty_complaint / penalty_antifraud / penalty_other （考勤类迟到/旷工/早退由考勤模块自动计算）
状态: draft → issued → acknowledged
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class PenaltyNotice(TimestampMixin, Base):
    __tablename__ = "hr_penalty_notices"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("penalty_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))

    penalty_type: Mapped[str] = mapped_column(String(30))  # penalty_complaint / penalty_antifraud / penalty_other
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reason: Mapped[str] = mapped_column(Text)

    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / issued / acknowledged
    extra: Mapped[dict | None] = mapped_column(JSONB)
