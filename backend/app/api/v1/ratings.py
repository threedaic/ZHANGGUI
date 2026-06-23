"""
桌面评分码 API 路由
- POST   /api/v1/ratings         客人扫码提交评分（无需登录）
- GET    /api/v1/ratings         评分列表（需登录）
- GET    /api/v1/ratings/summary  评分汇总统计（需登录）
- GET    /api/v1/ratings/alerts   低分告警列表（需登录）
- PUT    /api/v1/ratings/{id}/respond  回复评分（需登录）
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.rating import RatingService
from app.schemas.rating import RatingCreate
from app.utils.security import decode_token
from app.utils.exceptions import UnauthorizedError, NotFoundError
from app.utils.deps import make_response
from loguru import logger

router = APIRouter()


def require_auth(request: Request):
    """认证依赖：从 Request 中解析 JWT，未登录则抛 401"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("请先登录")
    payload = decode_token(auth_header[7:])
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("登录已过期，请重新登录")
    return payload


@router.post("", response_model=dict)
async def submit_rating(data: RatingCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """
    客人扫码提交评分。
    无需登录，store_id 由 QR code H5 页面在请求体中携带。
    """
    service = RatingService(db)
    rating = await service.submit_rating(data)
    return make_response(message="感谢您的评价", data=rating.model_dump(), request=request)


@router.get("", response_model=dict)
async def list_ratings(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _payload: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    store_id = getattr(request.state, "store_id", None)
    if not store_id:
        raise UnauthorizedError("无法确定门店")

    service = RatingService(db)
    result = await service.list_ratings(store_id, page, page_size)
    return make_response(data=result.model_dump(), request=request)


@router.get("/summary", response_model=dict)
async def get_summary(
    request: Request,
    _payload: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    store_id = getattr(request.state, "store_id", None)
    if not store_id:
        raise UnauthorizedError("无法确定门店")

    service = RatingService(db)
    summary = await service.get_summary(store_id)
    return make_response(data=summary.model_dump(), request=request)


@router.get("/alerts", response_model=dict)
async def get_alerts(
    request: Request,
    _payload: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    store_id = getattr(request.state, "store_id", None)
    if not store_id:
        raise UnauthorizedError("无法确定门店")

    service = RatingService(db)
    alerts = await service.get_alerts(store_id)
    return make_response(data=[a.model_dump() for a in alerts], request=request)


@router.put("/{rating_id}/respond", response_model=dict)
async def respond_to_rating(
    rating_id: uuid.UUID,
    request: Request,
    response_text: str = Query(..., min_length=1, description="回复内容"),
    _payload: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    store_id = getattr(request.state, "store_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not store_id or not user_id:
        raise UnauthorizedError("无法确定身份")

    service = RatingService(db)
    rating = await service.respond_to_rating(store_id, rating_id, response_text, user_id)
    if not rating:
        raise NotFoundError("评分记录不存在")
    return make_response(data=rating.model_dump(), request=request)
