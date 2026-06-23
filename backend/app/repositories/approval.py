"""
统一审批数据访问层
"""
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.approval import ApprovalRequest
from app.models.employee import Employee
from app.utils.pagination import PageParams


class ApprovalRepository:
    """审批 Repository"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    async def get_approval_by_id(self, approval_id: int) -> ApprovalRequest | None:
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_approvals(
        self,
        employee_id: int | None = None,
        status: str | None = None,
        approval_type: str | None = None,
        page: PageParams | None = None,
        approver_id: int | None = None,
        include_assigned: bool = False,
    ) -> tuple[list[ApprovalRequest], int]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.store_id == self.store_id)

        if include_assigned and employee_id and approver_id:
            # 查询：自己提交的 OR 指定给自己审批的
            stmt = stmt.where(
                or_(
                    ApprovalRequest.employee_id == employee_id,
                    ApprovalRequest.approver_id == approver_id,
                )
            )
        elif employee_id:
            stmt = stmt.where(ApprovalRequest.employee_id == employee_id)
        if approver_id and not include_assigned:
            stmt = stmt.where(ApprovalRequest.approver_id == approver_id)
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        if approval_type:
            stmt = stmt.where(ApprovalRequest.type == approval_type)

        stmt = stmt.order_by(ApprovalRequest.created_at.desc())

        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if page:
            stmt = stmt.offset((page.page - 1) * page.page_size).limit(page.page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def create_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        self.session.add(approval)
        await self.session.flush()
        await self.session.refresh(approval)
        return approval

    async def update_approval(self, approval: ApprovalRequest, **kwargs) -> ApprovalRequest:
        for key, value in kwargs.items():
            if hasattr(approval, key):
                setattr(approval, key, value)
        await self.session.flush()
        await self.session.refresh(approval)
        return approval

    async def get_employee_name_map(self, employee_ids: list[int]) -> dict[int, str]:
        if not employee_ids:
            return {}
        stmt = select(Employee.id, Employee.name).where(
            and_(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return {row.id: row.name for row in result.all()}
