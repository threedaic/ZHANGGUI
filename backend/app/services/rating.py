"""
桌面评分码业务逻辑
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rating import GuestRating
from app.repositories.rating import RatingRepository
from app.services.notification_service import NotificationService
from app.schemas.rating import RatingCreate, RatingItem, RatingSummary, RatingAlert
from app.utils.pagination import PageParams, PageResult
from loguru import logger


class RatingService:
    def __init__(self, session: AsyncSession):
        self.repo = RatingRepository(session)
        self.session = session

    async def submit_rating(self, data: RatingCreate) -> RatingItem:
        scores = [
            data.food_quality, data.food_speed, data.drink_quality,
            data.drink_speed, data.service_attitude, data.service_speed,
            data.cleanliness,
        ]
        overall = round(sum(scores) / len(scores), 1)
        is_low = overall <= 2.0

        rating = GuestRating(
            store_id=data.store_id,
            table_no=data.table_no,
            food_quality=data.food_quality,
            food_speed=data.food_speed,
            drink_quality=data.drink_quality,
            drink_speed=data.drink_speed,
            service_attitude=data.service_attitude,
            service_speed=data.service_speed,
            cleanliness=data.cleanliness,
            overall_score=overall,
            comment=data.comment,
            source=data.source,
            is_low_score=is_low,
            created_at=datetime.now(),
        )

        rating = await self.repo.create(rating)

        if is_low:
            logger.warning(f"低分评分: 桌{data.table_no} 均分{overall}")
            detail = (
                f"> 桌号: **{data.table_no}**\n"
                f"> 均分: **{overall}**\n"
                f"> 餐品品质: {data.food_quality} | 出餐速度: {data.food_speed}\n"
                f"> 酒水品质: {data.drink_quality} | 出酒速度: {data.drink_speed}\n"
                f"> 服务态度: {data.service_attitude} | 服务速度: {data.service_speed}\n"
                f"> 环境卫生: {data.cleanliness}\n"
            )
            if data.comment:
                detail += f"> 客人留言: {data.comment}\n"
            detail += "\n<font color=\"warning\">请注意跟进</font>"

            notif = NotificationService(self.session, data.store_id)
            await notif.send_alert("rating_alert", f"低分评分预警 - {data.table_no}桌", detail)

            rating.notified = True
            rating.notified_at = datetime.now()
            await self.session.commit()

        return RatingItem.model_validate(rating)

    async def get_summary(self, store_id: int) -> RatingSummary:
        data = await self.repo.get_summary(store_id)
        if not data:
            return RatingSummary(
                total_count=0,
                avg_overall=0.0,
                low_score_count=0,
                dimension_scores={
                    "food_quality": 0.0, "food_speed": 0.0,
                    "drink_quality": 0.0, "drink_speed": 0.0,
                    "service_attitude": 0.0, "service_speed": 0.0,
                    "cleanliness": 0.0,
                },
            )
        return RatingSummary(**data)

    async def get_alerts(self, store_id: int) -> list[RatingAlert]:
        alerts = await self.repo.get_alerts(store_id)
        return [RatingAlert.model_validate(a) for a in alerts]

    async def list_ratings(
        self, store_id: int, page: int = 1, page_size: int = 20
    ) -> PageResult[RatingItem]:
        result = await self.repo.list_by_store(store_id, PageParams(page=page, page_size=page_size))
        return PageResult(
            items=[RatingItem.model_validate(r) for r in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
        )

    async def respond_to_rating(
        self, store_id: int, rating_id: int, response_text: str, user_id: int
    ) -> RatingItem | None:
        rating = await self.repo.update_response(rating_id, store_id, response_text, user_id)
        if not rating:
            return None
        return RatingItem.model_validate(rating)
