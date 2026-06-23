"""
处罚通知 Repository — 数据访问层
"""
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.penalty_notice import PenaltyNotice
from app.utils.pagination import PageParams


class PenaltyRepository:
    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    async def create(self, notice: PenaltyNotice) -> PenaltyNotice:
        self.session.add(notice)
        await self.session.flush()
        await self.session.refresh(notice)
        return notice

    async def get_by_id(self, notice_id: int) -> PenaltyNotice | None:
        stmt = select(PenaltyNotice).where(
            and_(
                PenaltyNotice.id == notice_id,
                PenaltyNotice.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_notices(
        self,
        penalty_type: str | None = None,
        status: str | None = None,
        employee_id: int | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[PenaltyNotice], int]:
        conditions = [PenaltyNotice.store_id == self.store_id]
        if penalty_type:
            conditions.append(PenaltyNotice.penalty_type == penalty_type)
        if status:
            conditions.append(PenaltyNotice.status == status)
        if employee_id:
            conditions.append(PenaltyNotice.employee_id == employee_id)

        stmt = (
            select(PenaltyNotice)
            .where(and_(*conditions))
            .order_by(PenaltyNotice.created_at.desc())
        )

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_status(self, notice_id: int, status: str) -> bool:
        from sqlalchemy import update
        stmt = (
            update(PenaltyNotice)
            .where(
                and_(
                    PenaltyNotice.id == notice_id,
                    PenaltyNotice.store_id == self.store_id,
                )
            )
            .values(status=status)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, notice_id: int) -> bool:
        notice = await self.get_by_id(notice_id)
        if not notice or notice.status != "draft":
            return False
        await self.session.delete(notice)
        await self.session.flush()
        return True

    async def update(self, notice_id: int, **kwargs) -> PenaltyNotice | None:
        notice = await self.get_by_id(notice_id)
        if not notice or notice.status != "draft":
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(notice, key):
                setattr(notice, key, value)
        await self.session.flush()
        await self.session.refresh(notice)
        return notice
