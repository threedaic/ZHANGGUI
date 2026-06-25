"""
签收任务 Repository — 数据访问层
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sign_task import SignTask
from app.utils.pagination import PageParams


class SignTaskRepository:
    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def create(self, task: SignTask) -> SignTask:
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> SignTask | None:
        stmt = select(SignTask).where(
            and_(
                SignTask.id == task_id,
                SignTask.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_inbox(
        self,
        employee_id: uuid.UUID,
        status: str | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[SignTask], int]:
        conditions = [
            SignTask.store_id == self.store_id,
            SignTask.employee_id == employee_id,
        ]
        if status:
            conditions.append(SignTask.status == status)

        stmt = (
            select(SignTask)
            .where(and_(*conditions))
            .order_by(SignTask.created_at.desc())
        )

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_pending_count(self, employee_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(SignTask)
            .where(
                and_(
                    SignTask.store_id == self.store_id,
                    SignTask.employee_id == employee_id,
                    SignTask.status == "pending",
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def list_issued(
        self,
        issued_by: uuid.UUID,
        status: str | None = None,
        page: PageParams | None = None,
    ) -> tuple[list[SignTask], int]:
        conditions = [
            SignTask.store_id == self.store_id,
            SignTask.issued_by == issued_by,
        ]
        if status:
            conditions.append(SignTask.status == status)

        stmt = (
            select(SignTask)
            .where(and_(*conditions))
            .order_by(SignTask.created_at.desc())
        )

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_disputes(
        self,
        page: PageParams | None = None,
    ) -> tuple[list[SignTask], int]:
        stmt = (
            select(SignTask)
            .where(
                and_(
                    SignTask.store_id == self.store_id,
                    SignTask.status == "disputed",
                )
            )
            .order_by(SignTask.disputed_at.desc())
        )

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def sign(self, task_id: uuid.UUID, employee_id: uuid.UUID, signature_data: str, notes: str | None = None) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(SignTask)
            .where(
                and_(
                    SignTask.id == task_id,
                    SignTask.store_id == self.store_id,
                    SignTask.employee_id == employee_id,
                    SignTask.status == "pending",
                )
            )
            .values(
                status="signed",
                signature_data=signature_data,
                notes=notes,
                signed_at=now,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def dispute(self, task_id: uuid.UUID, employee_id: uuid.UUID, reason: str) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(SignTask)
            .where(
                and_(
                    SignTask.id == task_id,
                    SignTask.store_id == self.store_id,
                    SignTask.employee_id == employee_id,
                    SignTask.status == "pending",
                )
            )
            .values(
                status="disputed",
                dispute_reason=reason,
                disputed_at=now,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def revoke(self, task_id: uuid.UUID, reason: str | None = None, revoked_by: uuid.UUID | None = None) -> bool:
        """撤回已签收任务，原签名存入 extra.revoked_signatures"""
        from sqlalchemy import text

        # 先查当前签名
        stmt = select(SignTask).where(
            and_(
                SignTask.id == task_id,
                SignTask.store_id == self.store_id,
                SignTask.status == "signed",
            )
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return False

        # 构建撤回历史
        now = datetime.now(timezone.utc)
        revoked_entry = {
            "signature_data": task.signature_data,
            "signed_at": task.signed_at.isoformat() if task.signed_at else None,
            "revoked_at": now.isoformat(),
            "revoked_by": revoked_by,
            "reason": reason,
        }
        history = (task.extra or {}).get("revoked_signatures", [])
        history.append(revoked_entry)
        new_extra = {**(task.extra or {}), "revoked_signatures": history}

        stmt_update = (
            update(SignTask)
            .where(
                and_(
                    SignTask.id == task_id,
                    SignTask.store_id == self.store_id,
                    SignTask.status == "signed",
                )
            )
            .values(
                status="pending",
                signature_data=None,
                signed_at=None,
                notes=None,
                dispute_reason=None,
                disputed_at=None,
                extra=new_extra,
            )
        )
        result = await self.session.execute(stmt_update)
        await self.session.commit()
        return result.rowcount > 0

    async def get_by_ref(self, ref_type: str, ref_id: uuid.UUID, employee_id: uuid.UUID) -> SignTask | None:
        stmt = select(SignTask).where(
            and_(
                SignTask.store_id == self.store_id,
                SignTask.ref_type == ref_type,
                SignTask.ref_id == ref_id,
                SignTask.employee_id == employee_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
