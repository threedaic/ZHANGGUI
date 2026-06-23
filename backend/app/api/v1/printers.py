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
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.sys import Printer, PrintRoute
from app.models.shared import Category
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
    service = PrinterService(db)
    printers = await service.get_printer_status(store_id)
    return make_response(data=printers, request=request)


@router.post("")
async def create_printer(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """添加打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    # 验证必填字段
    name = body.get("name")
    if not name:
        raise ValidationError("打印机名称不能为空")

    printer_type = body.get("printer_type", "order")
    if printer_type not in ("label", "receipt", "order"):
        raise ValidationError("打印机类型无效")

    printer = Printer(
        store_id=store_id,
        name=name,
        printer_type=printer_type,
        brand=body.get("brand"),
        device_sn=body.get("device_sn"),
        api_url=body.get("api_url"),
        api_key=body.get("api_key"),
        api_user=body.get("api_user"),
        api_secret=body.get("api_secret"),
        paper_width=body.get("paper_width", 80),
        extra_config=body.get("extra_config", {}),
        is_active=True,
    )
    db.add(printer)
    await db.commit()
    await db.refresh(printer)

    return make_response(
        message="打印机添加成功",
        data={"printer_id": str(printer.printer_id)},
        request=request,
    )


@router.put("/{printer_id}")
async def update_printer(
    printer_id: uuid.UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    result = await db.execute(
        select(Printer).where(
            Printer.printer_id == printer_id,
            Printer.store_id == store_id,
        )
    )
    printer = result.scalar_one_or_none()
    if not printer:
        raise NotFoundError("打印机不存在")

    # 更新字段
    if "name" in body:
        printer.name = body["name"]
    if "printer_type" in body:
        printer.printer_type = body["printer_type"]
    if "brand" in body:
        printer.brand = body["brand"]
    if "device_sn" in body:
        printer.device_sn = body["device_sn"]
    if "api_url" in body:
        printer.api_url = body["api_url"]
    if "api_key" in body:
        printer.api_key = body["api_key"]
    if "api_user" in body:
        printer.api_user = body["api_user"]
    if "api_secret" in body:
        printer.api_secret = body["api_secret"]
    if "paper_width" in body:
        printer.paper_width = body["paper_width"]
    if "extra_config" in body:
        printer.extra_config = body["extra_config"]
    if "is_active" in body:
        printer.is_active = body["is_active"]

    await db.commit()
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

    result = await db.execute(
        select(Printer).where(
            Printer.printer_id == printer_id,
            Printer.store_id == store_id,
        )
    )
    printer = result.scalar_one_or_none()
    if not printer:
        raise NotFoundError("打印机不存在")

    printer.is_active = False
    await db.commit()

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
    service = PrinterService(db)
    status = await service.get_printer_status(store_id)
    return make_response(data=status, request=request)


# ==================== 统一打印接口 ====================

@router.post("/print")
async def print_by_category(
    body: dict,
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

    category_id = body.get("category_id")
    content = body.get("content")
    if not category_id or not content:
        raise ValidationError("分类ID和打印内容不能为空")

    service = PrinterService(db)
    result = await service.print_by_category(
        store_id=store_id,
        category_id=uuid.UUID(category_id),
        content=content,
        trigger=body.get("trigger", "order_created"),
        document_type=body.get("document_type", "order"),
    )

    if result["status"] == "no_printer":
        return make_response(code=40400, message=result["message"], data=result, request=request)

    return make_response(message="打印任务已处理", data=result, request=request)


@router.post("/print/direct")
async def print_direct(
    body: dict,
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

    printer_id = body.get("printer_id")
    content = body.get("content")
    if not printer_id or not content:
        raise ValidationError("打印机ID和打印内容不能为空")

    service = PrinterService(db)
    result = await service.print_direct(
        store_id=store_id,
        printer_id=uuid.UUID(printer_id),
        content=content,
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

    result = await db.execute(
        select(PrintRoute).where(
            PrintRoute.store_id == store_id,
        ).order_by(PrintRoute.trigger_event, PrintRoute.priority)
    )
    routes = result.scalars().all()

    data = []
    for r in routes:
        # 获取打印机名称
        printer_result = await db.execute(
            select(Printer.name).where(Printer.printer_id == r.printer_id)
        )
        printer_name = printer_result.scalar_one_or_none() or "未知打印机"

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
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """添加路由规则"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    name = body.get("name")
    printer_id = body.get("printer_id")
    if not name or not printer_id:
        raise ValidationError("规则名称和打印机不能为空")

    route = PrintRoute(
        store_id=store_id,
        name=name,
        trigger_event=body.get("trigger_event", "order_created"),
        document_type=body.get("document_type", "order"),
        filter_type=body.get("filter_type", "category"),
        filter_value=body.get("filter_value"),
        printer_id=uuid.UUID(printer_id),
        priority=body.get("priority", 1),
        is_active=True,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)

    return make_response(
        message="路由规则添加成功",
        data={"route_id": str(route.route_id)},
        request=request,
    )


@router.put("/routes/{route_id}")
async def update_route(
    route_id: uuid.UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新路由规则"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    result = await db.execute(
        select(PrintRoute).where(
            PrintRoute.route_id == route_id,
            PrintRoute.store_id == store_id,
        )
    )
    route = result.scalar_one_or_none()
    if not route:
        raise NotFoundError("路由规则不存在")

    if "name" in body:
        route.name = body["name"]
    if "trigger_event" in body:
        route.trigger_event = body["trigger_event"]
    if "document_type" in body:
        route.document_type = body["document_type"]
    if "filter_type" in body:
        route.filter_type = body["filter_type"]
    if "filter_value" in body:
        route.filter_value = body["filter_value"]
    if "printer_id" in body:
        route.printer_id = uuid.UUID(body["printer_id"])
    if "priority" in body:
        route.priority = body["priority"]
    if "is_active" in body:
        route.is_active = body["is_active"]

    await db.commit()
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

    result = await db.execute(
        select(PrintRoute).where(
            PrintRoute.route_id == route_id,
            PrintRoute.store_id == store_id,
        )
    )
    route = result.scalar_one_or_none()
    if not route:
        raise NotFoundError("路由规则不存在")

    await db.delete(route)
    await db.commit()

    return make_response(message="路由规则已删除", request=request)


# ==================== 分类打印机绑定 ====================

@router.get("/categories")
async def list_categories_with_printer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取分类列表（含打印机绑定信息）"""
    store_id = get_store_id(request)

    result = await db.execute(
        select(Category).where(
            Category.store_id == store_id,
            Category.is_active == True,
        ).order_by(Category.sort_order)
    )
    categories = result.scalars().all()

    data = []
    for c in categories:
        # 获取打印机名称
        printer_name = None
        backup_printer_name = None

        if c.printer_id:
            printer_result = await db.execute(
                select(Printer.name).where(Printer.printer_id == c.printer_id)
            )
            printer_name = printer_result.scalar_one_or_none()

        if c.backup_printer_id:
            backup_result = await db.execute(
                select(Printer.name).where(Printer.printer_id == c.backup_printer_id)
            )
            backup_printer_name = backup_result.scalar_one_or_none()

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
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新分类绑定的打印机"""
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)

    result = await db.execute(
        select(Category).where(
            Category.category_id == category_id,
            Category.store_id == store_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise NotFoundError("分类不存在")

    if "printer_id" in body:
        category.printer_id = uuid.UUID(body["printer_id"]) if body["printer_id"] else None
    if "backup_printer_id" in body:
        category.backup_printer_id = uuid.UUID(body["backup_printer_id"]) if body["backup_printer_id"] else None

    await db.commit()
    return make_response(message="分类打印机绑定更新成功", request=request)
