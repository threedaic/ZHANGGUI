"""
处罚通知 Service — 业务逻辑层
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.penalty_notice import PenaltyNotice
from app.models.employee import Employee
from app.repositories.penalty import PenaltyRepository
from app.schemas.penalty import PENALTY_TYPES
from app.utils.pagination import PageParams


class PenaltyService:
    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id
        self.repo = PenaltyRepository(session, store_id)

    async def create(
        self,
        employee_id: uuid.UUID,
        penalty_type: str,
        amount: float,
        reason: str,
        issued_by: uuid.UUID,
        auto_issue: bool = True,
    ) -> PenaltyNotice:
        notice = PenaltyNotice(
            store_id=self.store_id,
            employee_id=employee_id,
            penalty_type=penalty_type,
            amount=amount,
            reason=reason,
            issued_by=issued_by,
            issued_at=datetime.now(timezone.utc),
            status="draft",
        )
        notice = await self.repo.create(notice)

        if auto_issue:
            await self._issue_and_notify(notice)
            await self.repo.update_status(notice.id, "issued")

        return notice

    async def _issue_and_notify(self, notice: PenaltyNotice):
        """发布处罚通知时自动创建签收任务并推送企微通知"""
        try:
            from app.services.sign_task import SignTaskService
            sign_service = SignTaskService(self.session, self.store_id)
            title = f"处罚通知 - {PENALTY_TYPES.get(notice.penalty_type, notice.penalty_type)}"
            await sign_service.create_task(
                employee_id=notice.employee_id,
                task_type="penalty_notice",
                title=title,
                ref_type="penalty_notice",
                ref_id=notice.id,
                issued_by=notice.issued_by,
                extra={
                    "penalty_type": notice.penalty_type,
                    "amount": notice.amount,
                    "reason": notice.reason,
                },
            )

            # 推送企微通知
            from app.services.notification_service import NotificationService
            notifier = NotificationService(self.session, self.store_id)
            # 查员工对应的 user_id
            from app.models.user import User
            stmt = select(User.id).join(Employee, User.employee_id == Employee.id).where(
                Employee.id == notice.employee_id,
                Employee.store_id == self.store_id,
                User.is_active.is_(True),
            )
            result = await self.session.execute(stmt)
            user_ids = [row[0] for row in result.all()]

            if user_ids:
                content = f"您收到一份处罚通知：{PENALTY_TYPES.get(notice.penalty_type)}\n罚款金额：¥{notice.amount}\n事由：{notice.reason}\n请在收件箱中查看并签名确认。"
                await notifier.send(
                    notification_type="penalty_notice",
                    title=title,
                    content=content,
                    target_user_ids=user_ids,
                    channel="all",
                    extra={"penalty_id": notice.id},
                )
        except Exception as e:
            logger.error(f"处罚通知推送失败: {e}")

    async def get_list(
        self,
        penalty_type: str | None = None,
        status: str | None = None,
        employee_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        params = PageParams(page=page, page_size=page_size)
        notices, total = await self.repo.list_notices(
            penalty_type=penalty_type,
            status=status,
            employee_id=employee_id,
            page=params,
        )
        items = await self._enrich(notices)
        return items, total

    async def get_detail(self, notice_id: uuid.UUID) -> dict | None:
        notice = await self.repo.get_by_id(notice_id)
        if not notice:
            return None
        items = await self._enrich([notice])
        return items[0] if items else None

    async def update(self, notice_id: uuid.UUID, **kwargs) -> PenaltyNotice | None:
        return await self.repo.update(notice_id, **kwargs)

    async def delete(self, notice_id: uuid.UUID) -> bool:
        return await self.repo.delete(notice_id)

    async def _enrich(self, notices: list[PenaltyNotice]) -> list[dict]:
        if not notices:
            return []

        emp_ids = set(n.employee_id for n in notices)
        emp_ids.update(n.issued_by for n in notices)

        stmt = select(Employee).where(
            Employee.id.in_(list(emp_ids)),
            Employee.store_id == self.store_id,
        )
        result = await self.session.execute(stmt)
        emp_map = {e.id: e for e in result.scalars().all()}

        # 查关联的 sign_task
        from app.models.sign_task import SignTask
        sign_stmt = select(SignTask).where(
            SignTask.store_id == self.store_id,
            SignTask.ref_type == "penalty_notice",
            SignTask.ref_id.in_([n.id for n in notices]),
        )
        sign_result = await self.session.execute(sign_stmt)
        sign_map = {}
        for st in sign_result.scalars().all():
            sign_map[st.ref_id] = st

        items = []
        for n in notices:
            emp = emp_map.get(n.employee_id)
            issuer = emp_map.get(n.issued_by)
            sign_task = sign_map.get(n.id)
            items.append({
                "id": n.id,
                "store_id": n.store_id,
                "employee_id": n.employee_id,
                "penalty_type": n.penalty_type,
                "amount": n.amount,
                "reason": n.reason,
                "issued_by": n.issued_by,
                "issued_at": n.issued_at.isoformat() if n.issued_at else None,
                "status": n.status,
                "extra": n.extra,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "employee_name": emp.name if emp else f"员工{n.employee_id}",
                "issued_by_name": issuer.name if issuer else f"员工{n.issued_by}",
                "penalty_type_name": PENALTY_TYPES.get(n.penalty_type, n.penalty_type),
                "sign_task_id": sign_task.id if sign_task else None,
                "sign_task_status": sign_task.status if sign_task else None,
            })
        return items
