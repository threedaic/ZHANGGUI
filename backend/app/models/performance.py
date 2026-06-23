"""
员工月度业绩数据模型（已迁移到 SPEC 2.0 新表）

EmployeeMonthlyPerformance → hr_performance（UUID主键，Python属性 id 映射到 perf_id 列）

设计目的:
  - 作为 KPI 和工资计算的共同数据源，避免重复查询明细
  - 支持自动汇总（从 table_sessions + wework_payments）和手工录入
  - 业绩类型可扩展（开瓶/开卡/订桌/企微收款/手工录入等）

业绩闭环:
  1. 订桌系统识别员工 (table_sessions.commission_employee_id)
  2. 企微收款 API 拉取个人收款 (wework_payment_sync)
  3. 汇总到本表 (按员工×月份×业绩类型)
  4. KPI 和工资计算从本表取数
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class EmployeeMonthlyPerformance(TimestampMixin, Base):
    """员工月度业绩汇总表（hr_performance）

    每个员工每个月每个业绩类型一条记录。
    业绩类型(performance_type):
      - booking       订桌业绩（来自 table_sessions）
      - wework_payment 企微收款业绩（来自 wework_payment_sync）
      - bottle        开瓶业绩
      - card          开卡业绩
      - manual        手工录入
    """

    __tablename__ = "hr_performance"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "employee_id", "period", "performance_type",
            name="uq_emp_perf_store_emp_period_type",
        ),
        {'extend_existing': True},
    )

    # 主键：Python 用 EmployeeMonthlyPerformance.id，DB 列是 perf_id
    id: Mapped[uuid.UUID] = mapped_column("perf_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"), comment="门店ID"
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id", ondelete="CASCADE"), comment="员工ID"
    )
    period: Mapped[str] = mapped_column(
        String(7), comment="账期月份 YYYY-MM"
    )
    performance_type: Mapped[str] = mapped_column(
        String(30), comment="业绩类型: booking/wework_payment/bottle/card/manual"
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="业绩金额合计"
    )
    detail_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="明细笔数（如订单数/收款笔数）"
    )
    source: Mapped[str] = mapped_column(
        String(20), default="auto", comment="数据来源: auto/manual"
    )
    source_ref: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="明细引用（如订单ID列表）"
    )
    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后汇总时间"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
