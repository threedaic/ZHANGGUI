"""
账期管理服务

控制月度账期的状态流转: open -> locked -> closed
关账后该月考勤/KPI/业绩/工资数据不可修改。

状态规则:
  - open:    可正常录入/修改/重算
  - locked:  明细数据冻结，仅允许工资条状态流转
  - closed:  完全冻结，任何写入均被拒绝
"""
import uuid
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.period import Period
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError


class PeriodService:
    """账期管理 Service"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id

    async def get_or_create_period(self, period: str) -> Period:
        """获取或创建账期记录（默认 open 状态）"""
        stmt = select(Period).where(
            and_(
                Period.store_id == self.store_id,
                Period.period == period,
            )
        )
        result = await self.session.execute(stmt)
        period_obj = result.scalar_one_or_none()

        if not period_obj:
            period_obj = Period(
                store_id=self.store_id,
                period=period,
                status="open",
            )
            self.session.add(period_obj)
            await self.session.flush()
            logger.info(f"[Period] 门店 {self.store_id} 创建账期 {period}")
        return period_obj

    async def get_period(self, period: str) -> Period | None:
        """获取账期记录"""
        stmt = select(Period).where(
            and_(
                Period.store_id == self.store_id,
                Period.period == period,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_writable(self, period: str) -> None:
        """检查账期是否可写入（open 状态）

        locked/closed 状态下禁止修改明细数据。
        """
        period_obj = await self.get_period(period)
        if period_obj and period_obj.status in ("locked", "closed"):
            raise ConflictError(
                f"账期 {period} 已{period_obj.status}，不可修改明细数据"
            )

    async def check_payroll_writable(self, period: str) -> None:
        """检查账期是否可修改工资条状态

        locked 状态允许工资条状态流转（draft->confirmed->paid）
        closed 状态禁止任何修改
        """
        period_obj = await self.get_period(period)
        if period_obj and period_obj.status == "closed":
            raise ConflictError(f"账期 {period} 已关账，不可修改工资条")

    async def lock_period(self, period: str, user_id: uuid.UUID) -> Period:
        """锁定账期: open -> locked"""
        period_obj = await self.get_or_create_period(period)
        if period_obj.status != "open":
            raise ValidationError(
                f"账期 {period} 当前状态为 {period_obj.status}，不可锁定"
            )
        period_obj.status = "locked"
        period_obj.locked_at = datetime.now()
        period_obj.locked_by = user_id
        await self.session.flush()
        logger.info(f"[Period] 门店 {self.store_id} 账期 {period} 已锁定")
        return period_obj

    async def close_period(self, period: str, user_id: uuid.UUID) -> Period:
        """关账: locked -> closed"""
        period_obj = await self.get_period(period)
        if not period_obj:
            raise NotFoundError(f"账期 {period} 不存在")
        if period_obj.status != "locked":
            raise ValidationError(
                f"账期 {period} 当前状态为 {period_obj.status}，需先锁定再关账"
            )
        period_obj.status = "closed"
        period_obj.closed_at = datetime.now()
        period_obj.closed_by = user_id
        await self.session.flush()
        logger.info(f"[Period] 门店 {self.store_id} 账期 {period} 已关账")
        return period_obj

    async def reopen_period(self, period: str, user_id: uuid.UUID) -> Period:
        """重新开放账期: locked/closed -> open（需老板权限）"""
        period_obj = await self.get_period(period)
        if not period_obj:
            raise NotFoundError(f"账期 {period} 不存在")
        if period_obj.status == "open":
            raise ValidationError(f"账期 {period} 已是 open 状态")
        period_obj.status = "open"
        period_obj.note = f"由 user {user_id} 重新开放"
        await self.session.flush()
        logger.info(f"[Period] 门店 {self.store_id} 账期 {period} 已重新开放")
        return period_obj
