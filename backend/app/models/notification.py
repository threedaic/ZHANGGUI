"""
统一消息通知模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Notification(Base):
    __tablename__ = "sys_notifications"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("notification_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column("employee_id", UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))

    type: Mapped[str] = mapped_column(String(40))  # daily_report / attendance_alert / shift_change / approval / reminder
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)

    channel: Mapped[str] = mapped_column(String(20), default="in_app")  # in_app / wecom / all
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationSetting(TimestampMixin, Base):
    __tablename__ = "sys_notification_settings"
    __table_args__ = (
        UniqueConstraint("store_id", "setting_key"),
        {'extend_existing': True},
    )

    id: Mapped[uuid.UUID] = mapped_column("setting_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))

    setting_key: Mapped[str] = mapped_column(String(40))  # daily_report / attendance_alert / shift_change / approval / reminder
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    channel: Mapped[str] = mapped_column(String(20), default="all")  # in_app / wecom / all （站内信+企微应用消息）
    push_to_group: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否同时推送到企微群机器人
    target_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    schedule_time: Mapped[str | None] = mapped_column(String(8))  # 23:00
