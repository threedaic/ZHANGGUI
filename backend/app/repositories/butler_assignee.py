"""
开闭店检查单执行人顺位仓储

职责：
1. 顺位规则 CRUD（管理端配置）
2. 今日执行人查询（按请假数据自动跳顺位）
3. 每日指派记录写入（审计）
"""
import uuid
from datetime import date
from sqlalchemy import select, and_, delete, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.butler import ButlerAssigneeRule, ButlerDailyAssignment
from app.models.employee import Employee
from app.models.approval import ApprovalRequest


class ButlerAssigneeRepository:
    """开闭店顺位仓储"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    # ============ 顺位规则 CRUD ============

    async def list_rules(self, session_type: str | None = None) -> list[dict]:
        """列出本店所有顺位配置，含员工姓名"""
        stmt = (
            select(
                ButlerAssigneeRule.id,
                ButlerAssigneeRule.session_type,
                ButlerAssigneeRule.employee_id,
                ButlerAssigneeRule.priority,
                ButlerAssigneeRule.is_active,
                Employee.name.label("employee_name"),
                Employee.role.label("employee_role"),
            )
            .join(Employee, Employee.id == ButlerAssigneeRule.employee_id)
            .where(ButlerAssigneeRule.store_id == self.store_id)
        )
        if session_type:
            stmt = stmt.where(ButlerAssigneeRule.session_type == session_type)
        stmt = stmt.order_by(ButlerAssigneeRule.session_type, ButlerAssigneeRule.priority)
        result = await self.session.execute(stmt)
        return [
            {
                "rule_id": str(r.id),
                "session_type": r.session_type,
                "employee_id": str(r.employee_id),
                "employee_name": r.employee_name,
                "employee_role": r.employee_role,
                "priority": r.priority,
                "is_active": r.is_active,
            }
            for r in result.all()
        ]

    async def replace_rules(self, session_type: str, items: list[dict]) -> None:
        """整体替换某类型的顺位（前端拖动后保存）

        items: [{employee_id, priority}, ...]
        """
        # 删除旧规则
        await self.session.execute(
            delete(ButlerAssigneeRule).where(
                and_(
                    ButlerAssigneeRule.store_id == self.store_id,
                    ButlerAssigneeRule.session_type == session_type,
                )
            )
        )
        # 写入新规则
        for it in items:
            self.session.add(
                ButlerAssigneeRule(
                    store_id=self.store_id,
                    session_type=session_type,
                    employee_id=uuid.UUID(it["employee_id"]),
                    priority=int(it["priority"]),
                    is_active=True,
                )
            )
        await self.session.commit()

    # ============ 今日执行人查询 ============

    async def _is_on_leave(self, employee_id: uuid.UUID, target_date: date) -> bool:
        """检查员工当日是否已请假（已批准的请假单覆盖该日期）"""
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.employee_id == employee_id,
                ApprovalRequest.type == "leave",
                ApprovalRequest.status == "approved",
                ApprovalRequest.start_date <= target_date,
                ApprovalRequest.end_date >= target_date,
            )
        )
        row = await self.session.execute(stmt)
        return row.scalar() is not None

    async def resolve_today_assignee(
        self, session_type: str, target_date: date | None = None
    ) -> dict | None:
        """解析今日执行人：按顺位遍历，跳过请假的人

        返回 {employee_id, employee_name, priority, fallback_used, fallback_reason}
        全员请假返回 None
        """
        target_date = target_date or date.today()

        # 取顺位列表
        stmt = (
            select(
                ButlerAssigneeRule.employee_id,
                ButlerAssigneeRule.priority,
                Employee.name.label("employee_name"),
            )
            .join(Employee, Employee.id == ButlerAssigneeRule.employee_id)
            .where(
                and_(
                    ButlerAssigneeRule.store_id == self.store_id,
                    ButlerAssigneeRule.session_type == session_type,
                    ButlerAssigneeRule.is_active == True,  # noqa: E712
                )
            )
            .order_by(ButlerAssigneeRule.priority)
        )
        result = await self.session.execute(stmt)
        rules = result.all()

        if not rules:
            return None

        # 遍历顺位，第一个没请假的胜出
        skipped: list[str] = []
        for r in rules:
            if await self._is_on_leave(r.employee_id, target_date):
                skipped.append(f"{r.employee_name}(顺位{r.priority})")
                continue
            return {
                "employee_id": str(r.employee_id),
                "employee_name": r.employee_name,
                "priority": r.priority,
                "fallback_used": r.priority > 1 or bool(skipped),
                "fallback_reason": "、".join(skipped) + " 已请假" if skipped else None,
            }

        # 全员请假
        return None

    async def get_today_assignment(
        self, session_type: str, target_date: date | None = None
    ) -> dict | None:
        """读取今日已指派记录（无则实时解析并写入）"""
        target_date = target_date or date.today()

        stmt = (
            select(
                ButlerDailyAssignment.employee_id,
                ButlerDailyAssignment.fallback_used,
                ButlerDailyAssignment.fallback_reason,
                Employee.name.label("employee_name"),
            )
            .join(Employee, Employee.id == ButlerDailyAssignment.employee_id)
            .where(
                and_(
                    ButlerDailyAssignment.store_id == self.store_id,
                    ButlerDailyAssignment.session_type == session_type,
                    ButlerDailyAssignment.assign_date == target_date,
                )
            )
        )
        row = (await self.session.execute(stmt)).first()
        if row:
            return {
                "employee_id": str(row.employee_id),
                "employee_name": row.employee_name,
                "fallback_used": row.fallback_used,
                "fallback_reason": row.fallback_reason,
            }

        # 没记录，实时解析
        resolved = await self.resolve_today_assignee(session_type, target_date)
        if not resolved:
            return None

        # 写入今日记录（UNIQUE 约束兜底，避免并发重复）
        try:
            self.session.add(
                ButlerDailyAssignment(
                    store_id=self.store_id,
                    session_type=session_type,
                    assign_date=target_date,
                    employee_id=uuid.UUID(resolved["employee_id"]),
                    fallback_used=resolved["fallback_used"],
                    fallback_reason=resolved["fallback_reason"],
                )
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

        return resolved

    async def list_active_employees(self) -> list[dict]:
        """列出本店可用员工（管理端配置顺位时用）"""
        stmt = (
            select(Employee.id, Employee.name, Employee.role)
            .where(
                and_(
                    Employee.store_id == self.store_id,
                    Employee.status == "active",
                )
            )
            .order_by(Employee.role, Employee.name)
        )
        result = await self.session.execute(stmt)
        return [
            {"employee_id": str(r.id), "name": r.name, "role": r.role}
            for r in result.all()
        ]
