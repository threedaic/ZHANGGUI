"""打印机管理 API 路由

前缀: /api/v1/printers (由 main.py 提供)

端点:
  GET    ""              → 获取打印机列表
  POST   ""              → 添加打印机
  PUT    "/{id}"         → 更新打印机
  DELETE "/{id}"         → 删除打印机
  POST   "/{id}/test"    → 测试打印
  GET    "/status"       → 获取所有打印机状态
  POST   "/print"        → 统一打印接口

  GET    "/routes"       → 获取路由规则列表
  POST   "/routes"       → 添加路由规则
  PUT    "/routes/{id}"  → 更新路由规则
  DELETE "/routes/{id}"  → 删除路由规则
"""
from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sys import Printer, PrintRoute
from app.repositories.printer_repository import PrinterRepository
from app.schemas.printer import (
    PrinterCreate, PrinterUpdate, PrintRouteCreate, PrintRouteUpdate,
    PrintByCategoryRequest, PrintDirectRequest, CategoryPrinterUpdate,
)
from app.utils.deps import get_store_id, require_role, make_response
from app.utils.exceptions import NotFoundError, ValidationError
from app.services.printer_service import PrinterService

router = APIRouter()


# ==================== 打印机管理 ====================

@router.get("")
async def list_printers(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取打印机列表"""
    store_id = get_store_id(request)
    repo = PrinterRepository(db)
    printers = await repo.get_printers_by_store(store_id)

    data = []
    for p in printers:
        data.append({
            "printer_id": str(p.printer_id),
            "name": p.name,
            "printer_type": p.printer_type,
            "brand": p.brand,
            "device_sn": p.device_sn,
            "online_status": p.online_status,
            "last_heartbeat": p.last_heartbeat.isoformat() if p.last_heartbeat else None,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return make_response(data=data, request=request)


@router.post("")
async def create_printer(
    body: PrinterCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """添加打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    printer = Printer(
        store_id=store_id,
        name=body.name,
        printer_type=body.printer_type,
        brand=body.brand,
        device_sn=body.device_sn,
        api_url=body.api_url,
        api_key=body.api_key,
        api_user=body.api_user,
        api_secret=body.api_secret,
        paper_width=body.paper_width,
        extra_config=body.extra_config or {},
        is_active=True,
    )

    repo = PrinterRepository(db)
    await repo.create_printer(printer)

    return make_response(
        message="打印机添加成功",
        data={"printer_id": str(printer.printer_id)},
        request=request,
    )


@router.put("/{printer_id}")
async def update_printer(
    printer_id: uuid.UUID,
    body: PrinterUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    printer = await repo.get_printer_by_id(printer_id, store_id)
    if not printer:
        raise NotFoundError("打印机不存在")

    # 更新字段
    if body.name is not None:
        printer.name = body.name
    if body.printer_type is not None:
        printer.printer_type = body.printer_type
    if body.brand is not None:
        printer.brand = body.brand
    if body.device_sn is not None:
        printer.device_sn = body.device_sn
    if body.api_url is not None:
        printer.api_url = body.api_url
    if body.api_key is not None:
        printer.api_key = body.api_key
    if body.api_user is not None:
        printer.api_user = body.api_user
    if body.api_secret is not None:
        printer.api_secret = body.api_secret
    if body.paper_width is not None:
        printer.paper_width = body.paper_width
    if body.extra_config is not None:
        printer.extra_config = body.extra_config
    if body.is_active is not None:
        printer.is_active = body.is_active

    await repo.update_printer(printer)
    return make_response(message="打印机更新成功", request=request)


@router.delete("/{printer_id}")
async def delete_printer(
    printer_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除打印机（软删除）"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    printer = await repo.get_printer_by_id(printer_id, store_id)
    if not printer:
        raise NotFoundError("打印机不存在")

    await repo.soft_delete_printer(printer)
    return make_response(message="打印机已删除", request=request)


@router.post("/{printer_id}/test")
async def test_print(
    printer_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """测试打印"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    service = PrinterService(db)
    result = await service.test_print(store_id, printer_id)

    if result["status"] == "sent":
        return make_response(message="测试打印已发送", data=result, request=request)
    else:
        return make_response(
            code=50200,
            message=result.get("message", "测试打印失败"),
            data=result,
            request=request,
        )


@router.get("/status")
async def get_printer_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取所有打印机状态"""
    store_id = get_store_id(request)
    repo = PrinterRepository(db)
    printers = await repo.get_printers_by_store(store_id)

    data = []
    for p in printers:
        status = "offline"
        if p.online_status:
            status = "online"
        elif p.last_heartbeat:
            from datetime import datetime, timedelta
            if p.last_heartbeat > datetime.utcnow() - timedelta(minutes=5):
                status = "online"

        data.append({
            "printer_id": str(p.printer_id),
            "name": p.name,
            "printer_type": p.printer_type,
            "online_status": p.online_status,
            "last_heartbeat": p.last_heartbeat.isoformat() if p.last_heartbeat else None,
            "computed_status": status,
        })

    return make_response(data=data, request=request)


# ==================== 统一打印接口 ====================

@router.post("/print")
async def print_by_category(
    body: PrintByCategoryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """统一打印接口（根据分类自动路由）

    请求体：
    {
        "category_id": "xxx",        // 分类ID
        "content": "打印内容",        // 打印内容
        "trigger": "order_created",  // 触发时机（可选）
        "document_type": "order"     // 文档类型（可选）
    }
    """
    store_id = get_store_id(request)

    service = PrinterService(db)
    result = await service.print_by_category(
        store_id=store_id,
        category_id=uuid.UUID(body.category_id),
        content=body.content,
        trigger=body.trigger,
        document_type=body.document_type,
    )

    if result["status"] == "no_printer":
        return make_response(code=40400, message=result["message"], data=result, request=request)

    return make_response(message="打印任务已处理", data=result, request=request)


@router.post("/print/direct")
async def print_direct(
    body: PrintDirectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """直接打印到指定打印机

    请求体：
    {
        "printer_id": "xxx",
        "content": "打印内容"
    }
    """
    store_id = get_store_id(request)

    service = PrinterService(db)
    result = await service.print_direct(
        store_id=store_id,
        printer_id=uuid.UUID(body.printer_id),
        content=body.content,
    )

    if result["status"] == "failed":
        return make_response(code=50200, message=result["message"], data=result, request=request)

    return make_response(message="打印任务已处理", data=result, request=request)


# ==================== 路由规则管理 ====================

@router.get("/routes")
async def list_routes(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则列表"""
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    routes = await repo.get_routes_by_store(store_id)

    data = []
    for r in routes:
        # 获取打印机名称
        printer = await repo.get_printer_by_id(r.printer_id, store_id)
        printer_name = printer.name if printer else "未知打印机"

        data.append({
            "route_id": str(r.route_id),
            "name": r.name,
            "trigger_event": r.trigger_event,
            "document_type": r.document_type,
            "filter_type": r.filter_type,
            "filter_value": r.filter_value,
            "printer_id": str(r.printer_id),
            "printer_name": printer_name,
            "priority": r.priority,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return make_response(data=data, request=request)


@router.post("/routes")
async def create_route(
    body: PrintRouteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """添加路由规则"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    route = PrintRoute(
        store_id=store_id,
        name=body.name,
        trigger_event=body.trigger_event,
        document_type=body.document_type,
        filter_type=body.filter_type,
        filter_value=body.filter_value,
        printer_id=uuid.UUID(body.printer_id),
        priority=body.priority,
        is_active=True,
    )

    repo = PrinterRepository(db)
    await repo.create_route(route)

    return make_response(
        message="路由规则添加成功",
        data={"route_id": str(route.route_id)},
        request=request,
    )


@router.put("/routes/{route_id}")
async def update_route(
    route_id: uuid.UUID,
    body: PrintRouteUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新路由规则"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    route = await repo.get_route_by_id(route_id, store_id)
    if not route:
        raise NotFoundError("路由规则不存在")

    if body.name is not None:
        route.name = body.name
    if body.trigger_event is not None:
        route.trigger_event = body.trigger_event
    if body.document_type is not None:
        route.document_type = body.document_type
    if body.filter_type is not None:
        route.filter_type = body.filter_type
    if body.filter_value is not None:
        route.filter_value = body.filter_value
    if body.printer_id is not None:
        route.printer_id = uuid.UUID(body.printer_id)
    if body.priority is not None:
        route.priority = body.priority
    if body.is_active is not None:
        route.is_active = body.is_active

    await repo.update_route(route)
    return make_response(message="路由规则更新成功", request=request)


@router.delete("/routes/{route_id}")
async def delete_route(
    route_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除路由规则"""
    require_role(request, ["boss"])
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    route = await repo.get_route_by_id(route_id, store_id)
    if not route:
        raise NotFoundError("路由规则不存在")

    await repo.delete_route(route)
    return make_response(message="路由规则已删除", request=request)


# ==================== 分类打印机绑定 ====================

@router.get("/categories")
async def list_categories_with_printer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取分类列表（含打印机绑定信息）"""
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    categories = await repo.get_categories_by_store(store_id)

    data = []
    for c in categories:
        # 获取打印机名称
        printer_name = None
        backup_printer_name = None

        if c.printer_id:
            printer = await repo.get_printer_by_id(c.printer_id, store_id)
            printer_name = printer.name if printer else None

        if c.backup_printer_id:
            backup = await repo.get_printer_by_id(c.backup_printer_id, store_id)
            backup_printer_name = backup.name if backup else None

        data.append({
            "category_id": str(c.category_id),
            "name": c.name,
            "sort_order": c.sort_order,
            "printer_id": str(c.printer_id) if c.printer_id else None,
            "printer_name": printer_name,
            "backup_printer_id": str(c.backup_printer_id) if c.backup_printer_id else None,
            "backup_printer_name": backup_printer_name,
        })

    return make_response(data=data, request=request)


@router.put("/categories/{category_id}/printer")
async def update_category_printer(
    category_id: uuid.UUID,
    body: CategoryPrinterUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新分类绑定的打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    repo = PrinterRepository(db)
    category = await repo.get_category_by_id(category_id, store_id)
    if not category:
        raise NotFoundError("分类不存在")

    printer_id = uuid.UUID(body.printer_id) if body.printer_id else None
    backup_printer_id = uuid.UUID(body.backup_printer_id) if body.backup_printer_id else None

    await repo.update_category_printer(category, printer_id, backup_printer_id)
    return make_response(message="分类打印机绑定更新成功", request=request)
