"""排班模型（已迁移到 SPEC 2.0 新表）

Schedule → att_schedules
ScheduleSnapshot → att_schedule_snapshots
ScheduleRule → att_schedule_rules
ShiftSwapRequest → att_swap_requests

P1-4/P2-1 修复：Text→TIMESTAMPTZ/JSONB，补 TimestampMixin 审计字段
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Date, Text, Boolean, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Schedule(TimestampMixin, Base):
    __tablename__ = "att_schedules"
    __table_args__ = (UniqueConstraint("employee_id", "date"), {'extend_existing': True})

    id: Mapped[uuid.UUID] = mapped_column("schedule_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id", ondelete="CASCADE"))
    date: Mapped[str] = mapped_column(Date)
    shift_type: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ScheduleSnapshot(TimestampMixin, Base):
    """P2-1 修复：继承 TimestampMixin 补 updated_at；P1-4：Text→JSONB/TIMESTAMPTZ"""
    __tablename__ = "att_schedule_snapshots"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("snapshot_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    period: Mapped[str] = mapped_column(String(7))
    snapshot_data: Mapped[dict] = mapped_column(JSONB)  # P1-4: Text → JSONB
    version: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    # created_at/updated_at 由 TimestampMixin 提供


class ScheduleRule(TimestampMixin, Base):
    """P2-1 修复：继承 TimestampMixin；P1-4：Text→JSONB"""
    __tablename__ = "att_schedule_rules"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("rule_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"))
    rule_type: Mapped[str] = mapped_column(String(50))
    rule_config: Mapped[dict] = mapped_column(JSONB)  # P1-4: Text → JSONB
    is_active: Mapped[bool] = mapped_column(default=True)
    # created_at/updated_at 由 TimestampMixin 提供


class ShiftSwapRequest(TimestampMixin, Base):
    __tablename__ = "att_swap_requests"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("swap_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    swap_with_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    swap_date: Mapped[str] = mapped_column(Date)
    swap_shift: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending_swap_with")
    swap_with_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # P1-4: Text → TIMESTAMPTZ
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # P1-4: Text → TIMESTAMPTZ
    reject_reason: Mapped[str | None] = mapped_column(Text)
