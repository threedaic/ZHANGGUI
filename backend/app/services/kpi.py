"""
KPI 考核业务逻辑层
- 5 维度加权计算
- 系数换算
- 申诉流程
"""
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.kpi import KPIScore, KPIResult, KPIAppeal, KPITemplate
from app.repositories.kpi import KPIRepository
from app.utils.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
    ValidationError,
)


class KPIService:
    """KPI 考核 Service。每个请求创建新实例。"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.repo = KPIRepository(session, store_id)
        self.session = session
        self.store_id = store_id

    # ==================== 模板 ====================

    async def get_templates(self, role: str | None = None) -> list[KPITemplate]:
        return await self.repo.get_templates(role=role)

    # ==================== 评分计算 ====================

    async def calculate_scores(
        self, employee_ids: list[uuid.UUID], period: str
    ) -> list[KPIResult]:
        """
        5 维度加权计算。
        流程:
          1. 读取该岗位的 KPI 模板 (权重配置)
          2. 逐维度获取 raw_value 并归一化 (0-100)
          3. 加权求和 → total_score
          4. 系数换算 (0.8 / 1.0 / 1.2)
          5. 写入 kpi_scores + 更新 kpi_results
        """
        if not employee_ids:
            raise ValidationError("至少需要一位员工")

        employee_info = await self.repo.get_employee_info(employee_ids)
        results: list[KPIResult] = []

        for emp_id in employee_ids:
            emp = employee_info.get(emp_id)
            if not emp:
                logger.warning(f"员工 {emp_id} 不在当前门店，跳过")
                continue

            role = emp["role"]
            templates = await self.repo.get_templates(role=role)

            if not templates:
                raise NotFoundError(f"岗位 '{role}' 未配置 KPI 模板")

            # 5 维度逐项计算
            dimension_scores: list[KPIScore] = []
            total = 0.0
            weight_sum = 0.0

            for tpl in templates:
                raw_value = await self._fetch_raw_value(emp_id, tpl, period)
                normalized = self._normalize(raw_value, tpl)
                weighted = round(normalized * tpl.weight, 2)

                score = KPIScore(
                    employee_id=emp_id,
                    store_id=self.store_id,
                    period=period,
                    dimension=tpl.dimension,
                    raw_value=raw_value,
                    raw_description=f"自动采集: {tpl.data_source}",
                    normalized_score=normalized,
                    weight=tpl.weight,
                    weighted_score=weighted,
                    data_source=tpl.data_source,
                    calculated_at=datetime.now(),
                )
                dimension_scores.append(score)
                total += weighted
                weight_sum += tpl.weight

            # 归一化总分为 0-100 制
            if weight_sum > 0:
                total_score = round(total / weight_sum * 100, 2)
            else:
                total_score = 0.0

            # 系数换算
            coefficient, reason = self._coefficient(total_score)

            result = KPIResult(
                employee_id=emp_id,
                store_id=self.store_id,
                period=period,
                total_score=total_score,
                coefficient=coefficient,
                coefficient_reason=reason,
                status="pending",
            )

            # 持久化
            await self.repo.upsert_scores(dimension_scores)
            await self.repo.upsert_result(result)
            results.append(result)

        # 更新排名
        await self.repo.update_ranks(period)
        await self.session.commit()
        return results

    async def _fetch_raw_value(
        self, employee_id: uuid.UUID, template: KPITemplate, period: str
    ) -> float | None:
        """
        自动从数据源拉取原始值。
        根据 template.data_source 决定数据来源：
          - attendance: 从考勤表取出勤率
          - rating: 从评分表取均分
          - revenue: 从营收表取业绩
          - manual: 需手动填入
        """
        if template.data_source == "attendance":
            from app.repositories.attendance import AttendanceRepository
            year, month = int(period[:4]), int(period[5:7])
            att_repo = AttendanceRepository(self.session, self.store_id)
            stats = await att_repo.get_monthly_attendance_stats(employee_id, year, month)
            if stats["total_days"] == 0:
                return None
            return round(stats["present_days"] / stats["total_days"] * 100, 2)

        elif template.data_source == "rating":
            from app.models.rating import GuestRating
            from sqlalchemy import select, func, and_

            year, month = int(period[:4]), int(period[5:7])
            stmt = (
                select(func.avg(GuestRating.overall_score))
                .where(
                    and_(
                        GuestRating.employee_id == employee_id,
                        GuestRating.store_id == self.store_id,
                        func.date_trunc("month", GuestRating.created_at) == f"{year}-{month:02d}-01",
                    )
                )
            )
            result = await self.session.execute(stmt)
            avg_score = result.scalar()
            return round(float(avg_score), 2) if avg_score else None

        elif template.data_source == "revenue":
            from app.models.revenue import DailyRevenue
            from sqlalchemy import select, func, and_

            year, month = int(period[:4]), int(period[5:7])
            stmt = (
                select(func.sum(DailyRevenue.total_revenue))
                .where(
                    and_(
                        DailyRevenue.store_id == self.store_id,
                        func.date_trunc("month", DailyRevenue.date) == f"{year}-{month:02d}-01",
                    )
                )
            )
            result = await self.session.execute(stmt)
            total_rev = result.scalar() or 0
            return round(float(total_rev), 2)

        # manual / other → None, 等待手动输入
        return None

    def _normalize(self, raw_value: float | None, template: KPITemplate) -> float:
        """将原始值归一化到 0-100 分"""
        if raw_value is None:
            return 0.0

        formula_config = {}
        try:
            import json
            if template.formula_config and template.formula_config != "{}":
                formula_config = json.loads(template.formula_config)
        except (json.JSONDecodeError, TypeError):
            pass

        formula_type = template.formula_type

        if formula_type == "ratio":
            # 比例型：raw_value 已是 0-100 (如出勤率 95% → 95)
            return min(max(round(raw_value, 2), 0), 100)

        elif formula_type == "linear":
            # 线性型：min→0 分, max→100 分
            v_min = formula_config.get("min", 0)
            v_max = formula_config.get("max", 100)
            if v_max == v_min:
                return 50.0
            return min(max(round((raw_value - v_min) / (v_max - v_min) * 100, 2), 0), 100)

        elif formula_type == "step":
            # 阶梯型：config 中的阈值映射
            thresholds = formula_config.get("thresholds", [])
            for step in sorted(thresholds, key=lambda s: s.get("value", 0), reverse=True):
                if raw_value >= step.get("value", 0):
                    return float(step.get("score", 0))
            return 0.0

        # 默认 ratio
        return min(max(round(raw_value, 2), 0), 100)

    def _coefficient(self, total_score: float) -> tuple[float, str]:
        """总分 → 绩效系数"""
        if total_score >= 90:
            return 1.2, "A级：表现优异"
        elif total_score >= 75:
            return 1.0, "B级：达到预期"
        elif total_score >= 60:
            return 0.9, "C级：需要改进"
        else:
            return 0.8, "D级：不及格"

    # ==================== 查询 ====================

    async def get_employee_results(
        self, employee_id: uuid.UUID, period: str | None = None
    ) -> list[KPIResult]:
        results, _ = await self.repo.get_results(
            employee_id=employee_id, period=period
        )
        return results

    async def get_store_results(
        self, period: str, page_size: int = 20, page: int = 1
    ) -> dict:
        """门店月度 KPI 汇总"""
        from app.utils.pagination import PageParams
        params = PageParams(page=page, page_size=page_size)
        results, total = await self.repo.get_results(period=period, page=params)

        if not results:
            return {"period": period, "store_avg": 0.0, "store_count": 0, "results": []}

        employee_ids = [r.employee_id for r in results]
        emp_info = await self.repo.get_employee_info(employee_ids)

        # 一次取回所有员工的维度评分，按 employee_id 分组，避免 N+1
        all_scores = await self.repo.get_scores(period=period)
        scores_by_emp: dict[int, list[KPIScore]] = {}
        for s in all_scores:
            scores_by_emp.setdefault(s.employee_id, []).append(s)

        details = []
        score_sum = 0.0
        for r in results:
            scores = scores_by_emp.get(r.employee_id, [])
            emp = emp_info.get(r.employee_id, {"name": "", "role": ""})
            details.append({
                "id": r.id,
                "employee_id": r.employee_id,
                "store_id": r.store_id,
                "period": r.period,
                "total_score": r.total_score,
                "coefficient": r.coefficient,
                "coefficient_reason": r.coefficient_reason,
                "rank_in_store": r.rank_in_store,
                "status": r.status,
                "confirmed_by": r.confirmed_by,
                "confirmed_at": r.confirmed_at,
                "created_at": r.created_at,
                "employee_name": emp["name"],
                "employee_role": emp["role"],
                "dimensions": [
                    {
                        "id": s.id,
                        "employee_id": s.employee_id,
                        "store_id": s.store_id,
                        "period": s.period,
                        "dimension": s.dimension,
                        "raw_value": s.raw_value,
                        "raw_description": s.raw_description,
                        "normalized_score": s.normalized_score,
                        "weight": s.weight,
                        "weighted_score": s.weighted_score,
                        "data_source": s.data_source,
                        "source_reference": s.source_reference,
                        "calculated_at": s.calculated_at,
                    }
                    for s in scores
                ],
            })
            score_sum += r.total_score

        return {
            "period": period,
            "store_avg": round(score_sum / len(results), 2),
            "store_count": len(results),
            "results": details,
        }

    # ==================== 确认 ====================

    async def confirm_result(
        self, result_id: uuid.UUID, user_id: uuid.UUID, coefficient: float | None = None, reason: str | None = None
    ) -> KPIResult:
        result = await self.repo.get_result_by_id(result_id)
        if not result:
            raise NotFoundError("KPI 结果不存在")
        if result.status == "confirmed":
            raise ConflictError("该结果已确认，不能重复确认")

        if coefficient is not None:
            result.coefficient = coefficient
        if reason is not None:
            result.coefficient_reason = reason

        result.status = "confirmed"
        result.confirmed_by = user_id
        result.confirmed_at = datetime.now()

        await self.session.flush()
        await self.session.commit()
        return result

    # ==================== 申诉 ====================

    async def create_appeal(
        self, employee_id: uuid.UUID, result_id: uuid.UUID, dimension: str | None,
        reason: str, evidence: str | None = None
    ) -> KPIAppeal:
        """员工发起申诉"""
        result = await self.repo.get_result_by_id(result_id)
        if not result:
            raise NotFoundError("KPI 结果不存在")
        if result.employee_id != employee_id:
            raise ForbiddenError("只能申诉自己的 KPI 结果")
        if result.status != "confirmed":
            raise ValidationError("只能申诉已确认的 KPI 结果")

        # 检查是否有未处理的申诉
        existing_appeals, _ = await self.repo.get_appeals(
            employee_id=employee_id, result_id=result_id, status="pending"
        )
        if existing_appeals:
            raise ConflictError("该结果已有待处理的申诉")

        appeal = KPIAppeal(
            result_id=result_id,
            employee_id=employee_id,
            dimension=dimension,
            reason=reason,
            evidence=evidence,
            status="pending",
        )
        return await self.repo.create_appeal(appeal)

    async def review_appeal(
        self, appeal_id: uuid.UUID, reviewer_id: uuid.UUID, action: str, resolution: str | None = None
    ) -> KPIAppeal:
        """店长审批申诉"""
        appeal = await self.repo.get_appeal_by_id(appeal_id)
        if not appeal:
            raise NotFoundError("申诉不存在")
        if appeal.status != "pending":
            raise ConflictError("该申诉已处理")

        appeal.status = action  # "approved" / "rejected"
        appeal.reviewed_by = reviewer_id
        appeal.resolution = resolution
        appeal.resolved_at = datetime.now()

        await self.session.flush()
        await self.session.commit()
        return appeal

    async def get_appeals_for_review(
        self, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> dict:
        """店长查看申诉列表（按员工筛选、按状态筛选）"""
        from app.utils.pagination import PageParams
        params = PageParams(page=page, page_size=page_size)
        appeals, total = await self.repo.get_appeals(status=status, page=params)

        items = []
        for a in appeals:
            result = await self.repo.get_result_by_id(a.result_id)
            emp_info = await self.repo.get_employee_info([a.employee_id])
            emp = emp_info.get(a.employee_id, {"name": ""})
            items.append({
                "id": a.id,
                "result_id": a.result_id,
                "employee_id": a.employee_id,
                "dimension": a.dimension,
                "reason": a.reason,
                "evidence": a.evidence,
                "status": a.status,
                "reviewed_by": a.reviewed_by,
                "resolution": a.resolution,
                "resolved_at": a.resolved_at,
                "created_at": a.created_at,
                "employee_name": emp["name"],
                "period": result.period if result else "",
                "current_score": result.total_score if result else 0.0,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def get_employee_appeals(
        self, employee_id: uuid.UUID, status: str | None = None,
        page: int = 1, page_size: int = 20
    ) -> dict:
        """Get appeals for a specific employee only (M-008 fix)."""
        from app.utils.pagination import PageParams
        params = PageParams(page=page, page_size=page_size)
        appeals, total = await self.repo.get_appeals(
            employee_id=employee_id, status=status, page=params
        )

        items = []
        for a in appeals:
            result = await self.repo.get_result_by_id(a.result_id)
            items.append({
                "id": a.id,
                "result_id": a.result_id,
                "employee_id": a.employee_id,
                "dimension": a.dimension,
                "reason": a.reason,
                "evidence": a.evidence,
                "status": a.status,
                "reviewed_by": a.reviewed_by,
                "resolution": a.resolution,
                "resolved_at": a.resolved_at,
                "created_at": a.created_at,
                "period": result.period if result else "",
                "current_score": result.total_score if result else 0.0,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
