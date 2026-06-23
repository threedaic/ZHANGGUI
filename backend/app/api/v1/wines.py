"""
存酒管理 API 路由
前缀: /api/v1
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.wine import (
    WineCreate,
    WineResponse,
    WineStaffRetrieve,
    WineSelfRetrieve,
    WineRetrieveResponse,
    WineH5Info,
    WineH5ConfirmRequest,
    InventoryCheckItem,
    WineBatchCreate,
)
from app.repositories.wine import WineRepository
from app.services.wine import store_wine, staff_retrieve, self_retrieve
from app.utils.pagination import PageParams, PageResult
from app.utils.exceptions import NotFoundError, ForbiddenError
from app.utils.deps import make_response
from loguru import logger

router = APIRouter()


def _get_store_id(request: Request) -> int:
    store_id = getattr(request.state, "store_id", None)
    if store_id is None:
        raise ForbiddenError("无法获取门店信息")
    return store_id


async def _safe_commit(db: AsyncSession, request: Request = None, after_commit=None):
    """提交事务并安全执行 after_commit 钩子。

    commit 本身失败会抛出异常（由全局 handler 处理），
    after_commit 钩子失败仅记录日志不阻断响应。
    """
    await db.commit()  # commit 失败会自然抛出，不吞异常
    if after_commit:
        try:
            await after_commit()
        except Exception as e:
            logger.warning(f"after_commit event error: {e}")


# ==================== 存酒 ====================

@router.post("")
async def create_wine(body: WineCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """服务员存酒：填表 → 出标签 + 发短信"""
    store_id = _get_store_id(request)
    wine = await store_wine(
        session=db, store_id=store_id,
        customer_name=body.customer_name,
        phone=body.phone,
        wine_name=body.wine_name,
        remaining_ml=body.remaining_ml,
        quantity=body.quantity,
        cabinet_no=body.cabinet_no,
        notes=body.notes,
    )
    result = WineResponse.model_validate(wine).model_dump()
    await _safe_commit(db)
    return make_response(data=result, request=request)


@router.post("/batch")
async def create_wine_batch(body: WineBatchCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """一次存多种酒"""
    store_id = _get_store_id(request)
    results = []
    for item in body.wines:
        for _ in range(max(item.quantity, 1)):
            wine = await store_wine(
                session=db, store_id=store_id,
                customer_name=body.customer_name,
                phone=body.phone,
                wine_name=item.wine_name,
                remaining_ml=item.remaining_ml,
                quantity=1,
                notes=body.notes,
            )
            results.append(wine)
    await _safe_commit(db)
    return make_response(data={
        "count": len(results),
        "bottle_labels": [w.bottle_label for w in results],
    }, request=request)


# ==================== 列表查询 ====================

@router.get("")
async def list_wines(
    request: Request,
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    search_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """存酒列表，支持状态筛选、关键词搜索、分页"""
    store_id = _get_store_id(request)
    repo = WineRepository(db, store_id)
    items, total = await repo.list_wines(
        status=status, keyword=keyword, search_type=search_type,
        params=PageParams(page=page, page_size=page_size),
    )
    result = PageResult(
        items=[WineResponse.model_validate(w).model_dump() for w in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return make_response(data=result.model_dump(), request=request)


# ==================== H5 查酒信息（公开） ====================

@router.get("/h5/{bottle_label}")
async def h5_wine_info(bottle_label: str, request: Request, db: AsyncSession = Depends(get_db)):
    """客人短信链接查看存酒信息"""
    from sqlalchemy import select
    from app.models.wine_storage import WineStorage
    stmt = select(WineStorage).where(WineStorage.bottle_label == bottle_label)
    result = await db.execute(stmt)
    wine = result.scalar_one_or_none()
    if not wine:
        raise NotFoundError("未找到该存酒记录")
    return make_response(data=WineH5Info.model_validate(wine).model_dump(), request=request)


# ==================== H5 客人自助取酒 ====================

@router.post("/h5/confirm")
async def h5_confirm_retrieve(body: WineH5ConfirmRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """客人自助取酒"""
    wine = await self_retrieve(
        session=db, bottle_label=body.bottle_label,
        retrieve_ml=body.retrieve_ml, table_no=body.table_no,
    )
    await _safe_commit(db)
    return make_response(message="已通知服务员，请稍候",
        data={"bottle_label": body.bottle_label, "status": wine.status, "remaining_ml": wine.remaining_ml}, request=request)


# ==================== 公开：客人查自己的存酒 ====================

@router.get("/guest")
async def guest_my_wines(request: Request, phone: str = Query(...), db: AsyncSession = Depends(get_db)):
    """客人输入手机号查看所有存酒"""
    from sqlalchemy import select
    from app.models.wine_storage import WineStorage
    stmt = select(WineStorage).where(WineStorage.phone.contains(phone)).order_by(WineStorage.date_stored.desc())
    result = await db.execute(stmt)
    wines = result.scalars().all()
    return make_response(data=[
        {
            "bottle_label": w.bottle_label,
            "wine_name": w.wine_name,
            "initial_ml": w.initial_ml,
            "remaining_ml": w.remaining_ml,
            "date_stored": w.date_stored,
            "status": w.status,
        }
        for w in wines
    ], request=request)


# ==================== 服务员取酒 ====================

@router.post("/retrieve")
async def retrieve_wine_api(
    body: WineStaffRetrieve, request: Request, db: AsyncSession = Depends(get_db),
):
    """服务员取酒：输瓶身码 + 取酒量 + 桌号 → 扣减"""
    store_id = _get_store_id(request)
    user_id = getattr(request.state, "user_id", None)
    wine = await staff_retrieve(
        session=db, store_id=store_id,
        bottle_label=body.bottle_label,
        retrieve_ml=body.retrieve_ml,
        table_no=body.table_no,
        user_id=user_id,
    )
    result = WineRetrieveResponse.model_validate(wine).model_dump()
    await _safe_commit(db)
    return make_response(data=result, request=request)


# ==================== 盘点 ====================

@router.get("/inventory/summary")
async def inventory_summary(request: Request, db: AsyncSession = Depends(get_db)):
    """存酒盘点汇总"""
    store_id = _get_store_id(request)
    repo = WineRepository(db, store_id)
    summary = await repo.get_inventory()
    return make_response(data=summary, request=request)


@router.get("/inventory/items")
async def inventory_items(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """盘点明细"""
    store_id = _get_store_id(request)
    repo = WineRepository(db, store_id)
    items, total = await repo.list_wines(
        status="stored", params=PageParams(page=page, page_size=page_size),
    )
    result = PageResult(
        items=[InventoryCheckItem(
            bottle_label=w.bottle_label, customer_name=w.customer_name,
            wine_name=w.wine_name, remaining_ml=w.remaining_ml, status=w.status,
        ).model_dump() for w in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return make_response(data=result.model_dump(), request=request)


# ==================== 详情 ====================

@router.get("/{wine_id}")
async def get_wine(wine_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """单条存酒记录详情"""
    store_id = _get_store_id(request)
    repo = WineRepository(db, store_id)
    wine = await repo.get_by_id(wine_id)
    if not wine:
        raise NotFoundError("存酒记录不存在")
    return make_response(data=WineResponse.model_validate(wine).model_dump(), request=request)
