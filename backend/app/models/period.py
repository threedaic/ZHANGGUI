"""
账期管理数据模型（已迁移到 SPEC 2.0 新表）

wage_periods: 月度账期表，控制考勤/KPI/工资等数据的关账状态
             状态流转: open(开放) -> locked(锁定，不可改明细) -> closed(关账，不可改任何数据)

迁移变更（2026-06 SPEC 2.0）:
  - periods → wage_periods（主键 period_id, UUID）
  - store_id 外键指向 shared_stores.store_id
  - locked_by/closed_by 外键指向 sys_users.user_id
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Period(TimestampMixin, Base):
    """月度账期表（wage_periods）

    每个门店每个月一条记录，控制该月所有月度数据（考勤汇总/KPI/业绩/工资）的修改权限。
    - open: 可正常录入/修改/重算
    - locked: 明细数据冻结，仅允许工资条状态流转
    - closed: 完全冻结，任何写入均被拒绝
    """

    __tablename__ = "wage_periods"
    __table_args__ = (
        UniqueConstraint("store_id", "period", name="uq_periods_store_period"),
        {'extend_existing': True},
    )

    # 主键：Python 用 Period.id，DB 列是 period_id
    id: Mapped[uuid.UUID] = mapped_column(
        "period_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"), comment="门店ID"
    )
    period: Mapped[str] = mapped_column(
        String(7), comment="账期月份 YYYY-MM"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", comment="状态: open/locked/closed"
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="锁定时间"
    )
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="锁定操作人"
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="关账时间"
    )
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="关账操作人"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
