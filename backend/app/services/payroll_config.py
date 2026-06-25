"""
工资项配置服务

管理 payroll_items_config（工资项配置）和 salary_rules（薪资规则）。
新门店首次使用时自动初始化默认配置。

默认工资项:
  收入项: 底薪、餐补、提成、KPI奖金
  扣款项: 迟到扣款、旷工扣款、早退扣款

默认薪资规则:
  - 迟到每分钟扣 5 元
  - 旷工扣 3 倍日薪
  - 早退每次 100 元
  - 提成比例 10%
  - 月休息 4 天
"""
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.payroll_config import PayrollItemConfig, SalaryRule
from app.services.formula_engine import BUILTIN_FORMULAS


# ==================== 默认薪资规则 ====================

DEFAULT_SALARY_RULES = [
    {
        "rule_code": "late_deduction_per_minute",
        "rule_name": "迟到每分钟扣款",
        "rule_value": 5.0,
        "rule_unit": "元",
        "note": "迟到每分钟扣5元",
    },
    {
        "rule_code": "absent_factor",
        "rule_name": "旷工扣款倍数",
        "rule_value": 3.0,
        "rule_unit": "倍",
        "note": "旷工每天扣3倍日薪",
    },
    {
        "rule_code": "early_deduction_per_time",
        "rule_name": "早退每次扣款",
        "rule_value": 100.0,
        "rule_unit": "元",
        "note": "早退每次扣100元",
    },
    {
        "rule_code": "commission_rate",
        "rule_name": "提成比例",
        "rule_value": 0.10,
        "rule_unit": "%",
        "note": "个人业绩×10%作为提成",
    },
    {
        "rule_code": "rest_days_per_month",
        "rule_name": "月休息天数",
        "rule_value": 4.0,
        "rule_unit": "天",
        "note": "每月固定4天休息",
    },
    # ====== 自动化流程规则（按流程顺序） ======
    {
        "rule_code": "attendance_remind_days_before",
        "rule_name": "补卡提醒",
        "rule_value": 1.0,
        "rule_unit": "天",
        "note": "考勤锁定前N天提醒员工补卡",
    },
    {
        "rule_code": "attendance_lock_day",
        "rule_name": "考勤锁定日",
        "rule_value": 2.0,
        "rule_unit": "日",
        "note": "每月N日后锁定上月考勤，发考勤确认单给员工签收",
    },
    {
        "rule_code": "auto_generate_days_before",
        "rule_name": "提前生成天数",
        "rule_value": 1.0,
        "rule_unit": "天",
        "note": "发薪日前N天自动生成工资草稿（0=发薪日当天）",
    },
    {
        "rule_code": "auto_lock_period",
        "rule_name": "工资审批",
        "rule_value": 1.0,
        "rule_unit": "",
        "note": "老板审批通过后自动锁定账期（1=是, 0=否）",
    },
    {
        "rule_code": "send_payslip_day",
        "rule_name": "发送工资单",
        "rule_value": 1.0,
        "rule_unit": "",
        "note": "账期锁定后会计可发送工资单给员工（1=是, 0=否）",
    },
    {
        "rule_code": "kpi_deadline_day",
        "rule_name": "KPI评分截止日",
        "rule_value": 3.0,
        "rule_unit": "日",
        "note": "每月N日前完成上月KPI评分",
    },
]


# ==================== 默认工资项 ====================

DEFAULT_PAYROLL_ITEMS = [
    {
        "item_code": "base_salary",
        "item_name": "底薪",
        "item_type": "income",
        "data_source": "contract",
        "formula_ast": BUILTIN_FORMULAS["base_salary"],
        "sort_order": 1,
        "is_system": True,
        "note": "合同月薪",
    },
    {
        "item_code": "meal_allowance",
        "item_name": "餐补",
        "item_type": "income",
        "data_source": "contract",
        "formula_ast": BUILTIN_FORMULAS["meal_allowance"],
        "sort_order": 2,
        "is_system": True,
        "note": "合同餐补",
    },
    {
        "item_code": "commission",
        "item_name": "提成",
        "item_type": "income",
        "data_source": "performance",
        "formula_ast": BUILTIN_FORMULAS["commission"],
        "sort_order": 3,
        "is_system": True,
        "note": "个人业绩×提成比例",
    },
    {
        "item_code": "kpi_bonus",
        "item_name": "KPI奖金",
        "item_type": "income",
        "data_source": "kpi",
        "formula_ast": BUILTIN_FORMULAS["kpi_bonus"],
        "sort_order": 4,
        "is_system": True,
        "note": "底薪×(KPI系数-1)",
    },
    {
        "item_code": "deduction_late",
        "item_name": "迟到扣款",
        "item_type": "deduction",
        "data_source": "attendance",
        "formula_ast": BUILTIN_FORMULAS["deduction_late"],
        "sort_order": 10,
        "is_system": True,
        "note": "迟到分钟×每分钟扣款",
    },
    {
        "item_code": "deduction_absent",
        "item_name": "旷工扣款",
        "item_type": "deduction",
        "data_source": "attendance",
        "formula_ast": BUILTIN_FORMULAS["deduction_absent"],
        "sort_order": 11,
        "is_system": True,
        "note": "旷工天数×日薪×旷工倍数",
    },
    {
        "item_code": "deduction_early",
        "item_name": "早退扣款",
        "item_type": "deduction",
        "data_source": "attendance",
        "formula_ast": BUILTIN_FORMULAS["deduction_early"],
        "sort_order": 12,
        "is_system": True,
        "note": "早退次数×每次扣款",
    },
]


class PayrollConfigService:
    """工资项配置 Service"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def init_default_config_if_empty(self) -> None:
        """如果门店没有工资项配置，初始化默认配置"""
        # 检查是否已有配置
        stmt = select(PayrollItemConfig).where(
            PayrollItemConfig.store_id == self.store_id
        )
        result = await self.session.execute(stmt)
        if result.scalars().first():
            # 已有配置，检查是否缺少新规则，缺则补上
            await self._ensure_new_rules_exist()
            return

        # 初始化默认薪资规则
        for rule in DEFAULT_SALARY_RULES:
            self.session.add(
                SalaryRule(
                    store_id=self.store_id,
                    rule_code=rule["rule_code"],
                    rule_name=rule["rule_name"],
                    rule_type=rule.get("rule_code", "other"),
                    rule_config={
                        "value": rule["rule_value"],
                        "unit": rule.get("rule_unit", ""),
                        "note": rule.get("note", ""),
                    },
                )
            )

        # 初始化默认工资项
        for item in DEFAULT_PAYROLL_ITEMS:
            self.session.add(
                PayrollItemConfig(
                    store_id=self.store_id,
                    item_code=item["item_code"],
                    item_name=item["item_name"],
                    item_type=item["item_type"],
                    data_source=item["data_source"],
                    formula_ast=item["formula_ast"],
                    sort_order=item["sort_order"],
                )
            )

        await self.session.flush()
        logger.info(
            f"[PayrollConfig] 门店 {self.store_id} 初始化默认工资配置"
        )

    async def _ensure_new_rules_exist(self) -> None:
        """检查已有门店是否缺少新规则，缺则补上；同时更新旧规则名称"""
        stmt = select(SalaryRule).where(
            SalaryRule.store_id == self.store_id
        )
        result = await self.session.execute(stmt)
        existing_rules = {r.rule_code: r for r in result.scalars()}

        # 补上缺少的规则
        new_rules = [
            rule for rule in DEFAULT_SALARY_RULES
            if rule["rule_code"] not in existing_rules
        ]
        for rule in new_rules:
            self.session.add(
                SalaryRule(
                    store_id=self.store_id,
                    rule_code=rule["rule_code"],
                    rule_name=rule["rule_name"],
                    rule_type=rule.get("rule_code", "other"),
                    rule_config={
                        "value": rule["rule_value"],
                        "unit": rule.get("rule_unit", ""),
                        "note": rule.get("note", ""),
                    },
                )
            )

        # 更新 auto_lock_period 的名称（从"自动锁定账期"改成"工资审批"）
        auto_lock_rule = existing_rules.get("auto_lock_period")
        if auto_lock_rule and auto_lock_rule.rule_name == "自动锁定账期":
            auto_lock_rule.rule_name = "工资审批"

        if new_rules or auto_lock_rule:
            await self.session.flush()
            logger.info(
                f"[PayrollConfig] 门店 {self.store_id} 补充新规则: {[r['rule_code'] for r in new_rules]}"
            )

    async def get_items_config(self) -> list[PayrollItemConfig]:
        """获取门店所有启用的工资项配置（按 sort_order 排序）"""
        stmt = (
            select(PayrollItemConfig)
            .where(
                and_(
                    PayrollItemConfig.store_id == self.store_id,
                    PayrollItemConfig.is_active.is_(True),
                )
            )
            .order_by(PayrollItemConfig.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_salary_rules(self) -> dict[str, float]:
        """获取门店薪资规则 {rule_code: rule_value}"""
        stmt = select(SalaryRule).where(
            and_(
                SalaryRule.store_id == self.store_id,
                SalaryRule.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return {r.rule_code: float(r.rule_value) for r in result.scalars().all()}

    async def upsert_item_config(
        self,
        item_code: str,
        item_name: str,
        item_type: str,
        data_source: str,
        formula_ast: dict | None,
        sort_order: int,
        default_value: float = 0,
        note: str | None = None,
    ) -> PayrollItemConfig:
        """新增或更新工资项配置"""
        stmt = select(PayrollItemConfig).where(
            and_(
                PayrollItemConfig.store_id == self.store_id,
                PayrollItemConfig.item_code == item_code,
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.item_name = item_name
            existing.item_type = item_type
            existing.data_source = data_source
            existing.formula_ast = formula_ast
            existing.sort_order = sort_order
            return existing
        else:
            item = PayrollItemConfig(
                store_id=self.store_id,
                item_code=item_code,
                item_name=item_name,
                item_type=item_type,
                data_source=data_source,
                formula_ast=formula_ast,
                sort_order=sort_order,
            )
            self.session.add(item)
            return item

    async def update_salary_rule(
        self, rule_code: str, rule_value: float
    ) -> SalaryRule | None:
        """更新薪资规则"""
        stmt = select(SalaryRule).where(
            and_(
                SalaryRule.store_id == self.store_id,
                SalaryRule.rule_code == rule_code,
            )
        )
        result = await self.session.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule:
            rule.rule_value = rule_value
            return rule
        return None

    async def toggle_rule_active(self, rule_code: str, is_active: bool) -> SalaryRule | None:
        """启用/禁用薪资规则（流程步骤开关）"""
        stmt = select(SalaryRule).where(
            and_(
                SalaryRule.store_id == self.store_id,
                SalaryRule.rule_code == rule_code,
            )
        )
        result = await self.session.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule:
            rule.is_active = is_active
            return rule
        return None

    async def get_active_modules(self) -> dict[str, bool]:
        """获取各模块是否启用（供公式引擎使用）"""
        stmt = select(SalaryRule).where(
            SalaryRule.store_id == self.store_id
        )
        result = await self.session.execute(stmt)
        rules = {r.rule_code: r for r in result.scalars().all()}

        return {
            "kpi_enabled": rules.get("kpi_deadline_day", type('R', (), {'is_active': True})()).is_active if "kpi_deadline_day" in rules else True,
            "attendance_lock_enabled": rules.get("attendance_lock_day", type('R', (), {'is_active': True})()).is_active if "attendance_lock_day" in rules else True,
            "auto_generate_enabled": rules.get("auto_generate_days_before", type('R', (), {'is_active': True})()).is_active if "auto_generate_days_before" in rules else True,
            "performance_enabled": True,  # 业绩模块默认启用
        }
