"""
统一审批模型
涵盖：请假、补卡、调班、加班、报销
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "att_approvals"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("approval_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))

    type: Mapped[str] = mapped_column(String(20))  # leave / makeup / swap / expense
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected

    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)

    # 各类型自定义字段
    extra: Mapped[dict | None] = mapped_column(JSONB)

    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(Text)
