"""
工资计算数据模型（已迁移到 SPEC 2.0 新表）

wage_records:       工资主表（一个员工一个月一条）
wage_record_items:  工资明细子表（每条工资由 N 个工资项组成）

迁移变更（2026-06 SPEC 2.0）:
  - payroll_records → wage_records（主键 wage_id, UUID）
  - payroll_record_items → wage_record_items（主键 item_id, UUID）
  - 主键/外键改为 UUID 类型
  - snapshot/detail 从 JSON 改为 JSONB
  - finalized_by/paid_by 外键指向 sys_users.user_id
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, DateTime, Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class PayrollRecord(TimestampMixin, Base):
    """工资主表：一个员工一个账期一条记录（wage_records）"""

    __tablename__ = "wage_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "period"),
        {'extend_existing': True},
    )

    # 主键：Python 用 PayrollRecord.id，DB 列是 wage_id
    id: Mapped[uuid.UUID] = mapped_column(
        "wage_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    period: Mapped[str] = mapped_column(String(7), comment="账期 YYYY-MM")

    # 汇总金额（由子表 items 累加得出）
    total_income: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="收入项合计"
    )
    total_deduction: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="扣款项合计"
    )
    net_pay: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="实发工资 = 收入合计 - 扣款合计"
    )

    # 快照字段（生成工资时记录，便于审计追溯）
    kpi_coefficient: Mapped[float] = mapped_column(
        Numeric(5, 2), default=1.00, comment="KPI系数快照"
    )
    snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="计算快照（合同薪资/考勤汇总/业绩汇总等原始数据）"
    )

    # 状态流转: draft(草稿) -> confirmed(已确认) -> paid(已发放)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="状态: draft/confirmed/paid"
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生成时间"
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="确认时间"
    )
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="确认人"
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发放时间"
    )
    paid_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="发放操作人"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关联明细
    items: Mapped[list["PayrollRecordItem"]] = relationship(
        back_populates="record", cascade="all, delete-orphan", lazy="selectin"
    )


class PayrollRecordItem(Base):
    """工资明细子表：每条工资由 N 个工资项组成（wage_record_items）

    item_code 对应 wage_items_config.item_code
    item_type: income=收入 / deduction=扣款
    amount: 该项金额（正数）
    """

    __tablename__ = "wage_record_items"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 PayrollRecordItem.id，DB 列是 item_id
    id: Mapped[uuid.UUID] = mapped_column(
        "item_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    # record_id 属性映射到 wage_id 列（外键指向 wage_records.wage_id）
    record_id: Mapped[uuid.UUID] = mapped_column(
        "wage_id", UUID(as_uuid=True), ForeignKey("wage_records.wage_id", ondelete="CASCADE")
    )
    item_code: Mapped[str] = mapped_column(
        String(50), comment="工资项代码"
    )
    item_name: Mapped[str] = mapped_column(
        String(50), comment="工资项名称（快照）"
    )
    item_type: Mapped[str] = mapped_column(
        String(20), comment="类型: income/deduction"
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, comment="金额（正数）"
    )
    data_source: Mapped[str] = mapped_column(
        String(30), comment="数据源: contract/attendance/performance/kpi/rule/manual"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="显示顺序"
    )
    detail: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="计算明细（如迟到分钟数×5元=50元）"
    )

    record: Mapped["PayrollRecord"] = relationship(back_populates="items")
