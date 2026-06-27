"""
KPI 考核数据访问层
封装 SQL 查询，返回 ORM 对象。
"""
import uuid
from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.kpi import KPITemplate, KPIScore, KPIResult, KPIAppeal
from app.models.employee import Employee
from app.utils.pagination import PageParams, paginate


class KPIRepository:
    """KPI 考核 Repository"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ==================== 模板 ====================

    async def get_templates(
        self, role: str | None = None, is_active: bool = True
    ) -> list[KPITemplate]:
        stmt = select(KPITemplate).where(
            and_(
                KPITemplate.store_id == self.store_id,
                KPITemplate.is_active == is_active,
            )
        )
        if role:
            stmt = stmt.where(KPITemplate.role == role)
        stmt = stmt.order_by(KPITemplate.role, KPITemplate.dimension)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 评分 ====================

    async def get_scores(
        self,
        employee_id: uuid.UUID | None = None,
        period: str | None = None,
        dimension: str | None = None,
    ) -> list[KPIScore]:
        stmt = select(KPIScore).where(KPIScore.store_id == self.store_id)
        if employee_id:
            stmt = stmt.where(KPIScore.employee_id == employee_id)
        if period:
            stmt = stmt.where(KPIScore.period == period)
        if dimension:
            stmt = stmt.where(KPIScore.dimension == dimension)
        stmt = stmt.order_by(KPIScore.employee_id, KPIScore.dimension)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_scores(self, scores: list[KPIScore]) -> list[KPIScore]:
        """批量 upsert 评分数据。存在则更新，不存在则插入。"""
        for score in scores:
            existing = await self.session.execute(
                select(KPIScore).where(
                    and_(
                        KPIScore.employee_id == score.employee_id,
                        KPIScore.period == score.period,
                        KPIScore.dimension == score.dimension,
                    )
                )
            )
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                existing_obj.raw_value = score.raw_value
                existing_obj.raw_description = score.raw_description
                existing_obj.normalized_score = score.normalized_score
                existing_obj.weight = score.weight
                existing_obj.weighted_score = score.weighted_score
                existing_obj.data_source = score.data_source
                existing_obj.source_reference = score.source_reference
                existing_obj.calculated_at = score.calculated_at
            else:
                self.session.add(score)
        await self.session.flush()
        return scores

    # ==================== 结果 ====================

    async def get_results(
        self,
        employee_id: uuid.UUID | None = None,
        period: str | None = None,
        status: str | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[KPIResult], int]:
        stmt = select(KPIResult).where(KPIResult.store_id == self.store_id)
        if employee_id:
            stmt = stmt.where(KPIResult.employee_id == employee_id)
        if period:
            stmt = stmt.where(KPIResult.period == period)
        if status:
            stmt = stmt.where(KPIResult.status == status)
        stmt = stmt.order_by(KPIResult.total_score.desc())

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_result_by_id(self, result_id: uuid.UUID) -> KPIResult | None:
        stmt = select(KPIResult).where(
            and_(KPIResult.id == result_id, KPIResult.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_result(self, result: KPIResult) -> KPIResult:
        existing = await self.session.execute(
            select(KPIResult).where(
                and_(
                    KPIResult.employee_id == result.employee_id,
                    KPIResult.period == result.period,
                )
            )
        )
        existing_obj = existing.scalar_one_or_none()
        if existing_obj:
            existing_obj.total_score = result.total_score
            existing_obj.coefficient = result.coefficient
            existing_obj.coefficient_reason = result.coefficient_reason
            existing_obj.rank_in_store = result.rank_in_store
            existing_obj.status = result.status
        else:
            self.session.add(result)
        await self.session.flush()
        return result

    async def update_result(self, result_id: uuid.UUID, **kwargs) -> KPIResult | None:
        result = await self.get_result_by_id(result_id)
        if not result:
            return None
        for key, value in kwargs.items():
            if hasattr(result, key):
                setattr(result, key, value)
        await self.session.flush()
        return result

    async def update_ranks(self, period: str):
        """更新门店内排名"""
        results, _ = await self.get_results(period=period)
        sorted_results = sorted(results, key=lambda r: r.total_score, reverse=True)
        for rank, r in enumerate(sorted_results, start=1):
            r.rank_in_store = rank
        await self.session.flush()

    # ==================== 申诉 ====================

    async def create_appeal(self, appeal: KPIAppeal) -> KPIAppeal:
        self.session.add(appeal)
        await self.session.flush()
        return appeal

    async def get_appeals(
        self,
        employee_id: uuid.UUID | None = None,
        status: str | None = None,
        result_id: uuid.UUID | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[KPIAppeal], int]:
        stmt = select(KPIAppeal).where(KPIAppeal.store_id == self.store_id)
        if employee_id:
            stmt = stmt.where(KPIAppeal.employee_id == employee_id)
        if status:
            stmt = stmt.where(KPIAppeal.status == status)
        if result_id:
            stmt = stmt.where(KPIAppeal.result_id == result_id)
        stmt = stmt.order_by(KPIAppeal.created_at.desc())

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_appeal_by_id(self, appeal_id: uuid.UUID) -> KPIAppeal | None:
        stmt = select(KPIAppeal).where(
            and_(KPIAppeal.id == appeal_id, KPIAppeal.store_id == self.store_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_appeal(self, appeal_id: uuid.UUID, **kwargs) -> KPIAppeal | None:
        appeal = await self.get_appeal_by_id(appeal_id)
        if not appeal:
            return None
        for key, value in kwargs.items():
            if hasattr(appeal, key):
                setattr(appeal, key, value)
        await self.session.flush()
        return appeal

    # ==================== 辅助 ====================

    async def get_employee_info(
        self, employee_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict]:
        """批量获取员工信息，返回 {employee_id: {name, role}}"""
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
