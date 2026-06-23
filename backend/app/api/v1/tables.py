"""桌位管理 API 路由。

前缀: /api/v1/tables (由 main.py 提供)

完整路径映射:
  GET  ""              → /api/v1/tables          (桌位列表)
  POST ""              → /api/v1/tables          (新增桌位)
  GET  "/{table_id}"   → /api/v1/tables/{id}     (桌位详情)
  PUT  "/{table_id}"   → /api/v1/tables/{id}     (更新桌位)
  DELETE "/{table_id}" → /api/v1/tables/{id}     (删除桌位)
"""

import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.booking import TableCreate, TableUpdate, TableResponse
from app.services.booking import TableService
from app.utils.pagination import PageParams
from app.utils.deps import get_store_id, make_response

router = APIRouter()


# ==================== 桌位 CRUD ====================

@router.get("")
async def list_tables(
    request: Request,
    area: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """查询桌位列表，支持按区域筛选和分页。"""
    store_id = get_store_id(request)
    svc = TableService(db)
    result = await svc.list(store_id, area=area, params=PageParams(page=page, page_size=page_size))
    return make_response(data=result.model_dump(), request=request)


@router.post("")
async def create_table(
    body: TableCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """新增桌位。"""
    store_id = get_store_id(request)
    svc = TableService(db)
    table = await svc.create(store_id, body)
    return make_response(data=table.model_dump(), request=request)


@router.get("/{table_id}")
async def get_table(
    table_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取单个桌位详情。"""
    store_id = get_store_id(request)
    svc = TableService(db)
    table = await svc.get(table_id, store_id)
    return make_response(data=table.model_dump(), request=request)


@router.put("/{table_id}")
async def update_table(
    table_id: uuid.UUID,
    body: TableUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新桌位信息（区域、桌号、容量、状态）。"""
    store_id = get_store_id(request)
    svc = TableService(db)
    table = await svc.update(table_id, store_id, body)
    return make_response(data=table.model_dump(), request=request)


@router.delete("/{table_id}")
async def delete_table(
    table_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除桌位。"""
    store_id = get_store_id(request)
    svc = TableService(db)
    await svc.delete(table_id, store_id)
    return make_response(data=None, request=request)
