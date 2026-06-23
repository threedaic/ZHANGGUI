"""
工资计算业务逻辑层（重构版）

核心改造:
  1. 从 payroll_items_config 读取工资项配置（替代硬编码）
  2. 从 4 个数据源汇总: 合同 + 考勤 + 个人业绩 + KPI
  3. 通过公式引擎计算每个工资项金额
  4. 写入 payroll_records + payroll_record_items（主表+明细子表）
  5. 账期锁定: 关账后不可重算

数据流:
  合同(contracts) ─┐
  考勤(attendance) ─┼─> 4源数据上下文 ─> 公式引擎 ─> 工资项金额 ─> payroll_record_items
  业绩(performance)─┤                                          └─> payroll_records (汇总)
  KPI(kpi_results) ─┘

公式: 实发 = 收入项合计 - 扣款项合计
"""
import calendar
from datetime import datetime
from sqlalchemy import select, and_, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.payroll import PayrollRecord, PayrollRecordItem
from app.models.contract import Contract
from app.models.employee import Employee
from app.models.kpi import KPIResult
from app.models.attendance import AttendanceRecord
from app.services.formula_engine import FormulaEngine
from app.services.payroll_config import PayrollConfigService
from app.services.performance import PerformanceService
from app.services.period import PeriodService
from app.utils.exceptions import (
    AppError, NotFoundError, ConflictError, ValidationError,
)


class PayrollService:
    """工资计算 Service（配置驱动版）"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id
        self.engine = FormulaEngine()
        self.config_service = PayrollConfigService(session, store_id)
        self.performance_service = PerformanceService(session, store_id)
        self.period_service = PeriodService(session, store_id)

    # ==================== 生成工资 ====================

    async def generate(
        self,
        period: str,
        employee_ids: list[int] | None = None,
        user_id: int | None = None,
    ) -> list[PayrollRecord]:
        """
        为指定员工生成月度工资记录。

        流程:
          1. 检查账期是否可写入（open 状态）
          2. 确保工资项配置已初始化
          3. 同步该月员工业绩到 employee_monthly_performance
          4. 取在职员工列表
          5. 逐人计算:
             a. 构建 4 源数据上下文（合同/考勤/业绩/KPI）
             b. 读取工资项配置，逐项用公式引擎计算
             c. 汇总收入项和扣款项
             d. 实发 = 收入合计 - 扣款合计
          6. 写入 payroll_records + payroll_record_items（upsert）
        """
        # 1. 账期检查
        await self.period_service.check_writable(period)

        # 2. 初始化默认配置（首次使用）
        await self.config_service.init_default_config_if_empty()

        # 3. 同步业绩数据
        await self.performance_service.sync_monthly_performance(period, employee_ids)

        # 4. 取员工列表
        employees = await self._get_employees(employee_ids)
        if not employees:
            raise NotFoundError("门店没有在职员工")

        # 5. 取工资项配置和薪资规则
        items_config = await self.config_service.get_items_config()
        if not items_config:
            raise ValidationError("门店未配置工资项，请先在设置中配置")

        salary_rules = await self.config_service.get_salary_rules()

        # 6. 逐人计算
        records: list[PayrollRecord] = []
        now = datetime.now()

        for emp in employees:
            try:
                record = await self._generate_for_employee(
                    emp, period, items_config, salary_rules, now
                )
                if record:
                    records.append(record)
            except Exception as e:
                logger.error(
                    f"[Payroll] 员工 {emp.name}({emp.id}) 工资计算失败: {e}"
                )
                raise

        await self.session.flush()
        await self.session.commit()
        logger.info(
            f"[Payroll] 门店 {self.store_id} 账期 {period} 生成 {len(records)} 条工资"
        )
        return records

    async def _get_employees(
        self, employee_ids: list[int] | None
    ) -> list[Employee]:
        """获取在职员工列表"""
        stmt = select(Employee).where(
            and_(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            )
        )
        if employee_ids:
            stmt = stmt.where(Employee.id.in_(employee_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _generate_for_employee(
        self,
        emp: Employee,
        period: str,
        items_config: list,
        salary_rules: dict[str, float],
        now: datetime,
    ) -> PayrollRecord | None:
        """为单个员工生成工资"""
        # 构建 4 源数据上下文
        context = await self._build_context(emp, period, salary_rules)
        if not context.get("contract"):
            logger.warning(
                f"[Payroll] 员工 {emp.name}({emp.id}) 无有效合同，跳过"
            )
            return None

        # 逐项计算
        items: list[PayrollRecordItem] = []
        total_income = 0.0
        total_deduction = 0.0

        for cfg in items_config:
            amount, detail = self.engine.evaluate(cfg.formula_ast, context)
            amount = abs(amount)  # 金额存正数，类型区分收入/扣款

            item = PayrollRecordItem(
                item_code=cfg.item_code,
                item_name=cfg.item_name,
                item_type=cfg.item_type,
                amount=amount,
                data_source=cfg.data_source,
                sort_order=cfg.sort_order,
                detail=detail,
            )
            items.append(item)

            if cfg.item_type == "income":
                total_income += amount
            else:
                total_deduction += amount

        net_pay = round(total_income - total_deduction, 2)

        # upsert 工资主表
        record = await self._upsert_record(
            emp, period, items, total_income, total_deduction, net_pay,
            context, now
        )

        logger.info(
            f"[Payroll] {emp.name}({emp.id}) {period}: "
            f"income={total_income} deduction={total_deduction} net={net_pay}"
        )
        return record

    async def _build_context(
        self, emp: Employee, period: str, salary_rules: dict[str, float]
    ) -> dict:
        """构建 4 源数据上下文

        Returns:
          {
            "contract": {"monthly_salary", "base_salary", "meal_allowance", "allowance"},
            "attendance": {"late_count", "total_late_minutes", "absent_count", "early_count", ...},
            "performance": {"total_amount", "booking", "wework_payment", ...},
            "kpi": {"coefficient", "total_score"},
            "rule": {"late_deduction_per_minute", ...},
          }
        """
        # 1. 合同数据
        contract_data = await self._get_contract_data(emp.id)

        # 2. 考勤数据
        attendance_data = await self._get_attendance_data(emp.id, period)

        # 3. 业绩数据
        performance_data = await self.performance_service.get_employee_performance(
            emp.id, period
        )

        # 4. KPI 数据
        kpi_data = await self._get_kpi_data(emp.id, period)

        return {
            "contract": contract_data,
            "attendance": attendance_data,
            "performance": {
                "total_amount": performance_data.get("total_amount", 0),
                "booking": performance_data.get("by_type", {}).get("booking", {}).get("amount", 0),
                "wework_payment": performance_data.get("by_type", {}).get("wework_payment", {}).get("amount", 0),
                "bottle": performance_data.get("by_type", {}).get("bottle", {}).get("amount", 0),
                "card": performance_data.get("by_type", {}).get("card", {}).get("amount", 0),
            },
            "kpi": kpi_data,
            "rule": salary_rules,
        }

    async def _get_contract_data(self, employee_id: int) -> dict:
        """获取员工合同数据（取最新生效合同）"""
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
            return {}

        return {
            "monthly_salary": float(contract.monthly_salary or 0),
            "base_salary": float(contract.base_salary or 0),
            "meal_allowance": float(contract.meal_allowance or 0),
            "allowance": float(contract.allowance or 0),
        }

    async def _get_attendance_data(self, employee_id: int, period: str) -> dict:
        """获取员工月度考勤汇总"""
        year, month = int(period[:4]), int(period[5:7])
        month_str = f"{year}-{month:02d}"

        result = await self.session.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE status = 'late') AS late_count, "
                "  COALESCE(SUM(late_minutes), 0) AS total_late_minutes, "
                "  COUNT(*) FILTER (WHERE status = 'absent') AS absent_count, "
                "  COUNT(*) FILTER (WHERE status = 'early') AS early_count, "
                "  COUNT(*) FILTER (WHERE status IN ('present','late','early')) AS present_days, "
                "  COUNT(*) AS total_days "
                "FROM attendance_records "
                "WHERE employee_id = :eid "
                "  AND store_id = :sid "
                "  AND date_trunc('month', date) = :month"
            ),
            {"eid": employee_id, "sid": self.store_id, "month": f"{month_str}-01"},
        )
        row = result.mappings().first()
        if not row:
            return {
                "late_count": 0, "total_late_minutes": 0,
                "absent_count": 0, "early_count": 0,
                "present_days": 0, "total_days": 0,
            }
        return {k: (int(v) if v is not None else 0) for k, v in dict(row).items()}

    async def _get_kpi_data(self, employee_id: int, period: str) -> dict:
        """获取员工月度 KPI 数据"""
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

        if not kpi:
            return {"coefficient": 1.0, "total_score": 0.0}

        return {
            "coefficient": float(kpi.coefficient or 1.0),
            "total_score": float(kpi.total_score or 0),
        }

    async def _upsert_record(
        self,
        emp: Employee,
        period: str,
        items: list[PayrollRecordItem],
        total_income: float,
        total_deduction: float,
        net_pay: float,
        context: dict,
        now: datetime,
    ) -> PayrollRecord:
        """upsert 工资记录（存在则更新，不存在则插入）"""
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.employee_id == emp.id,
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
            record.kpi_coefficient = context.get("kpi", {}).get("coefficient", 1.0)
            record.snapshot = context
            record.status = "draft"
            record.generated_at = now

            # 清空旧明细，重新写入
            for old_item in list(record.items):
                await self.session.delete(old_item)
            record.items = items
            for item in items:
                item.record = record
        else:
            # 新建记录
            record = PayrollRecord(
                employee_id=emp.id,
                store_id=self.store_id,
                period=period,
                total_income=round(total_income, 2),
                total_deduction=round(total_deduction, 2),
                net_pay=net_pay,
                kpi_coefficient=context.get("kpi", {}).get("coefficient", 1.0),
                snapshot=context,
                status="draft",
                generated_at=now,
                items=items,
            )
            self.session.add(record)

        return record

    # ==================== 工资查询 ====================

    async def get_monthly(
        self, period: str, page: int = 1, page_size: int = 50
    ) -> dict:
        """门店月度工资汇总"""
        from app.utils.pagination import PageParams
        params = PageParams(page=page, page_size=page_size)

        stmt = (
            select(PayrollRecord)
            .where(
                and_(
                    PayrollRecord.store_id == self.store_id,
                    PayrollRecord.period == period,
                )
            )
            .order_by(PayrollRecord.employee_id)
        )
        count_stmt = select(
            func.count(PayrollRecord.id)
        ).where(
            and_(
                PayrollRecord.store_id == self.store_id,
                PayrollRecord.period == period,
            )
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return {
                "period": period,
                "store_id": self.store_id,
                "items": [],
                "total_income": 0.0,
                "total_deduction": 0.0,
                "total_net_pay": 0.0,
                "status_summary": {},
            }

        employee_ids = [r.employee_id for r in records]
        emp_info = await self._get_employee_info(employee_ids)

        total_income = 0.0
        total_ded = 0.0
        total_net = 0.0
        status_summary: dict[str, int] = {}
        items = []

        for r in records:
            emp = emp_info.get(r.employee_id, {"name": "", "role": ""})
            items.append({
                "record_id": r.id,
                "employee_id": r.employee_id,
                "employee_name": emp["name"],
                "employee_role": emp["role"],
                "total_income": float(r.total_income or 0),
                "total_deduction": float(r.total_deduction or 0),
                "net_pay": float(r.net_pay or 0),
                "status": r.status,
            })
            total_income += float(r.total_income or 0)
            total_ded += float(r.total_deduction or 0)
            total_net += float(r.net_pay or 0)
            status_summary[r.status] = status_summary.get(r.status, 0) + 1

        return {
            "period": period,
            "store_id": self.store_id,
            "items": items,
            "total_income": round(total_income, 2),
            "total_deduction": round(total_ded, 2),
            "total_net_pay": round(total_net, 2),
            "status_summary": status_summary,
        }

    async def get_detail(self, record_id: int) -> dict:
        """单条工资详情，含明细项和数据源快照"""
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.id == record_id,
                PayrollRecord.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundError("工资记录不存在")

        emp_info = await self._get_employee_info([record.employee_id])
        emp = emp_info.get(record.employee_id, {"name": "", "role": ""})

        return {
            "id": record.id,
            "employee_id": record.employee_id,
            "store_id": record.store_id,
            "period": record.period,
            "total_income": float(record.total_income or 0),
            "total_deduction": float(record.total_deduction or 0),
            "net_pay": float(record.net_pay or 0),
            "kpi_coefficient": float(record.kpi_coefficient or 1.0),
            "status": record.status,
            "generated_at": record.generated_at.isoformat() if record.generated_at else None,
            "finalized_at": record.finalized_at.isoformat() if record.finalized_at else None,
            "paid_at": record.paid_at.isoformat() if record.paid_at else None,
            "notes": record.notes,
            "employee_name": emp["name"],
            "employee_role": emp["role"],
            "items": [
                {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "item_type": item.item_type,
                    "amount": float(item.amount or 0),
                    "data_source": item.data_source,
                    "sort_order": item.sort_order,
                    "detail": item.detail,
                }
                for item in sorted(record.items, key=lambda x: x.sort_order)
            ],
            "snapshot": record.snapshot,
        }

    async def _get_employee_info(self, employee_ids: list[int]) -> dict[int, dict]:
        """批量获取员工信息"""
        if not employee_ids:
            return {}
        stmt = select(Employee).where(
            and_(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return {
            e.id: {"name": e.name, "role": e.role}
            for e in result.scalars().all()
        }

    # ==================== 工资确认 ====================

    async def finalize(
        self,
        record_ids: list[int],
        user_id: int,
        notes: str | None = None,
    ) -> int:
        """确认工资条，状态 draft -> confirmed"""
        records = await self._get_records_by_ids(record_ids)
        if not records:
            raise NotFoundError("未找到指定的工资记录")

        # 账期检查（locked 允许工资条状态流转）
        for r in records:
            await self.period_service.check_payroll_writable(r.period)

        not_draft = [r for r in records if r.status != "draft"]
        if not_draft:
            raise ValidationError(
                f"以下记录非草稿状态，不可确认: {[r.id for r in not_draft]}"
            )

        now = datetime.now()
        for r in records:
            r.status = "confirmed"
            r.finalized_at = now
            r.finalized_by = user_id
            if notes:
                r.notes = notes

        await self.session.commit()
        logger.info(f"[Payroll] 确认 {len(records)} 条工资记录")
        return len(records)

    async def mark_paid(
        self, record_ids: list[int], user_id: int, paid_at: str | None = None
    ) -> int:
        """标记已发放，状态 confirmed -> paid"""
        records = await self._get_records_by_ids(record_ids)
        if not records:
            raise NotFoundError("未找到指定的工资记录")

        for r in records:
            await self.period_service.check_payroll_writable(r.period)

        not_confirmed = [r for r in records if r.status != "confirmed"]
        if not_confirmed:
            raise ValidationError(
                f"以下记录非已确认状态，不可标记发放: {[r.id for r in not_confirmed]}"
            )

        now = datetime.fromisoformat(paid_at) if paid_at else datetime.now()
        for r in records:
            r.status = "paid"
            r.paid_at = now
            r.paid_by = user_id

        await self.session.commit()
        logger.info(f"[Payroll] 标记 {len(records)} 条工资已发放")
        return len(records)

    async def _get_records_by_ids(self, record_ids: list[int]) -> list[PayrollRecord]:
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.id.in_(record_ids),
                PayrollRecord.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
