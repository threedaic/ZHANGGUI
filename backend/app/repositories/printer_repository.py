"""打印机 Repository 层

职责：数据库 CRUD 操作
调用方：Service 层
"""
from __future__ import annotations

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.sys import Printer, PrintRoute, PrintQueue
from app.models.shared import Category


class PrinterRepository:
    """打印机数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 打印机 CRUD ====================

    async def get_printer_by_id(self, printer_id: uuid.UUID, store_id: uuid.UUID) -> Optional[Printer]:
        """根据ID获取打印机"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.printer_id == printer_id,
                Printer.store_id == store_id,
                Printer.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_printers_by_store(self, store_id: uuid.UUID) -> List[Printer]:
        """获取门店所有打印机"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.is_active == True,
            ).order_by(Printer.printer_type, Printer.name)
        )
        return list(result.scalars().all())

    async def get_printer_by_type(self, store_id: uuid.UUID, printer_type: str) -> Optional[Printer]:
        """按类型获取第一台打印机"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.printer_type == printer_type,
                Printer.is_active == True,
            ).order_by(Printer.name).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_printer(self, printer: Printer) -> Printer:
        """创建打印机"""
        self.db.add(printer)
        await self.db.commit()
        await self.db.refresh(printer)
        return printer

    async def update_printer(self, printer: Printer) -> Printer:
        """更新打印机"""
        await self.db.commit()
        await self.db.refresh(printer)
        return printer

    async def soft_delete_printer(self, printer: Printer) -> None:
        """软删除打印机"""
        printer.is_active = False
        await self.db.commit()

    # ==================== 路由规则 CRUD ====================

    async def get_routes_by_store(
        self,
        store_id: uuid.UUID,
        trigger_event: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[PrintRoute]:
        """获取门店路由规则"""
        query = select(PrintRoute).where(
            PrintRoute.store_id == store_id,
            PrintRoute.is_active == True,
        )

        if trigger_event:
            query = query.where(PrintRoute.trigger_event == trigger_event)
        if document_type:
            query = query.where(PrintRoute.document_type == document_type)

        query = query.order_by(PrintRoute.trigger_event, PrintRoute.priority)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_route_by_id(self, route_id: uuid.UUID, store_id: uuid.UUID) -> Optional[PrintRoute]:
        """根据ID获取路由规则"""
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.route_id == route_id,
                PrintRoute.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_route(self, route: PrintRoute) -> PrintRoute:
        """创建路由规则"""
        self.db.add(route)
        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def update_route(self, route: PrintRoute) -> PrintRoute:
        """更新路由规则"""
        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def delete_route(self, route: PrintRoute) -> None:
        """删除路由规则"""
        await self.db.delete(route)
        await self.db.commit()

    # ==================== 打印队列 CRUD ====================

    async def enqueue(self, queue: PrintQueue) -> PrintQueue:
        """添加到打印队列"""
        self.db.add(queue)
        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def get_pending_tasks(self, limit: int = 50) -> List[PrintQueue]:
        """获取待处理的打印任务"""
        result = await self.db.execute(
            select(PrintQueue).where(
                PrintQueue.status == "pending",
                PrintQueue.retry_count < PrintQueue.max_retries,
            ).order_by(PrintQueue.created_at).limit(limit)
        )
        return list(result.scalars().all())

    async def update_task_status(
        self,
        queue_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """更新任务状态"""
        result = await self.db.execute(
            select(PrintQueue).where(PrintQueue.queue_id == queue_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            if status == "completed":
                task.printed_at = datetime.utcnow()
            elif status == "failed":
                task.error_message = error_message
                task.retry_count += 1
            await self.db.commit()

    async def retry_task(self, queue_id: uuid.UUID) -> None:
        """重试任务"""
        result = await self.db.execute(
            select(PrintQueue).where(PrintQueue.queue_id == queue_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "pending"
            task.retry_count += 1
            await self.db.commit()

    # ==================== 分类打印机绑定 ====================

    async def get_category_by_id(self, category_id: uuid.UUID, store_id: uuid.UUID) -> Optional[Category]:
        """根据ID获取分类"""
        result = await self.db.execute(
            select(Category).where(
                Category.category_id == category_id,
                Category.store_id == store_id,
                Category.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_categories_by_store(self, store_id: uuid.UUID) -> List[Category]:
        """获取门店所有分类"""
        result = await self.db.execute(
            select(Category).where(
                Category.store_id == store_id,
                Category.is_active == True,
            ).order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    async def update_category_printer(
        self,
        category: Category,
        printer_id: Optional[uuid.UUID],
        backup_printer_id: Optional[uuid.UUID],
    ) -> Category:
        """更新分类绑定的打印机"""
        category.printer_id = printer_id
        category.backup_printer_id = backup_printer_id
        await self.db.commit()
        await self.db.refresh(category)
        return category
