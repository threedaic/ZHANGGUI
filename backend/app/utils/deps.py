"""Shared FastAPI dependency functions.

Provides reusable dependency callables for store/role/employee extraction
from JWT-authenticated request context.  All router modules should import
these from here instead of defining their own copies.
"""

import uuid
import json
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.store import StoreSettings
from app.utils.exceptions import UnauthorizedError, ForbiddenError


def make_response(code: int = 0, message: str = "ok", data=None, request: Request | None = None) -> dict:
    """Standardized API response dict with optional request_id (m-009 fix).

    Usage:
        return make_response(data=result)
        return make_response(message="创建成功", data=item)
    """
    request_id = getattr(request.state, "request_id", None) if request else None
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }


def get_user_id(request: Request) -> str:
    """Extract the current user ID from request context.

    Raises 403 (ForbiddenError) when no user identity is bound.
    返回 UUID 字符串（SPEC 2.0）。
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise ForbiddenError("无法获取用户信息")
    return user_id


def get_store_id(request: Request) -> str:
    """Extract the current store ID from JWT-decoded request context.

    Raises 401 (UnauthorizedError) when no store_id is present.
    返回 UUID 字符串（SPEC 2.0）。
    """
    store_id = getattr(request.state, "store_id", None)
    if store_id is None:
        raise UnauthorizedError("未登录或Token已过期，请重新登录")
    return store_id


def require_role(request: Request, allowed: list[str]) -> None:
    """Check that the current user's role is in *allowed*.

    Raises 403 (ForbiddenError) when the role is not permitted.
    """
    role = getattr(request.state, "role", None)
    if role not in allowed:
        raise ForbiddenError("无权执行此操作")


def get_employee_id(request: Request) -> str:
    """Extract the current employee ID from request context.

    Raises 403 (ForbiddenError) when no employee identity is bound.
    返回 UUID 字符串（SPEC 2.0）。
    """
    employee_id = getattr(request.state, "employee_id", None)
    if not employee_id:
        raise ForbiddenError("需要绑定员工身份")
    return employee_id


# Alias for backward compatibility (used by kpi.py, payroll.py)
require_employee_id = get_employee_id


async def require_contract_initiator(request: Request, db: AsyncSession = Depends(get_db)):
    """检查当前用户是否有合同发起权限。

    读取 store_settings.contract_initiator_ids（JSON 数组）。
    - 如果为空列表 → 所有人都可以发起（默认行为）
    - 如果有指定人员 → 仅列表中的 employee_id 可以发起
    """
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)

    stmt = select(StoreSettings.contract_initiator_ids).where(
        StoreSettings.store_id == store_id
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if not row:
        return  # 没有配置 → 允许所有人

    try:
        ids = json.loads(row) if isinstance(row, str) else row
        ids = ids if ids else []
    except (json.JSONDecodeError, TypeError):
        ids = []

    if not ids:
        return  # 空列表 → 允许所有人

    if employee_id not in ids:
        raise ForbiddenError("您没有合同发起权限，请联系老板开通")
