"""
客户评价数据模型（已迁移到 SPEC 2.0 新表）

GuestRating → hr_guest_ratings（UUID主键，Python属性 id 映射到 rating_id 列）

字段说明:
  - employee_id: 关联服务员工（订桌时自动识别，用于KPI评分维度）
  - overall_score: 综合评分（1-5分，由各维度均分得出）
  - created_at: 评价时间（DateTime类型，便于按月聚合）
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, CheckConstraint, DateTime, Numeric, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class GuestRating(Base):
    __tablename__ = "hr_guest_ratings"
    __table_args__ = (
        CheckConstraint("food_quality IS NULL OR (food_quality >= 1 AND food_quality <= 5)", name="ck_food_quality"),
        CheckConstraint("food_speed IS NULL OR (food_speed >= 1 AND food_speed <= 5)", name="ck_food_speed"),
        CheckConstraint("drink_quality IS NULL OR (drink_quality >= 1 AND drink_quality <= 5)", name="ck_drink_quality"),
        CheckConstraint("drink_speed IS NULL OR (drink_speed >= 1 AND drink_speed <= 5)", name="ck_drink_speed"),
        CheckConstraint("service_attitude IS NULL OR (service_attitude >= 1 AND service_attitude <= 5)", name="ck_service_attitude"),
        CheckConstraint("service_speed IS NULL OR (service_speed >= 1 AND service_speed <= 5)", name="ck_service_speed"),
        CheckConstraint("cleanliness IS NULL OR (cleanliness >= 1 AND cleanliness <= 5)", name="ck_cleanliness"),
        {'extend_existing': True},
    )

    # 主键：Python 用 GuestRating.id，DB 列是 rating_id
    id: Mapped[uuid.UUID] = mapped_column("rating_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"), nullable=True, comment="服务员工ID（订桌识别）"
    )
    table_no: Mapped[str] = mapped_column(String(16))
    food_quality: Mapped[int | None] = mapped_column(Integer)
    food_speed: Mapped[int | None] = mapped_column(Integer)
    drink_quality: Mapped[int | None] = mapped_column(Integer)
    drink_speed: Mapped[int | None] = mapped_column(Integer)
    service_attitude: Mapped[int | None] = mapped_column(Integer)
    service_speed: Mapped[int | None] = mapped_column(Integer)
    cleanliness: Mapped[int | None] = mapped_column(Integer)
    overall_score: Mapped[float] = mapped_column(Numeric(3, 1), comment="综合评分1-5")
    comment: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="qr_code")
    is_low_score: Mapped[bool] = mapped_column(Boolean, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    store_response: Mapped[str | None] = mapped_column(Text)
    response_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
