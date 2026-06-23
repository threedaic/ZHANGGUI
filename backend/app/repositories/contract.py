"""
合同数据访问层

封装 SQL 查询，返回 ORM 对象。
所有查询强制带上 store_id（RLS 应用层兜底）。
"""
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contract import SalaryMatrix, Contract
from app.models.employee import Employee


class ContractRepository:
    """合同相关数据访问。每个请求实例化一次，绑定 store_id。"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    # ========== 薪资矩阵 ==========

    async def list_salary_matrix(self) -> list[SalaryMatrix]:
        result = await self.session.execute(
            select(SalaryMatrix).where(
                SalaryMatrix.store_id == self.store_id
            ).order_by(
                SalaryMatrix.position, SalaryMatrix.grade
            )
        )
        return list(result.scalars().all())

    async def get_matrix_entry(
        self, position: str, grade: str
    ) -> SalaryMatrix | None:
        result = await self.session.execute(
            select(SalaryMatrix).where(
                SalaryMatrix.position == position,
                SalaryMatrix.grade == grade,
            )
        )
        return result.scalar_one_or_none()

    async def update_matrix_entry(
        self, entry: SalaryMatrix, **kwargs
    ) -> SalaryMatrix:
        for key, value in kwargs.items():
            if value is not None:
                setattr(entry, key, value)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    # ========== 合同 CRUD ==========

    async def get_by_id(self, contract_id: int) -> Contract | None:
        result = await self.session.execute(
            select(Contract).where(
                Contract.id == contract_id,
                Contract.store_id == self.store_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_contract_no(self, contract_no: str) -> Contract | None:
        result = await self.session.execute(
            select(Contract).where(
                and_(Contract.contract_no == contract_no, Contract.store_id == self.store_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_employee(
        self, employee_id: int
    ) -> Contract | None:
        """获取某员工当前有效合同（signed 或 pending_sign）。"""
        result = await self.session.execute(
            select(Contract)
            .where(
                Contract.store_id == self.store_id,
                Contract.employee_id == employee_id,
                Contract.status.in_(["signed", "pending_sign"]),
            )
            .order_by(Contract.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        employee_id: Optional[int] = None,
        position: Optional[str] = None,
    ) -> tuple[list[Contract], int]:
        """分页查询合同列表，支持按 status/employee/position 筛选。"""
        where_clauses = [Contract.store_id == self.store_id]

        if status:
            where_clauses.append(Contract.status == status)
        if employee_id:
            where_clauses.append(Contract.employee_id == employee_id)
        if position:
            where_clauses.append(Contract.position == position)

        # Total count
        count_result = await self.session.execute(
            select(func.count()).select_from(Contract).where(and_(*where_clauses))
        )
        total = count_result.scalar() or 0

        # Paginated items
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(Contract)
            .where(and_(*where_clauses))
            .order_by(Contract.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    async def create(self, contract: Contract) -> Contract:
        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def update(self, contract: Contract, **kwargs) -> Contract:
        for key, value in kwargs.items():
            if value is not None:
                setattr(contract, key, value)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def delete(self, contract: Contract) -> None:
        await self.session.delete(contract)
        await self.session.flush()

    # ========== 员工 ==========

    async def get_active_employees(self) -> list[Employee]:
        result = await self.session.execute(
            select(Employee)
            .where(
                Employee.store_id == self.store_id,
                Employee.status == "active",
            )
            .order_by(Employee.id)
        )
        return list(result.scalars().all())

    async def get_employee(self, employee_id: int) -> Employee | None:
        result = await self.session.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.store_id == self.store_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_employees_by_ids(self, employee_ids: set[int]) -> dict[int, Employee]:
        """Batch fetch employees by IDs (M-005 fix: eliminates N+1 query)."""
        if not employee_ids:
            return {}
        result = await self.session.execute(
            select(Employee).where(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        return {e.id: e for e in result.scalars().all()}

    async def get_next_contract_seq(self, store_id: int) -> int:
        """Get next contract sequence number for a store (DB-based, survives restarts).

        Scans existing contract_no values to find the max sequence.
        M-002 fix: replaces in-memory _contract_seq dict.
        """
        from sqlalchemy import func as _func
        result = await self.session.execute(
            select(_func.max(Contract.id)).where(Contract.store_id == store_id)
        )
        max_id = result.scalar() or 0
        return max_id + 1
