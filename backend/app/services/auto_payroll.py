"""
============================================================================
自动发薪 Service — 六模块工资计算
============================================================================

【模块概览】
六个模块按顺序计算，最终相加 = 员工实发工资：

  合同模块(始终启用) → 底薪3000 + 补贴(月薪-3000) = 月薪
  业绩模块(可关)     → 业绩总额 × 提成比例(默认10%) = 提成
  考勤模块(始终启用) → 迟到分钟×5 + 旷工天数×日薪×3 + 早退次数×100 = 扣款(负数)
  KPI模块(可关)      → 底薪 × (KPI系数 - 1) = 奖金
  奖惩模块(可关)     → 奖励总额 - 惩罚总额 = 净额
  加班费模块(可关)    → 日薪 × 3倍 × 加班天数 = 加班费

  实发 = 合同 + 业绩提成 - 考勤扣款 + KPI奖金 + 奖惩净额 + 加班费

【数据来源】
  合同   ← wage_contracts 表（status=signed 的最新合同）
  业绩   ← hr_performance 表（按 period 聚合 total_amount）
  考勤   ← att_records 表（按月聚合迟到/旷工/早退次数）
  KPI   ← kpi_results 表（status=confirmed）
  奖惩   ← hr_penalty_notices 表（status=issued，按 issued_at 月份过滤）
  加班费 ← att_records 表（出勤天数 - 应出勤天数 = 加班天数）

【模块开关存储】
  存在 shared_store_settings.extra_config.payroll_modules 里
  格式：{"contract": true, "performance": false, ...}
  合同和考勤 always_on=True，不能关闭

【薪资规则存储】
  存在 shared_store_settings.extra_config.payroll_rules 里
  格式：{"commission_rate": 0.1, "late_deduction_per_minute": 5, ...}
============================================================================
"""
import uuid
import calendar
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text, func
from sqlalchemy.orm.attributes import flag_modified
from loguru import logger

from app.models.store import StoreSettings
from app.models.employee import Employee
from app.models.contract import Contract
from app.models.attendance import AttendanceRecord
from app.models.performance import EmployeeMonthlyPerformance
from app.models.penalty_notice import PenaltyNotice
from app.schemas.penalty import NOTICE_TYPES, is_reward


# ============================================================================
# 模块定义：六个模块的元信息（名称、是否锁定、颜色）
# always_on=True 的模块不能被关闭（合同和考勤）
# color 用于前端显示彩色卡片
# ============================================================================
MODULES = {
    "contract": {"name": "合同", "always_on": True, "color": "#4CAF50"},
    "performance": {"name": "业绩", "always_on": False, "color": "#E91E63"},
    "attendance": {"name": "考勤", "always_on": True, "color": "#FF9800"},
    "kpi": {"name": "KPI", "always_on": False, "color": "#00BCD4"},
    "reward_penalty": {"name": "奖惩", "always_on": False, "color": "#9C27B0"},
    "overtime": {"name": "加班费", "always_on": False, "color": "#3F51B5"},
}

# ============================================================================
# 默认薪资规则（老板可在前端调整）
# 这些值会作为默认值，如果门店没有自定义规则就用这些
# ============================================================================
DEFAULT_RULES = {
    "commission_rate": 0.10,           # 提成比例 10%（业绩总额 × 此比例 = 提成）
    "commission_mode": "fixed",         # 提成模式: fixed(固定) / by_role(按角色) / tiered(阶梯)
    # 按角色提成：不同岗位不同比例
    "commission_rates_by_role": {
        "boss": 0.03,
        "store_manager": 0.03,
        "bar_manager": 0.10,
        "service_manager": 0.05,
        "kitchen_manager": 0.03,
        "staff": 0.05,
    },
    # 阶梯提成：业绩越高比例越高（按命中最高档计算）
    "commission_tiers": [
        {"min": 0, "rate": 0.05},
        {"min": 10000, "rate": 0.08},
        {"min": 30000, "rate": 0.12},
    ],
    "late_deduction_per_minute": 5,    # 迟到每分钟扣 5 元
    "absent_factor": 3,                # 旷工扣 3 倍日薪（日薪 = 月薪 / 应出勤天数）
    "early_deduction_per_time": 100,   # 早退每次扣 100 元
    "rest_days_per_month": 4,           # 月休息 4 天（应出勤 = 当月天数 - 4）
    "overtime_multiplier": 3,          # 加班费 3 倍日薪
    "base_salary": 3000,               # 底薪 3000（合同拆分用）
}


class AutoPayrollService:
    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ==================== 模块开关 ====================

    async def get_modules(self) -> dict:
        """获取模块启用状态"""
        settings = await self._get_settings()
        extra = settings.extra_config if settings and settings.extra_config else {}
        payroll_modules = extra.get("payroll_modules", {})
        # 默认全部启用
        return {
            code: payroll_modules.get(code, True) for code in MODULES
        }

    async def set_modules(self, modules: dict) -> dict:
        """设置模块启用状态（不能关闭合同和考勤）"""
        settings = await self._get_settings()
        if not settings:
            return {}

        extra = settings.extra_config if settings.extra_config else {}
        payroll_modules = extra.get("payroll_modules", {})

        for code, enabled in modules.items():
            if code in MODULES and not MODULES[code]["always_on"]:
                payroll_modules[code] = bool(enabled)

        extra["payroll_modules"] = payroll_modules
        settings.extra_config = extra
        # JSONB 字段需要手动标记为已修改，否则 SQLAlchemy 不会生成 UPDATE
        flag_modified(settings, "extra_config")
        await self.session.flush()
        return await self.get_modules()

    # ==================== 规则 ====================

    async def get_rules(self) -> dict:
        """获取薪资规则"""
        settings = await self._get_settings()
        extra = settings.extra_config if settings and settings.extra_config else {}
        rules = extra.get("payroll_rules", {})
        # 合并默认值
        return {**DEFAULT_RULES, **rules}

    async def set_rules(self, rules: dict) -> dict:
        """更新薪资规则"""
        settings = await self._get_settings()
        if not settings:
            return {}

        extra = settings.extra_config if settings.extra_config else {}
        current_rules = extra.get("payroll_rules", {})
        current_rules.update(rules)
        extra["payroll_rules"] = current_rules
        settings.extra_config = extra
        # JSONB 字段需要手动标记为已修改
        flag_modified(settings, "extra_config")
        await self.session.flush()
        return await self.get_rules()

    # ==================== 大表格 ====================

    async def get_table(self, period: str) -> dict:
        """获取工资大表格数据"""
        modules = await self.get_modules()
        rules = await self.get_rules()
        employees = await self._get_active_employees()

        rows = []
        for emp in employees:
            row = await self._calc_employee(emp, period, modules, rules)
            rows.append(row)

        return {
            "period": period,
            "modules": modules,
            "module_info": MODULES,
            "rules": rules,
            "employees": rows,
            "summary": self._calc_summary(rows),
        }

    async def calculate(self, period: str) -> dict:
        """重新计算所有员工工资（自动触发）"""
        return await self.get_table(period)

    async def finalize(self, period: str, issued_by: uuid.UUID) -> dict:
        """一键发薪：算完 → 存档到 wage_records → 推送签收任务到收件箱

        流程:
          1. 调用 get_table() 获取计算结果
          2. 遍历员工，upsert 到 wage_records + wage_record_items
          3. 为每个员工推送 salary_slip 签收任务
          4. 返回汇总信息
        """
        from app.models.payroll import PayrollRecord, PayrollRecordItem
        from app.services.sign_task import SignTaskService

        # 1. 计算工资
        table = await self.get_table(period)
        employees = table.get("employees", [])
        if not employees:
            return {"period": period, "count": 0, "tasks_created": 0, "message": "无可发薪员工"}

        now = datetime.now(timezone.utc)
        records_created = 0
        tasks_created = 0
        sign_service = SignTaskService(self.session, self.store_id)

        # 2. 遍历员工，存档 + 推送
        for emp_row in employees:
            emp_id = uuid.UUID(emp_row["employee_id"])
            modules = emp_row.get("modules", {})

            # 收入项和扣款项
            income_items = []
            deduction_items = []
            total_income = 0.0
            total_deduction = 0.0

            # 合同模块（收入）
            contract = modules.get("contract", {})
            if contract.get("monthly_salary", 0) > 0:
                income_items.append(("contract", "合同月薪", contract["monthly_salary"], "contract", contract))
                total_income += contract["monthly_salary"]

            # 业绩模块（收入）
            perf = modules.get("performance", {})
            if perf.get("commission", 0) != 0:
                income_items.append(("commission", "业绩提成", perf["commission"], "performance", perf))
                total_income += perf["commission"]

            # KPI模块（收入，可能为负）
            kpi = modules.get("kpi", {})
            if kpi.get("bonus", 0) != 0:
                amount = kpi["bonus"]
                if amount > 0:
                    income_items.append(("kpi_bonus", "KPI奖金", amount, "kpi", kpi))
                    total_income += amount
                else:
                    deduction_items.append(("kpi_deduction", "KPI扣款", abs(amount), "kpi", kpi))
                    total_deduction += abs(amount)

            # 奖惩模块（收入或扣款）
            rp = modules.get("reward_penalty", {})
            if rp.get("reward", 0) > 0:
                income_items.append(("reward", "奖励", rp["reward"], "reward_penalty", rp))
                total_income += rp["reward"]
            if rp.get("penalty", 0) > 0:
                deduction_items.append(("penalty", "惩罚", rp["penalty"], "reward_penalty", rp))
                total_deduction += rp["penalty"]

            # 加班费模块（收入）
            ot = modules.get("overtime", {})
            if ot.get("total", 0) > 0:
                income_items.append(("overtime", "加班费", ot["total"], "overtime", ot))
                total_income += ot["total"]

            # 考勤模块（扣款）
            att = modules.get("attendance", {})
            if att.get("total", 0) < 0:
                deduction_amount = abs(att["total"])
                deduction_items.append(("attendance", "考勤扣款", deduction_amount, "attendance", att))
                total_deduction += deduction_amount

            net_pay = round(total_income - total_deduction, 2)

            # upsert wage_records
            stmt = select(PayrollRecord).where(
                and_(
                    PayrollRecord.employee_id == emp_id,
                    PayrollRecord.period == period,
                    PayrollRecord.store_id == self.store_id,
                )
            )
            result = await self.session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                # 更新已有记录
                record.total_income = round(total_income, 2)
                record.total_deduction = round(total_deduction, 2)
                record.net_pay = net_pay
                record.snapshot = {"modules": modules, "rules": table.get("rules", {})}
                record.status = "confirmed"
                record.generated_at = now
                record.finalized_at = now
                record.finalized_by = issued_by
                # 清空旧明细
                for old_item in list(record.items):
                    await self.session.delete(old_item)
                record.items = []
            else:
                record = PayrollRecord(
                    employee_id=emp_id,
                    store_id=self.store_id,
                    period=period,
                    total_income=round(total_income, 2),
                    total_deduction=round(total_deduction, 2),
                    net_pay=net_pay,
                    snapshot={"modules": modules, "rules": table.get("rules", {})},
                    status="confirmed",
                    generated_at=now,
                    finalized_at=now,
                    finalized_by=issued_by,
                )
                self.session.add(record)

            await self.session.flush()

            # 写入明细项
            sort_idx = 1
            for code, name, amount, source, detail in income_items:
                item = PayrollRecordItem(
                    store_id=self.store_id,
                    record_id=record.id,
                    item_code=code,
                    item_name=name,
                    item_type="income",
                    amount=round(amount, 2),
                    data_source=source,
                    sort_order=sort_idx,
                    detail=detail,
                )
                self.session.add(item)
                sort_idx += 1

            for code, name, amount, source, detail in deduction_items:
                item = PayrollRecordItem(
                    store_id=self.store_id,
                    record_id=record.id,
                    item_code=code,
                    item_name=name,
                    item_type="deduction",
                    amount=round(amount, 2),
                    data_source=source,
                    sort_order=sort_idx,
                    detail=detail,
                )
                self.session.add(item)
                sort_idx += 1

            records_created += 1

            # 推送签收任务到收件箱
            try:
                await sign_service.send_to_inbox(
                    employee_id=emp_id,
                    msg_type="salary_slip",
                    ref_id=record.id,
                    issued_by=issued_by,
                    extra={
                        "period": period,
                        "net_pay": net_pay,
                        "employee_name": emp_row.get("employee_name", ""),
                    },
                )
                tasks_created += 1
            except Exception as e:
                logger.warning(f"[AutoPayroll] 员工 {emp_id} 签收任务推送失败: {e}")

        await self.session.commit()
        logger.info(
            f"[AutoPayroll] 一键发薪完成: 账期 {period}, "
            f"存档 {records_created} 条, 推送 {tasks_created} 个签收任务"
        )
        return {
            "period": period,
            "count": records_created,
            "tasks_created": tasks_created,
            "total_net_pay": table.get("summary", {}).get("net_pay", 0),
        }

    async def update_cell(
        self, employee_id: uuid.UUID, period: str, module: str, amount: float
    ) -> dict:
        """更新单个单元格（手动调整金额）"""
        # 存到 extra_config 的 manual_adjustments 里
        settings = await self._get_settings()
        if not settings:
            return {}

        extra = settings.extra_config if settings.extra_config else {}
        adjustments = extra.get("manual_adjustments", {})
        key = f"{period}:{employee_id}:{module}"
        adjustments[key] = float(amount)
        extra["manual_adjustments"] = adjustments
        settings.extra_config = extra
        # JSONB 字段需要手动标记为已修改
        flag_modified(settings, "extra_config")
        await self.session.flush()
        return {"employee_id": str(employee_id), "period": period, "module": module, "amount": amount}

    # ==================== 加班费日历 ====================

    async def get_overtime_days(self, period: str) -> dict:
        """获取某月的三薪日期 { "2026-06-01": 3, "2026-06-02": 2 }"""
        settings = await self._get_settings()
        if not settings:
            return {}
        extra = settings.extra_config if settings.extra_config else {}
        all_days = extra.get("overtime_days", {})
        # 只返回该月份的数据
        return {k: v for k, v in all_days.items() if k.startswith(period)}

    async def set_overtime_days(self, period: str, days: dict) -> dict:
        """保存某月的三薪日期"""
        settings = await self._get_settings()
        if not settings:
            return {}

        extra = settings.extra_config if settings.extra_config else {}
        all_days = extra.get("overtime_days", {})

        # 删除该月份的旧数据
        keys_to_remove = [k for k in all_days.keys() if k.startswith(period)]
        for k in keys_to_remove:
            del all_days[k]

        # 写入新数据
        all_days.update(days)
        extra["overtime_days"] = all_days
        settings.extra_config = extra
        # JSONB 字段需要手动标记为已修改
        flag_modified(settings, "extra_config")
        await self.session.flush()
        return {k: v for k, v in all_days.items() if k.startswith(period)}

    # ==================== 单员工计算 ====================

    async def _calc_employee(
        self, emp: Employee, period: str, modules: dict, rules: dict
    ) -> dict:
        """计算单个员工工资"""
        result = {
            "employee_id": str(emp.id),
            "employee_name": emp.name,
            "position": emp.role or "staff",
            "modules": {},
            "net_pay": 0,
        }

        total = 0.0

        # 1. 合同模块（始终启用）
        contract_data = await self._get_contract_data(emp.id, rules)
        result["modules"]["contract"] = contract_data
        total += contract_data["total"]

        # 2. 业绩模块（可关）
        if modules.get("performance", True):
            perf_data = await self._get_performance_data(emp.id, period, rules, emp.role)
            result["modules"]["performance"] = perf_data
            total += perf_data["total"]
        else:
            result["modules"]["performance"] = {"total_amount": 0, "commission": 0, "total": 0}

        # 3. 考勤模块（始终启用）
        att_data = await self._get_attendance_data(emp.id, period, rules)
        result["modules"]["attendance"] = att_data
        total += att_data["total"]  # 负数

        # 4. KPI模块（可关）
        if modules.get("kpi", True):
            kpi_data = await self._get_kpi_data(emp.id, period, rules)
            result["modules"]["kpi"] = kpi_data
            total += kpi_data["total"]
        else:
            result["modules"]["kpi"] = {"coefficient": 1.0, "bonus": 0, "total": 0}

        # 5. 奖惩模块（可关）
        if modules.get("reward_penalty", True):
            rp_data = await self._get_reward_penalty_data(emp.id, period)
            result["modules"]["reward_penalty"] = rp_data
            total += rp_data["total"]
        else:
            result["modules"]["reward_penalty"] = {"reward": 0, "penalty": 0, "total": 0}

        # 6. 加班费模块（可关）
        if modules.get("overtime", True):
            ot_data = await self._get_overtime_data(emp.id, period, rules, contract_data)
            result["modules"]["overtime"] = ot_data
            total += ot_data["total"]
        else:
            result["modules"]["overtime"] = {"days": 0, "daily_wage": 0, "total": 0}

        result["net_pay"] = round(total, 2)
        return result

    # ==================== 各模块数据获取 ====================

    async def _get_contract_data(self, employee_id: uuid.UUID, rules: dict) -> dict:
        """合同模块：底薪 + 补贴 = 月薪"""
        stmt = (
            select(Contract)
            .where(
                and_(
                    Contract.store_id == self.store_id,
                    Contract.employee_id == employee_id,
                    Contract.status == "signed",
                )
            )
            .order_by(Contract.start_date.desc())
        )
        result = await self.session.execute(stmt)
        contract = result.scalars().first()

        if not contract:
            return {"monthly_salary": 0, "base_salary": 0, "allowance": 0, "total": 0}

        base = float(contract.base_salary or rules.get("base_salary", 3000))
        monthly = float(contract.monthly_salary or 0)
        allowance = float(contract.allowance or (monthly - base))

        return {
            "monthly_salary": round(monthly, 2),
            "base_salary": round(base, 2),
            "allowance": round(allowance, 2),
            "total": round(monthly, 2),
        }

    async def _get_performance_data(self, employee_id: uuid.UUID, period: str, rules: dict, role: str = "staff") -> dict:
        """业绩模块：根据提成模式计算提成

        3种模式:
          - fixed: 固定比例（业绩 × commission_rate）
          - by_role: 按角色设比例（不同岗位不同比例）
          - tiered: 阶梯提成（业绩越高比例越高，按命中最高档计算）
        """
        stmt = select(
            func.coalesce(func.sum(EmployeeMonthlyPerformance.total_amount), 0)
        ).where(
            and_(
                EmployeeMonthlyPerformance.store_id == self.store_id,
                EmployeeMonthlyPerformance.employee_id == employee_id,
                EmployeeMonthlyPerformance.period == period,
            )
        )
        result = await self.session.execute(stmt)
        total_amount = float(result.scalar() or 0)

        mode = rules.get("commission_mode", "fixed")
        commission_rate = 0.0
        mode_detail = ""

        if mode == "by_role":
            # 按角色提成
            rates_by_role = rules.get("commission_rates_by_role", {})
            commission_rate = float(rates_by_role.get(role, rates_by_role.get("staff", 0.05)))
            mode_detail = f"角色={role}, 比例={commission_rate*100:.1f}%"
        elif mode == "tiered":
            # 阶梯提成：找命中最高档
            tiers = rules.get("commission_tiers", [])
            commission_rate = float(rules.get("commission_rate", 0.10))  # 默认兜底
            if tiers:
                # 按门槛升序，找最后一个 total_amount >= min 的档位
                sorted_tiers = sorted(tiers, key=lambda t: t.get("min", 0))
                matched_rate = sorted_tiers[0].get("rate", 0.05)
                for tier in sorted_tiers:
                    if total_amount >= tier.get("min", 0):
                        matched_rate = tier.get("rate", matched_rate)
                commission_rate = float(matched_rate)
                mode_detail = f"阶梯: 业绩¥{total_amount:.0f} → 比例={commission_rate*100:.1f}%"
        else:
            # 固定比例
            commission_rate = float(rules.get("commission_rate", 0.10))
            mode_detail = f"固定比例={commission_rate*100:.1f}%"

        commission = round(total_amount * commission_rate, 2)

        return {
            "total_amount": round(total_amount, 2),
            "commission_mode": mode,
            "commission_rate": commission_rate,
            "mode_detail": mode_detail,
            "commission": commission,
            "total": commission,
        }

    async def _get_attendance_data(self, employee_id: uuid.UUID, period: str, rules: dict) -> dict:
        """考勤模块：迟到/旷工/早退扣款"""
        year, month = int(period[:4]), int(period[5:7])
        month_start = date(year, month, 1)

        result = await self.session.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE status = 'late') AS late_count, "
                "  COALESCE(SUM(late_minutes), 0) AS total_late_minutes, "
                "  COUNT(*) FILTER (WHERE status = 'absent') AS absent_count, "
                "  COUNT(*) FILTER (WHERE status = 'early') AS early_count "
                "FROM att_records "
                "WHERE employee_id = :eid AND store_id = :sid "
                "  AND date_trunc('month', date) = :month"
            ),
            {"eid": employee_id, "sid": self.store_id, "month": month_start},
        )
        row = result.mappings().first()

        late_count = int(row["late_count"] or 0) if row else 0
        total_late_minutes = int(row["total_late_minutes"] or 0) if row else 0
        absent_count = int(row["absent_count"] or 0) if row else 0
        early_count = int(row["early_count"] or 0) if row else 0

        late_per_min = float(rules.get("late_deduction_per_minute", 5))
        absent_factor = float(rules.get("absent_factor", 3))
        early_per_time = float(rules.get("early_deduction_per_time", 100))

        # 日薪 = 月薪 / (当月天数 - 休息天数)
        days_in_month = calendar.monthrange(year, month)[1]
        rest_days = int(rules.get("rest_days_per_month", 4))
        work_days = max(days_in_month - rest_days, 1)

        # 旷工扣款需要日薪，从合同获取
        contract_stmt = select(Contract.monthly_salary).where(
            and_(
                Contract.store_id == self.store_id,
                Contract.employee_id == employee_id,
                Contract.status == "signed",
            )
        ).order_by(Contract.start_date.desc())
        contract_result = await self.session.execute(contract_stmt)
        monthly_salary = float(contract_result.scalar() or 0)
        daily_wage = monthly_salary / work_days if work_days > 0 else 0

        late_deduction = round(total_late_minutes * late_per_min, 2)
        absent_deduction = round(absent_count * daily_wage * absent_factor, 2)
        early_deduction = round(early_count * early_per_time, 2)
        total_deduction = round(late_deduction + absent_deduction + early_deduction, 2)

        return {
            "late_count": late_count,
            "total_late_minutes": total_late_minutes,
            "late_deduction": late_deduction,
            "absent_count": absent_count,
            "absent_deduction": absent_deduction,
            "early_count": early_count,
            "early_deduction": early_deduction,
            "total": -total_deduction,  # 负数
        }

    async def _get_kpi_data(self, employee_id: uuid.UUID, period: str, rules: dict) -> dict:
        """KPI模块：底薪 × (KPI系数 - 1)"""
        from app.models.kpi import KPIResult
        stmt = select(KPIResult).where(
            and_(
                KPIResult.employee_id == employee_id,
                KPIResult.store_id == self.store_id,
                KPIResult.period == period,
                KPIResult.status == "confirmed",
            )
        )
        result = await self.session.execute(stmt)
        kpi = result.scalar_one_or_none()

        coefficient = float(kpi.coefficient or 1.0) if kpi else 1.0

        # 从合同获取底薪
        contract_stmt = select(Contract.base_salary).where(
            and_(
                Contract.store_id == self.store_id,
                Contract.employee_id == employee_id,
                Contract.status == "signed",
            )
        ).order_by(Contract.start_date.desc())
        contract_result = await self.session.execute(contract_stmt)
        base_salary = float(contract_result.scalar() or rules.get("base_salary", 3000))

        bonus = round(base_salary * (coefficient - 1.0), 2)

        return {
            "coefficient": coefficient,
            "total_score": float(kpi.total_score or 0) if kpi else 0,
            "bonus": bonus,
            "total": bonus,
        }

    async def _get_reward_penalty_data(self, employee_id: uuid.UUID, period: str) -> dict:
        """奖惩模块：奖励 - 惩罚"""
        year, month = int(period[:4]), int(period[5:7])
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        stmt = select(PenaltyNotice).where(
            and_(
                PenaltyNotice.store_id == self.store_id,
                PenaltyNotice.employee_id == employee_id,
                PenaltyNotice.status == "issued",
                PenaltyNotice.issued_at >= start_date,
                PenaltyNotice.issued_at < end_date,
            )
        )
        result = await self.session.execute(stmt)
        notices = result.scalars().all()

        reward = 0.0
        penalty = 0.0
        for n in notices:
            amount = float(n.amount or 0)
            if is_reward(n.penalty_type):
                reward += amount
            else:
                penalty += amount

        return {
            "reward": round(reward, 2),
            "penalty": round(penalty, 2),
            "total": round(reward - penalty, 2),
        }

    async def _get_overtime_data(
        self, employee_id: uuid.UUID, period: str, rules: dict, contract_data: dict
    ) -> dict:
        """加班费模块：日薪 × 倍数 × 天数

        自动匹配：法定节假日考勤记录算加班
        """
        year, month = int(period[:4]), int(period[5:7])
        days_in_month = calendar.monthrange(year, month)[1]
        rest_days = int(rules.get("rest_days_per_month", 4))
        work_days = max(days_in_month - rest_days, 1)

        monthly_salary = contract_data.get("monthly_salary", 0)
        daily_wage = monthly_salary / work_days if work_days > 0 else 0
        multiplier = float(rules.get("overtime_multiplier", 3))

        # 统计当月出勤天数中落在周末的天数（简化：用考勤记录数 - 应出勤天数）
        # 实际应匹配法定节假日日历，这里简化为统计考勤记录数
        month_start = date(year, month, 1)
        result = await self.session.execute(
            text(
                "SELECT COUNT(*) FROM att_records "
                "WHERE employee_id = :eid AND store_id = :sid "
                "  AND date_trunc('month', date) = :month "
                "  AND status IN ('present', 'late', 'early')"
            ),
            {"eid": employee_id, "sid": self.store_id, "month": month_start},
        )
        present_days = int(result.scalar() or 0)

        # 加班天数 = 实际出勤 - 应出勤（如果为正，算加班）
        overtime_days = max(present_days - work_days, 0)
        overtime_pay = round(daily_wage * multiplier * overtime_days, 2)

        return {
            "days": overtime_days,
            "daily_wage": round(daily_wage, 2),
            "multiplier": multiplier,
            "total": overtime_pay,
        }

    # ==================== 辅助方法 ====================

    async def _get_settings(self) -> StoreSettings | None:
        stmt = select(StoreSettings).where(StoreSettings.store_id == self.store_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_active_employees(self) -> list[Employee]:
        stmt = select(Employee).where(
            and_(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            )
        ).order_by(Employee.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _calc_summary(self, rows: list[dict]) -> dict:
        """计算汇总"""
        summary = {module: 0 for module in MODULES}
        total_net = 0
        for row in rows:
            for module_code, module_data in row["modules"].items():
                summary[module_code] += module_data.get("total", 0)
            total_net += row["net_pay"]

        return {
            "modules": {k: round(v, 2) for k, v in summary.items()},
            "net_pay": round(total_net, 2),
            "employee_count": len(rows),
        }

    # ==================== 员工自助预览 ====================

    async def get_my_preview(self, employee_id: uuid.UUID, period: str | None = None) -> dict:
        """员工自助工资预览：只算自己，按当前月份聚合 6 张表数据。

        与 get_table() 共用 _calc_employee() 计算逻辑，保证数据一致。
        返回字段包含：各模块明细、合计、发薪日、是否锁定。
        """
        # 默认当前月份（YYYY-MM）
        if not period:
            period = datetime.now(timezone.utc).strftime("%Y-%m")

        # 查员工
        emp_stmt = select(Employee).where(Employee.id == employee_id)
        emp = (await self.session.execute(emp_stmt)).scalar_one_or_none()
        if not emp:
            return {"error": "employee_not_found"}

        modules = await self.get_modules()
        rules = await self.get_rules()

        # 复用核心计算逻辑
        calc = await self._calc_employee(emp, period, modules, rules)

        # 转换为面向员工的展示结构
        m = calc["modules"]
        items = []
        # 合同（收入）
        c = m.get("contract", {})
        if c.get("monthly_salary", 0) != 0:
            items.append({
                "code": "contract", "name": "合同月薪", "type": "income",
                "amount": c.get("monthly_salary", 0), "source": "合同",
                "detail": c,
            })
        # 业绩（收入）
        p = m.get("performance", {})
        if p.get("commission", 0) != 0:
            items.append({
                "code": "performance", "name": "业绩提成", "type": "income",
                "amount": p.get("commission", 0), "source": "业绩表",
                "detail": {
                    "total_amount": p.get("total_amount", 0),
                    "commission_mode": p.get("commission_mode", ""),
                    "commission_rate": p.get("commission_rate", 0),
                    "mode_detail": p.get("mode_detail", ""),
                },
            })
        # 考勤（扣款，负数转正数显示）
        a = m.get("attendance", {})
        if a.get("total_deduction", 0) != 0:
            items.append({
                "code": "attendance", "name": "考勤扣款", "type": "deduction",
                "amount": abs(a.get("total_deduction", 0)), "source": "考勤表",
                "detail": {
                    "late_count": a.get("late_count", 0),
                    "total_late_minutes": a.get("total_late_minutes", 0),
                    "absent_count": a.get("absent_count", 0),
                    "early_count": a.get("early_count", 0),
                    "late_deduction": a.get("late_deduction", 0),
                    "absent_deduction": a.get("absent_deduction", 0),
                    "early_deduction": a.get("early_deduction", 0),
                },
            })
        # KPI（收入或扣款）
        k = m.get("kpi", {})
        if k.get("bonus", 0) != 0:
            items.append({
                "code": "kpi", "name": "KPI奖金/扣款", "type": "income" if k["bonus"] > 0 else "deduction",
                "amount": abs(k.get("bonus", 0)), "source": "KPI表",
                "detail": {
                    "coefficient": k.get("coefficient", 1.0),
                    "total_score": k.get("total_score", 0),
                },
            })
        # 奖惩
        r = m.get("reward_penalty", {})
        if r.get("reward", 0) > 0:
            items.append({
                "code": "reward", "name": "奖励", "type": "income",
                "amount": r.get("reward", 0), "source": "奖惩表",
                "detail": {"count": r.get("reward_count", 0)},
            })
        if r.get("penalty", 0) > 0:
            items.append({
                "code": "penalty", "name": "惩罚", "type": "deduction",
                "amount": r.get("penalty", 0), "source": "奖惩表",
                "detail": {"count": r.get("penalty_count", 0)},
            })
        # 加班费
        o = m.get("overtime", {})
        if o.get("total", 0) > 0:
            items.append({
                "code": "overtime", "name": "加班费", "type": "income",
                "amount": o.get("total", 0), "source": "考勤表",
                "detail": {
                    "days": o.get("days", 0),
                    "daily_wage": o.get("daily_wage", 0),
                    "multiplier": o.get("multiplier", 3),
                },
            })

        # 发薪日（从门店设置读）
        pay_day = 10
        try:
            settings = await self._get_settings()
            if settings:
                pay_day = getattr(settings, "payroll_day_of_month", None) or 10
        except Exception:
            pass

        return {
            "period": period,
            "employee_id": str(emp.id),
            "employee_name": emp.name,
            "position": emp.role or "staff",
            "net_pay": calc["net_pay"],
            "items": items,
            "modules_enabled": modules,
            "pay_day": pay_day,
            "is_finalized": False,  # 预览模式永远不是最终
            "notice": "预估数据，最终以月底结算为准",
        }
