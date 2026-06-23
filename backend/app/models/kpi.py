"""
KPI 考核数据模型（已迁移到 SPEC 2.0 新表）

KPITemplate → hr_kpi_templates（UUID主键，Python属性 id 映射到 template_id 列）
KPIScore    → hr_kpi_scores（UUID主键，Python属性 id 映射到 score_id 列）
KPIResult   → hr_kpi_results（UUID主键，Python属性 id 映射到 result_id 列）
KPIAppeal   → hr_kpi_appeals（UUID主键，Python属性 id 映射到 appeal_id 列）

字段类型规范:
  - 分数/系数: Numeric(12,2) / Numeric(5,2)
  - 时间: DateTime(timezone=True)
  - JSON: JSONB
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class KPITemplate(TimestampMixin, Base):
    __tablename__ = "hr_kpi_templates"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 KPITemplate.id，DB 列是 template_id
    id: Mapped[uuid.UUID] = mapped_column("template_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    role: Mapped[str] = mapped_column(String(30))
    dimension: Mapped[str] = mapped_column(String(50))
    dimension_label: Mapped[str] = mapped_column(String(50))
    weight: Mapped[float] = mapped_column(Numeric(5, 2))
    formula_type: Mapped[str] = mapped_column(String(30), default="ratio")
    formula_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_source: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KPIScore(Base):
    __tablename__ = "hr_kpi_scores"
    __table_args__ = (
        UniqueConstraint("employee_id", "period", "dimension"),
        {'extend_existing': True},
    )

    # 主键：Python 用 KPIScore.id，DB 列是 score_id
    id: Mapped[uuid.UUID] = mapped_column("score_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    period: Mapped[str] = mapped_column(String(7))
    dimension: Mapped[str] = mapped_column(String(50))
    raw_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    raw_description: Mapped[str | None] = mapped_column(Text)
    normalized_score: Mapped[float] = mapped_column(Numeric(12, 2))
    weight: Mapped[float] = mapped_column(Numeric(5, 2))
    weighted_score: Mapped[float] = mapped_column(Numeric(12, 2))
    data_source: Mapped[str | None] = mapped_column(String(50))
    source_reference: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KPIResult(Base):
    __tablename__ = "hr_kpi_results"
    __table_args__ = (
        UniqueConstraint("employee_id", "period"),
        {'extend_existing': True},
    )

    # 主键：Python 用 KPIResult.id，DB 列是 result_id
    id: Mapped[uuid.UUID] = mapped_column("result_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    period: Mapped[str] = mapped_column(String(7))
    total_score: Mapped[float] = mapped_column(Numeric(12, 2))
    coefficient: Mapped[float] = mapped_column(Numeric(5, 2), default=1.00)
    coefficient_reason: Mapped[str | None] = mapped_column(Text)
    rank_in_store: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KPIAppeal(Base):
    __tablename__ = "hr_kpi_appeals"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 KPIAppeal.id，DB 列是 appeal_id
    id: Mapped[uuid.UUID] = mapped_column("appeal_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hr_kpi_results.result_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    dimension: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
