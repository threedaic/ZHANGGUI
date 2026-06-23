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

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
    service = PrinterService(db)
    data = await service.list_printers(store_id)
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

    service = PrinterService(db)
    result = await service.create_printer(store_id, body.model_dump(exclude_unset=True))

    return make_response(
        message="打印机添加成功",
        data=result,
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

    service = PrinterService(db)
    success = await service.update_printer(store_id, printer_id, body.model_dump(exclude_unset=True))

    if not success:
        raise NotFoundError("打印机不存在")

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

    service = PrinterService(db)
    success = await service.delete_printer(store_id, printer_id)

    if not success:
        raise NotFoundError("打印机不存在")

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
    data = await service.get_printer_status_list(store_id)
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
    service = PrinterService(db)
    data = await service.list_routes(store_id)
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

    service = PrinterService(db)
    result = await service.create_route(store_id, body.model_dump(exclude_unset=True))

    return make_response(
        message="路由规则添加成功",
        data=result,
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

    service = PrinterService(db)
    success = await service.update_route(store_id, route_id, body.model_dump(exclude_unset=True))

    if not success:
        raise NotFoundError("路由规则不存在")

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

    service = PrinterService(db)
    success = await service.delete_route(store_id, route_id)

    if not success:
        raise NotFoundError("路由规则不存在")

    return make_response(message="路由规则已删除", request=request)


# ==================== 分类打印机绑定 ====================

@router.get("/categories")
async def list_categories_with_printer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取分类列表（含打印机绑定信息）"""
    store_id = get_store_id(request)
    service = PrinterService(db)
    data = await service.list_categories_with_printer(store_id)
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

    service = PrinterService(db)
    success = await service.update_category_printer(
        store_id,
        category_id,
        body.printer_id,
        body.backup_printer_id,
    )

    if not success:
        raise NotFoundError("分类不存在")

    return make_response(message="分类打印机绑定更新成功", request=request)
