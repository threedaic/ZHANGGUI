"""
OA 任务模型
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Date, DateTime, Boolean, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class OaTaskTemplate(TimestampMixin, Base):
    __tablename__ = "oa_task_templates"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    assignee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"), nullable=False)
    due_time: Mapped[str | None] = mapped_column(String(5))
    recurrence_type: Mapped[str] = mapped_column(String(10), nullable=False)
    recurrence_rule: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 完成要求（创建任务时传递给任务）
    require_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    require_note: Mapped[bool] = mapped_column(Boolean, default=False)
    requirements: Mapped[str | None] = mapped_column(Text)


class OaTask(TimestampMixin, Base):
    __tablename__ = "oa_tasks"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    task_type: Mapped[str] = mapped_column(String(20), default="direct")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("oa_task_templates.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 完成要求（用于完成时校验）
    require_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    require_note: Mapped[bool] = mapped_column(Boolean, default=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    # 完成说明（标记完成时填写）
    completion_note: Mapped[str | None] = mapped_column(Text)


class OaTaskAttachment(Base):
    __tablename__ = "oa_task_attachments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("oa_tasks.id", ondelete="CASCADE"), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(200))
    file_size: Mapped[int | None] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(20), default="progress")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
