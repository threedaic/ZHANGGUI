"""
签收任务模型 — 统一收件箱

支持类型：salary_slip（工资单）、penalty_notice（处罚通知）、attendance_confirm（考勤确认）
状态流转：pending → signed | disputed | revoked
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SignTask(TimestampMixin, Base):
    __tablename__ = "sig_tasks"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("task_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))

    type: Mapped[str] = mapped_column(String(30))  # salary_slip / penalty_notice / attendance_confirm
    title: Mapped[str] = mapped_column(String(200))
    ref_type: Mapped[str] = mapped_column(String(30))  # 关联业务表名
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))  # 关联业务记录 ID

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / signed / disputed / revoked
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signature_data: Mapped[str | None] = mapped_column(Text)  # base64 PNG 手写签名

    dispute_reason: Mapped[str | None] = mapped_column(Text)  # 异议理由
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))  # 发布人
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    notes: Mapped[str | None] = mapped_column(Text)  # 签收备注
    extra: Mapped[dict | None] = mapped_column(JSONB)  # 扩展（含撤回历史）
