"""
统一分页工具
所有列表接口统一使用这个。
"""
from typing import TypeVar, Generic, Sequence
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate(items: Sequence[T], total: int, params: PageParams) -> PageResult[T]:
    return PageResult(
        items=list(items),
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=(total + params.page_size - 1) // params.page_size,
    )


async def paginate_query(
    session: AsyncSession,
    base_stmt: Select,
    params: PageParams,
) -> tuple[list, int]:
    """Execute a count + paginated query against a SQLAlchemy async session.
    Returns (items, total). The caller wraps results with PageResult."""
    count_stmt = base_stmt.with_only_columns(func.count()).order_by(None)
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (params.page - 1) * params.page_size
    items = (await session.execute(base_stmt.offset(offset).limit(params.page_size))).scalars().all()
    return list(items), total
