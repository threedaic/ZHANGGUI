import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.leave_balance import LeaveBalance


class LeaveBalanceRepository:
    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def get_balance(self, employee_id: uuid.UUID, year: int) -> list[LeaveBalance]:
        stmt = select(LeaveBalance).where(
            and_(
                LeaveBalance.store_id == self.store_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deduct_leave(self, employee_id: uuid.UUID, year: int, leave_type: str, days: float) -> LeaveBalance | None:
        stmt = select(LeaveBalance).where(
            and_(
                LeaveBalance.store_id == self.store_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
                LeaveBalance.leave_type == leave_type,
            )
        )
        result = await self.session.execute(stmt)
        balance = result.scalar_one_or_none()
        if not balance:
            # 自增创建
            balance = LeaveBalance(
                store_id=self.store_id,
                employee_id=employee_id,
                year=year,
                leave_type=leave_type,
                total_days={"annual": 5, "sick": 12, "personal": 3}.get(leave_type, 5),
                used_days=0,
            )
            self.session.add(balance)
            await self.session.flush()
        balance.used_days += days
        await self.session.flush()
        return balance
