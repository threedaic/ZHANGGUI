"""
工资项配置与薪资规则数据模型（已迁移到 SPEC 2.0 新表）

wage_items_config: 工资项配置表（老板可视化配置）
  - 定义工资项（底薪/全勤奖/岗位津贴/提成/迟到扣款/旷工扣款...）
  - 每个工资项关联一个公式 AST（JSONB）
  - 工资生成时按配置逐项计算

wage_salary_rules: 薪资规则表（替代硬编码常量）
  - 迟到每分钟扣款、旷工扣款倍数、提成比例等
  - 按门店隔离，老板可在设置中调整

迁移变更（2026-06 SPEC 2.0）:
  - payroll_items_config → wage_items_config（主键 config_id, UUID）
  - salary_rules → wage_salary_rules（主键 rule_id, UUID）
  - formula_ast 属性映射到 formula 列（DB列名变更），JSON → JSONB
  - 删除 default_value / is_system / note（新表无）
  - SalaryRule 用 rule_type + rule_config(JSONB) 替代 rule_value + rule_unit
"""
import uuid
from sqlalchemy import (
    String, Integer, ForeignKey, UniqueConstraint, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class PayrollItemConfig(TimestampMixin, Base):
    """工资项配置表（wage_items_config）

    每个门店可配置任意数量的工资项，按 sort_order 顺序计算。
    item_type:
      - income     收入项（加项）
      - deduction  扣款项（减项）
    data_source:
      - contract / attendance / performance / kpi / rule / manual
    """

    __tablename__ = "wage_items_config"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "item_code", name="uq_payroll_items_store_code"
        ),
        {'extend_existing': True},
    )

    # 主键：Python 用 PayrollItemConfig.id，DB 列是 config_id
    id: Mapped[uuid.UUID] = mapped_column(
        "config_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"), comment="门店ID"
    )
    item_code: Mapped[str] = mapped_column(
        String(50), comment="工资项代码: base_salary/commission/kpi_bonus/full_attendance/deduction_late..."
    )
    item_name: Mapped[str] = mapped_column(
        String(50), comment="显示名称: 底薪/提成/KPI奖金/全勤奖/迟到扣款"
    )
    item_type: Mapped[str] = mapped_column(
        String(20), comment="类型: income=收入 / deduction=扣款"
    )
    data_source: Mapped[str] = mapped_column(
        String(30), comment="数据源: contract/attendance/performance/kpi/rule/manual"
    )
    # formula_ast 属性映射到 formula 列（DB列名变更），JSON → JSONB
    formula_ast: Mapped[dict | None] = mapped_column(
        "formula", JSONB, nullable=True, comment="公式 AST（JSONB），manual 类型可为空"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="计算顺序（从小到大）"
    )


class SalaryRule(TimestampMixin, Base):
    """薪资规则表（wage_salary_rules，替代硬编码常量）

    每个门店一套规则，老板可在设置中调整。
    规则代码(rule_code)对应公式 AST 中 source=rule 的 field。
    新表用 rule_type + rule_config(JSONB) 替代 rule_value + rule_unit。
    """

    __tablename__ = "wage_salary_rules"
    __table_args__ = (
        UniqueConstraint("store_id", "rule_code", name="uq_salary_rules_store_code"),
        {'extend_existing': True},
    )

    # 主键：Python 用 SalaryRule.id，DB 列是 rule_id
    id: Mapped[uuid.UUID] = mapped_column(
        "rule_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"), comment="门店ID"
    )
    rule_code: Mapped[str] = mapped_column(
        String(50), comment="规则代码: late_deduction_per_minute/absent_factor/commission_rate/rest_days_per_month..."
    )
    rule_name: Mapped[str] = mapped_column(
        String(100), comment="显示名称: 迟到每分钟扣款/旷工扣款倍数/提成比例/月休息天数"
    )
    rule_type: Mapped[str] = mapped_column(
        String(30), comment="规则类型"
    )
    rule_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="规则配置（JSONB）"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用"
    )
