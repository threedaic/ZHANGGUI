"""
合同系统数据模型（已迁移到 SPEC 2.0 新表）

wage_salary_matrix: 薪资矩阵（5岗位 x 4档）
wage_contracts:     员工劳动合同

迁移变更（2026-06 SPEC 2.0）:
  - salary_matrix → wage_salary_matrix（主键 matrix_id, UUID）
  - contracts → wage_contracts（主键 contract_id, UUID）
  - SalaryMatrix 新增 store_id 字段，继承 TimestampMixin
  - SalaryMatrix UniqueConstraint 改为 UNIQUE(store_id, position, grade)
  - signed_by/created_by 外键指向 sys_users.user_id
  - template_data 从 JSON 改为 JSONB
"""
import uuid
from datetime import date, datetime
from sqlalchemy import (
    String, Numeric, Date, DateTime, Text,
    ForeignKey, Boolean, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SalaryMatrix(TimestampMixin, Base):
    """薪资矩阵表：5岗位 x 4档 薪资标准（wage_salary_matrix）"""

    __tablename__ = "wage_salary_matrix"
    __table_args__ = (
        UniqueConstraint("store_id", "position", "grade", name="uq_salary_matrix_position_grade"),
        {'extend_existing': True},
    )

    # 主键：Python 用 SalaryMatrix.id，DB 列是 matrix_id
    id: Mapped[uuid.UUID] = mapped_column(
        "matrix_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE")
    )
    position: Mapped[str] = mapped_column(
        String(30), comment="岗位: 店长/吧员/服务员/厨师/保洁"
    )
    grade: Mapped[str] = mapped_column(
        String(20), comment="职档: 学徒/正式/副职/正职"
    )
    monthly_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), comment="月薪总额"
    )
    base_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), default=3000.0, comment="基本工资，固定3000"
    )
    meal_allowance: Mapped[float] = mapped_column(
        Numeric(12, 2), default=400.0, comment="餐补"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用"
    )


class Contract(TimestampMixin, Base):
    """劳动合同表（wage_contracts，薪资基准表，工资计算以此为准）"""

    __tablename__ = "wage_contracts"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 Contract.id，DB 列是 contract_id
    id: Mapped[uuid.UUID] = mapped_column(
        "contract_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id", ondelete="CASCADE")
    )
    contract_no: Mapped[str] = mapped_column(
        String(50), unique=True, comment="合同编号"
    )
    position: Mapped[str] = mapped_column(
        String(30), comment="岗位"
    )
    grade: Mapped[str] = mapped_column(
        String(20), comment="职档"
    )
    monthly_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), comment="月薪总额（工资计算基准）"
    )
    base_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), default=3000.0, comment="基本工资"
    )
    meal_allowance: Mapped[float] = mapped_column(
        Numeric(12, 2), default=400.0, comment="餐补"
    )
    allowance: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.0, comment="补贴 = 月薪 - 基本工资"
    )
    start_date: Mapped[date] = mapped_column(
        Date, comment="合同开始日期"
    )
    end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="合同结束日期"
    )
    status: Mapped[str] = mapped_column(
        String(30), default="draft",
        comment="draft/pending_sign/signed/expired/terminated"
    )
    esign_flow_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="腾讯电子签流程 ID"
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="签署完成时间"
    )
    signed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="签署人 user_id"
    )
    template_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="模板填充的完整字段（20+字段）"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True, comment="创建人"
    )
