"""
考勤与排班一体化数据模型（已迁移到 SPEC 2.0 新表）

AttendanceRecord → att_records（UUID主键，record_id）
ShiftConfig → att_shift_configs（UUID主键，shift_config_id）

字段与旧表完全对应，主键和外键改为 UUID。
clock_in/clock_out 在新表是 TIMESTAMPTZ，旧代码用字符串读写，SQLAlchemy 会自动处理。
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Date, Text, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class AttendanceRecord(TimestampMixin, Base):
    __tablename__ = "att_records"
    __table_args__ = (UniqueConstraint("employee_id", "date"), {'extend_existing': True})

    id: Mapped[uuid.UUID] = mapped_column("record_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    date: Mapped[str] = mapped_column(Date)

    # 排班信息
    scheduled_shift: Mapped[str | None] = mapped_column(String(20))
    shift_start_time: Mapped[str | None] = mapped_column(String(8))
    shift_end_time: Mapped[str | None] = mapped_column(String(8))
    is_overnight: Mapped[bool] = mapped_column(Boolean, default=False)

    # 打卡信息（P1-4: Text → TIMESTAMPTZ，与DB一致）
    clock_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 考勤判定
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_minutes: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[str] = mapped_column(String(20), default="manual")
    note: Mapped[str | None] = mapped_column(Text)


class ShiftConfig(TimestampMixin, Base):
    """门店班次配置。每个门店独立，老板在设置中维护。"""

    __tablename__ = "att_shift_configs"
    __table_args__ = (UniqueConstraint("store_id", "shift_code"), {'extend_existing': True})

    id: Mapped[uuid.UUID] = mapped_column("shift_config_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    shift_code: Mapped[str] = mapped_column(String(20))
    shift_name: Mapped[str] = mapped_column(String(20))
    start_time: Mapped[str] = mapped_column(String(8))
    end_time: Mapped[str] = mapped_column(String(8))
    is_overnight: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[str] = mapped_column(String(8), default="#FB0079")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
