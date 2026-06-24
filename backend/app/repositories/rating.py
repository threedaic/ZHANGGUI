"""
评分码数据访问层
"""
import uuid
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rating import GuestRating
from app.utils.pagination import PageParams, paginate


class RatingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rating: GuestRating) -> GuestRating:
        self.session.add(rating)
        await self.session.commit()
        await self.session.refresh(rating)
        return rating

    async def get_by_id(self, rating_id: uuid.UUID, store_id: uuid.UUID) -> GuestRating | None:
        result = await self.session.execute(
            select(GuestRating).where(
                and_(GuestRating.id == rating_id, GuestRating.store_id == store_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_store(self, store_id: uuid.UUID, params: PageParams):
        base = select(GuestRating).where(GuestRating.store_id == store_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            base.order_by(GuestRating.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        items = result.scalars().all()

        return paginate(items, total, params)

    async def get_alerts(self, store_id: uuid.UUID, limit: int = 50):
        result = await self.session.execute(
            select(GuestRating)
            .where(
                and_(GuestRating.store_id == store_id, GuestRating.is_low_score.is_(True))
            )
            .order_by(GuestRating.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_summary(self, store_id: uuid.UUID) -> dict | None:
        result = await self.session.execute(
            select(
                func.count(GuestRating.id).label("total"),
                func.coalesce(func.avg(GuestRating.overall_score), 0).label("avg_overall"),
                func.coalesce(
                    func.count().filter(GuestRating.is_low_score.is_(True)), 0
                ).label("low_count"),
                func.coalesce(func.avg(GuestRating.food_quality), 0).label("avg_food_quality"),
                func.coalesce(func.avg(GuestRating.food_speed), 0).label("avg_food_speed"),
                func.coalesce(func.avg(GuestRating.drink_quality), 0).label("avg_drink_quality"),
                func.coalesce(func.avg(GuestRating.drink_speed), 0).label("avg_drink_speed"),
                func.coalesce(func.avg(GuestRating.service_attitude), 0).label("avg_service_attitude"),
                func.coalesce(func.avg(GuestRating.service_speed), 0).label("avg_service_speed"),
                func.coalesce(func.avg(GuestRating.cleanliness), 0).label("avg_cleanliness"),
            ).where(GuestRating.store_id == store_id)
        )
        row = result.one_or_none()
        if not row or row.total == 0:
            return None

        return {
            "total_count": row.total,
            "avg_overall": round(float(row.avg_overall), 1),
            "low_score_count": row.low_count,
            "dimension_scores": {
                "food_quality": round(float(row.avg_food_quality), 1),
                "food_speed": round(float(row.avg_food_speed), 1),
                "drink_quality": round(float(row.avg_drink_quality), 1),
                "drink_speed": round(float(row.avg_drink_speed), 1),
                "service_attitude": round(float(row.avg_service_attitude), 1),
                "service_speed": round(float(row.avg_service_speed), 1),
                "cleanliness": round(float(row.avg_cleanliness), 1),
            },
        }

    async def update_response(
        self, rating_id: uuid.UUID, store_id: uuid.UUID, response_text: str, user_id: uuid.UUID
    ) -> GuestRating | None:
        from datetime import datetime

        rating = await self.get_by_id(rating_id, store_id)
        if not rating:
            return None
        rating.store_response = response_text
        rating.response_by = user_id
        rating.responded_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(rating)
        return rating
