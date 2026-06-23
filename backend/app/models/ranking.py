"""
员工排名数据模型（已迁移到 SPEC 2.0 新表）

EmployeeRanking → hr_rankings（UUID主键，Python属性 id 映射到 ranking_id 列）

设计目的:
  - 激励员工：业绩/KPI/考勤/评分四维排名
  - 全员可见名次（透明激励），但不显示工资金额
  - 按门店+月份+排名类型聚合

排名类型(rank_type):
  - performance  业绩排名（按个人业绩金额）
  - kpi          KPI排名（按KPI总分）
  - attendance   考勤排名（按全勤天数/迟到次数倒序）
  - rating       评分排名（按客户评分均分）
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class EmployeeRanking(Base):
    """员工月度排名表（hr_rankings）

    每个员工每个月每个排名类型一条记录。
    rank_value 为排名依据的数值（如业绩金额/KPI总分/全勤天数/评分均分）
    rank_position 为名次（1=第一名）。
    """

    __tablename__ = "hr_rankings"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "employee_id", "period", "rank_type",
            name="uq_emp_ranking_store_emp_period_type",
        ),
        {'extend_existing': True},
    )

    # 主键：Python 用 EmployeeRanking.id，DB 列是 ranking_id
    id: Mapped[uuid.UUID] = mapped_column("ranking_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"), comment="门店ID"
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id", ondelete="CASCADE"), comment="员工ID"
    )
    period: Mapped[str] = mapped_column(
        String(7), comment="账期月份 YYYY-MM"
    )
    rank_type: Mapped[str] = mapped_column(
        String(30), comment="排名类型: performance/kpi/attendance/rating"
    )
    rank_value: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="排名依据数值"
    )
    rank_position: Mapped[int] = mapped_column(
        Integer, comment="名次（1=第一名）"
    )
    detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="排名明细（JSON，如业绩构成）"
    )
    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="计算时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
