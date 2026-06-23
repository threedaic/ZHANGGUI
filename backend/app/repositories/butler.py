"""
智能管家模块数据访问层
"""
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.butler import (
    ClosingChecklistTemplate,
    ClosingChecklistItem,
    ClosingSession,
    ClosingItemResult,
)
from app.models.store import Store
from app.utils.pagination import PageParams


class ButlerRepository:
    """智能管家 Repository"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    # ==================== 模板 ====================

    async def list_templates(self, session_type: str | None = None) -> list[dict]:
        """列出本店所有模板，含 items"""
        stmt = select(ClosingChecklistTemplate).where(
            ClosingChecklistTemplate.store_id == self.store_id
        )
        if session_type:
            stmt = stmt.where(ClosingChecklistTemplate.session_type == session_type)
        stmt = stmt.order_by(ClosingChecklistTemplate.sort_order)
        result = await self.session.execute(stmt)
        templates = list(result.scalars().all())

        if not templates:
            return []

        # 批量查询所有模板的清单项，按 template_id 分组，避免 N+1
        template_ids = [t.id for t in templates]
        items_stmt = (
            select(ClosingChecklistItem)
            .where(ClosingChecklistItem.template_id.in_(template_ids))
            .order_by(ClosingChecklistItem.template_id, ClosingChecklistItem.sort_order)
        )
        items_result = await self.session.execute(items_stmt)
        items_by_tpl: dict[int, list[ClosingChecklistItem]] = {}
        for item in items_result.scalars().all():
            items_by_tpl.setdefault(item.template_id, []).append(item)

        output = []
        for tpl in templates:
            items = items_by_tpl.get(tpl.id, [])
            d = {c.name: getattr(tpl, c.name) for c in tpl.__table__.columns}
            d["items"] = [{c.name: getattr(i, c.name) for c in i.__table__.columns} for i in items]
            output.append(d)
        return output

    async def get_template(self, template_id: int) -> ClosingChecklistTemplate | None:
        stmt = select(ClosingChecklistTemplate).where(
            and_(
                ClosingChecklistTemplate.id == template_id,
                ClosingChecklistTemplate.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_template(self, data: dict) -> ClosingChecklistTemplate:
        tpl = ClosingChecklistTemplate(store_id=self.store_id, **data)
        self.session.add(tpl)
        await self.session.flush()
        return tpl

    async def update_template(self, template: ClosingChecklistTemplate, **kwargs) -> ClosingChecklistTemplate:
        for key, value in kwargs.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        await self.session.flush()
        return template

    async def delete_template(self, template: ClosingChecklistTemplate) -> None:
        await self.session.delete(template)
        await self.session.flush()

    # ==================== 清单项 ====================

    async def replace_items(self, template_id: int, items: list[dict]) -> list[ClosingChecklistItem]:
        """全量替换模板下的清单项"""
        # 删除旧项
        old = await self.session.execute(
            select(ClosingChecklistItem).where(ClosingChecklistItem.template_id == template_id)
        )
        for o in old.scalars().all():
            await self.session.delete(o)

        # 插入新项
        new_items = []
        for item in items:
            obj = ClosingChecklistItem(template_id=template_id, **item)
            self.session.add(obj)
            new_items.append(obj)
        await self.session.flush()
        return new_items

    async def get_items_by_ids(self, item_ids: list[int]) -> list[ClosingChecklistItem]:
        stmt = select(ClosingChecklistItem).where(ClosingChecklistItem.id.in_(item_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 会话 ====================

    async def create_session(self, data: dict) -> ClosingSession:
        obj = ClosingSession(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_session(self, session_id: int) -> ClosingSession | None:
        stmt = select(ClosingSession).where(
            and_(
                ClosingSession.id == session_id,
                ClosingSession.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session(self, session: ClosingSession, **kwargs) -> ClosingSession:
        for key, value in kwargs.items():
            if hasattr(session, key) and value is not None:
                setattr(session, key, value)
        await self.session.flush()
        return session

    async def list_sessions(self, session_type: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[ClosingSession], int]:
        stmt = select(ClosingSession).where(ClosingSession.store_id == self.store_id)
        if session_type:
            stmt = stmt.where(ClosingSession.session_type == session_type)
        stmt = stmt.order_by(ClosingSession.started_at.desc())

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_active_session(self, session_type: str) -> ClosingSession | None:
        """查找当前是否有未完成的开店/闭店会话"""
        stmt = select(ClosingSession).where(
            and_(
                ClosingSession.store_id == self.store_id,
                ClosingSession.session_type == session_type,
                ClosingSession.status == "in_progress",
            )
        ).order_by(ClosingSession.started_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== 检查结果 ====================

    async def create_results_batch(self, results: list[dict]) -> list[ClosingItemResult]:
        objs = [ClosingItemResult(**r) for r in results]
        self.session.add_all(objs)
        await self.session.flush()
        return objs

    async def get_results_by_session(self, session_id: int) -> list[ClosingItemResult]:
        stmt = select(ClosingItemResult).where(
            ClosingItemResult.session_id == session_id
        ).order_by(ClosingItemResult.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_result(self, result_id: int, session_id: int) -> ClosingItemResult | None:
        stmt = select(ClosingItemResult).where(
            and_(
                ClosingItemResult.id == result_id,
                ClosingItemResult.session_id == session_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_result(self, result: ClosingItemResult, **kwargs) -> ClosingItemResult:
        for key, value in kwargs.items():
            if hasattr(result, key):
                setattr(result, key, value)
        await self.session.flush()
        return result

    async def create_result(self, data: dict) -> ClosingItemResult:
        obj = ClosingItemResult(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    # ==================== 看板 ====================

    async def get_all_stores_status(self) -> list[dict]:
        """获取所有活跃门店的最新开店/闭店状态（boss 看板）"""
        # 获取所有活跃门店
        stores_stmt = select(Store).where(Store.status == "active")
        stores_result = await self.session.execute(stores_stmt)
        stores = list(stores_result.scalars().all())

        if not stores:
            return []

        store_ids = [s.id for s in stores]

        # 批量查询所有店的 in_progress 会话（取最新一条）
        active_stmt = (
            select(ClosingSession)
            .where(
                and_(
                    ClosingSession.store_id.in_(store_ids),
                    ClosingSession.status == "in_progress",
                )
            )
            .order_by(ClosingSession.store_id, ClosingSession.started_at.desc())
        )
        active_result = await self.session.execute(active_stmt)
        active_by_store: dict[int, ClosingSession] = {}
        for s in active_result.scalars().all():
            # 已按 started_at desc 排序，首条即最新
            if s.store_id not in active_by_store:
                active_by_store[s.store_id] = s

        # 批量查询所有店的 completed 会话（取最新一条）
        completed_stmt = (
            select(ClosingSession)
            .where(
                and_(
                    ClosingSession.store_id.in_(store_ids),
                    ClosingSession.status == "completed",
                )
            )
            .order_by(ClosingSession.store_id, ClosingSession.completed_at.desc())
        )
        completed_result = await self.session.execute(completed_stmt)
        completed_by_store: dict[int, ClosingSession] = {}
        for s in completed_result.scalars().all():
            if s.store_id not in completed_by_store:
                completed_by_store[s.store_id] = s

        output = []
        for store in stores:
            active = active_by_store.get(store.id)
            last_completed = completed_by_store.get(store.id)

            status_data = {
                "store_id": store.id,
                "store_name": store.name,
                "has_active_session": active is not None,
                "last_completed_type": last_completed.session_type if last_completed else None,
                "last_completed_at": last_completed.completed_at.isoformat() if last_completed and last_completed.completed_at else None,
            }

            if active:
                status_data["session_type"] = active.session_type
                status_data["session_id"] = active.id
                status_data["session_status"] = active.status
                status_data["total_items"] = active.total_items
                status_data["completed_items"] = active.completed_items
                status_data["started_at"] = active.started_at.isoformat() if active.started_at else None

            output.append(status_data)
        return output
