"""
存酒盘点单 API 路由
前缀: /api/v1/wines/stocktake
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.wine_stocktake import (
    StocktakeResponse,
    StocktakeItemResponse,
    StocktakeScanRequest,
    StocktakeScanResult,
    StocktakeCompleteRequest,
    StocktakeCreateRequest,
)
from app.repositories.wine_stocktake import WineStocktakeRepository
from app.services.wine_stocktake import (
    generate_monthly_stocktake,
    scan_bottle,
    complete_stocktake,
)
from app.utils.pagination import PageParams, PageResult
from app.utils.exceptions import NotFoundError, ForbiddenError
from app.utils.deps import make_response, get_store_id, get_user_id, require_role

router = APIRouter()


@router.post("/wines/stocktake")
async def create_stocktake(
    body: StocktakeCreateRequest, request: Request, db: AsyncSession = Depends(get_db),
):
    """手动创建盘点单（店长/老板）"""
    store_id = get_store_id(request)
    require_role(request, ["boss", "store_manager"])
    stocktake_id = await generate_monthly_stocktake(
        session=db, store_id=store_id, period=body.period,
    )
    if stocktake_id == 0:
        return make_response(message="当前无在库酒，无需盘点", data={"id": 0}, request=request)
    return make_response(message="盘点单已生成", data={"id": stocktake_id}, request=request)


@router.get("/wines/stocktake")
async def list_stocktakes(
    request: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """盘点单列表"""
    store_id = get_store_id(request)
    repo = WineStocktakeRepository(db, store_id)
    items, total = await repo.list_stocktakes(
        status=status, params=PageParams(page=page, page_size=page_size),
    )
    result = PageResult(
        items=[StocktakeResponse.model_validate(s).model_dump() for s in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return make_response(data=result.model_dump(), request=request)


@router.get("/wines/stocktake/{stocktake_id}")
async def get_stocktake_detail(
    stocktake_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
):
    """盘点单详情"""
    store_id = get_store_id(request)
    repo = WineStocktakeRepository(db, store_id)
    stocktake = await repo.get_by_id(stocktake_id)
    if not stocktake:
        raise NotFoundError("盘点单不存在")
    return make_response(data=StocktakeResponse.model_validate(stocktake).model_dump(), request=request)


@router.get("/wines/stocktake/{stocktake_id}/items")
async def list_stocktake_items(
    stocktake_id: uuid.UUID,
    request: Request,
    check_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """盘点单明细列表"""
    store_id = get_store_id(request)
    repo = WineStocktakeRepository(db, store_id)
    items, total = await repo.list_items(
        stocktake_id, check_status=check_status,
        params=PageParams(page=page, page_size=page_size),
    )
    result = PageResult(
        items=[StocktakeItemResponse.model_validate(i).model_dump() for i in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return make_response(data=result.model_dump(), request=request)


@router.post("/wines/stocktake/{stocktake_id}/scan")
async def scan_stocktake_bottle(
    stocktake_id: uuid.UUID,
    body: StocktakeScanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """扫码核对单瓶酒"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    result = await scan_bottle(
        session=db, store_id=store_id, stocktake_id=stocktake_id,
        bottle_label=body.bottle_label, actual_ml=body.actual_ml, user_id=user_id,
    )
    await db.commit()
    return make_response(data=result, request=request)


@router.post("/wines/stocktake/{stocktake_id}/complete")
async def complete_stocktake_api(
    stocktake_id: uuid.UUID,
    body: StocktakeCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """完成盘点"""
    store_id = get_store_id(request)
    require_role(request, ["boss", "store_manager"])
    result = await complete_stocktake(
        session=db, store_id=store_id, stocktake_id=stocktake_id, notes=body.notes,
    )
    await db.commit()
    return make_response(message="盘点已完成", data=result, request=request)
