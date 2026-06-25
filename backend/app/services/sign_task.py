"""
签收任务 Service — 业务逻辑层
"""
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.sign_task import SignTask
from app.models.employee import Employee
from app.models.user import User
from app.repositories.sign_task import SignTaskRepository
from app.utils.pagination import PageParams
from app.services.inbox_types import InboxType, get_inbox_type


class SignTaskService:
    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.session = session
        self.store_id = store_id
        self.repo = SignTaskRepository(session, store_id)

    async def create_task(
        self,
        employee_id: uuid.UUID,
        task_type: str,
        title: str,
        ref_type: str,
        ref_id: uuid.UUID,
        issued_by: uuid.UUID,
        extra: dict[str, Any] | None = None,
    ) -> SignTask:
        task = SignTask(
            store_id=self.store_id,
            employee_id=employee_id,
            type=task_type,
            title=title,
            ref_type=ref_type,
            ref_id=ref_id,
            status="pending",
            issued_by=issued_by,
            issued_at=datetime.now(timezone.utc),
            extra=extra,
        )
        task = await self.repo.create(task)
        logger.info(f"签收任务已创建: {task_type} employee={employee_id} ref={ref_type}/{ref_id}")
        return task

    async def create_batch(
        self,
        employee_ids: list[uuid.UUID],
        task_type: str,
        title_template: str,
        ref_type: str,
        ref_ids: list[uuid.UUID],
        issued_by: uuid.UUID,
        extra: dict[str, Any] | None = None,
    ) -> list[SignTask]:
        """批量创建签收任务，一个员工一条"""
        tasks = []
        for i, emp_id in enumerate(employee_ids):
            title = title_template
            ref_id = ref_ids[i] if i < len(ref_ids) else 0
            task = await self.create_task(
                employee_id=emp_id,
                task_type=task_type,
                title=title,
                ref_type=ref_type,
                ref_id=ref_id,
                issued_by=issued_by,
                extra=extra,
            )
            tasks.append(task)
        return tasks

    # ================================================================
    #  标准化收件箱发送方法（推荐所有新代码用这个）
    # ================================================================
    async def send_to_inbox(
        self,
        employee_id: uuid.UUID,
        msg_type: str,
        ref_id: uuid.UUID,
        issued_by: uuid.UUID,
        extra: dict[str, Any] | None = None,
    ) -> SignTask:
        """
        统一收件箱发送入口。

        参数:
            employee_id: 接收员工ID
            msg_type:     消息类型（见 InboxType 枚举）
            ref_id:       关联业务记录ID（工资单ID/考勤ID/罚单ID）
            issued_by:    发送人员工ID
            extra:        附加数据，用于填充标题模板和详情页展示

        标题、ref_type 由 inbox_types.py 注册表自动填充。
        extra 里必须包含标题模板所需的占位字段。

        示例:
            await service.send_to_inbox(
                employee_id=emp_id,
                msg_type=InboxType.SALARY_SLIP,
                ref_id=wage_id,
                issued_by=boss_id,
                extra={"period": "2026-07", "employee_name": "张吧员", "net_pay": 3250},
            )
        """
        meta = get_inbox_type(msg_type)
        if not meta:
            raise ValueError(f"未知的收件箱消息类型: {msg_type}，请在 inbox_types.py 中注册")

        # 用 extra 填充标题模板
        title = meta.title_template
        if extra:
            try:
                title = title.format(**extra)
            except KeyError as e:
                logger.warning(f"收件箱标题模板缺字段: {e}，用原始模板")

        task = await self.create_task(
            employee_id=employee_id,
            task_type=meta.code,
            title=title,
            ref_type=meta.ref_type,
            ref_id=ref_id,
            issued_by=issued_by,
            extra=extra,
        )
        logger.info(
            f"[收件箱] 推送: type={msg_type} to={employee_id} title={title}"
        )
        return task

    async def send_batch_to_inbox(
        self,
        employee_ids: list[uuid.UUID],
        msg_type: str,
        ref_ids: list[uuid.UUID],
        issued_by: uuid.UUID,
        extra_list: list[dict[str, Any]] | None = None,
    ) -> list[SignTask]:
        """批量发送收件箱消息（一个员工一条）"""
        meta = get_inbox_type(msg_type)
        if not meta:
            raise ValueError(f"未知的收件箱消息类型: {msg_type}")

        tasks = []
        for i, emp_id in enumerate(employee_ids):
            ref_id = ref_ids[i] if i < len(ref_ids) else ref_ids[0]
            extra = extra_list[i] if extra_list and i < len(extra_list) else None
            task = await self.send_to_inbox(
                employee_id=emp_id,
                msg_type=msg_type,
                ref_id=ref_id,
                issued_by=issued_by,
                extra=extra,
            )
            tasks.append(task)
        return tasks

    async def get_inbox(
        self,
        employee_id: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        params = PageParams(page=page, page_size=page_size)
        tasks, total = await self.repo.list_inbox(employee_id, status=status, page=params)
        items = await self._enrich_tasks(tasks)
        return items, total

    async def get_pending_count(self, employee_id: uuid.UUID) -> int:
        return await self.repo.get_pending_count(employee_id)

    async def get_detail(self, task_id: uuid.UUID, employee_id: uuid.UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        # employee_id 可能是 str（来自JWT）或 UUID，统一转 UUID 再比较
        emp_uuid = employee_id if isinstance(employee_id, uuid.UUID) else uuid.UUID(str(employee_id))
        if not task or task.employee_id != emp_uuid:
            return None
        items = await self._enrich_tasks([task])
        return items[0] if items else None

    async def sign(self, task_id: uuid.UUID, employee_id: uuid.UUID, signature_data: str, notes: str | None = None) -> bool:
        ok = await self.repo.sign(task_id, employee_id, signature_data, notes)
        if ok:
            # 更新关联业务表状态
            await self._sync_ref_status(task_id, "signed")
        return ok

    async def batch_sign(
        self,
        task_ids: list[uuid.UUID],
        employee_id: uuid.UUID,
        signature_data: str,
        notes: str | None = None,
    ) -> dict:
        """批量签收：用同一份签名签收多个任务"""
        success: list[int] = []
        failed: list[dict] = []
        for tid in task_ids:
            ok = await self.repo.sign(tid, employee_id, signature_data, notes)
            if ok:
                await self._sync_ref_status(tid, "signed")
                success.append(tid)
            else:
                failed.append({"task_id": tid, "reason": "任务不存在或已处理"})
        return {
            "success_count": len(success),
            "failed_count": len(failed),
            "success_ids": success,
            "failed": failed,
        }

    async def dispute(self, task_id: uuid.UUID, employee_id: uuid.UUID, reason: str) -> bool:
        ok = await self.repo.dispute(task_id, employee_id, reason)
        if ok:
            await self._notify_dispute(task_id)
        return ok

    async def revoke(self, task_id: uuid.UUID, reason: str | None = None, revoked_by: uuid.UUID | None = None) -> bool:
        return await self.repo.revoke(task_id, reason=reason, revoked_by=revoked_by)

    async def get_issued(
        self,
        issued_by: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        params = PageParams(page=page, page_size=page_size)
        tasks, total = await self.repo.list_issued(issued_by, status=status, page=params)
        items = await self._enrich_tasks(tasks)
        return items, total

    async def get_disputes(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        params = PageParams(page=page, page_size=page_size)
        tasks, total = await self.repo.list_disputes(page=params)
        items = await self._enrich_tasks(tasks)
        return items, total

    async def _enrich_tasks(self, tasks: list[SignTask]) -> list[dict]:
        """充实展示字段：employee_name, issued_by_name, ref_data"""
        if not tasks:
            return []

        # 收集所有需要查的 employee_id
        emp_ids = set()
        emp_ids.update(t.employee_id for t in tasks)
        emp_ids.update(t.issued_by for t in tasks)

        stmt = select(Employee).where(
            Employee.id.in_(list(emp_ids)),
            Employee.store_id == self.store_id,
        )
        result = await self.session.execute(stmt)
        emp_map = {e.id: e for e in result.scalars().all()}

        items = []
        for t in tasks:
            emp = emp_map.get(t.employee_id)
            issuer = emp_map.get(t.issued_by)
            item = {
                "id": t.id,
                "store_id": t.store_id,
                "employee_id": t.employee_id,
                "type": t.type,
                "title": t.title,
                "ref_type": t.ref_type,
                "ref_id": t.ref_id,
                "status": t.status,
                "signed_at": t.signed_at.isoformat() if t.signed_at else None,
                "signature_data": t.signature_data,
                "dispute_reason": t.dispute_reason,
                "disputed_at": t.disputed_at.isoformat() if t.disputed_at else None,
                "issued_by": t.issued_by,
                "issued_at": t.issued_at.isoformat() if t.issued_at else None,
                "notes": t.notes,
                "extra": t.extra,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "employee_name": emp.name if emp else f"员工{t.employee_id}",
                "issued_by_name": issuer.name if issuer else f"员工{t.issued_by}",
                "ref_data": None,  # 详情接口按需加载
            }
            items.append(item)
        return items

    async def _sync_ref_status(self, task_id: uuid.UUID, new_status: str):
        """签收后同步关联业务表状态"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return
        try:
            if task.ref_type == "wage_record" and new_status == "signed":
                from app.models.payroll import PayrollRecord
                from sqlalchemy import update
                stmt = (
                    update(PayrollRecord)
                    .where(PayrollRecord.id == task.ref_id)
                    .values(status="confirmed")
                )
                await self.session.execute(stmt)
            elif task.ref_type == "penalty_notice" and new_status == "signed":
                from app.models.penalty_notice import PenaltyNotice
                from sqlalchemy import update
                stmt = (
                    update(PenaltyNotice)
                    .where(PenaltyNotice.id == task.ref_id)
                    .values(status="acknowledged")
                )
                await self.session.execute(stmt)
        except Exception as e:
            logger.warning(f"同步关联业务状态失败: {e}")

    async def _notify_dispute(self, task_id: uuid.UUID):
        """异议通知推送给 boss + store_manager + accountant"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return
        try:
            from app.services.notification_service import NotificationService
            notifier = NotificationService(self.session, self.store_id)
            target_user_ids = await notifier._resolve_user_ids_by_roles(
                ["boss", "store_manager", "accountant"]
            )
            content = f"员工对「{task.title}」提出异议。\n理由：{task.dispute_reason}"
            await notifier.send(
                notification_type="sign_dispute",
                title=f"签收异议 - {task.title}",
                content=content,
                target_user_ids=target_user_ids,
                channel="all",
                extra={"task_id": task_id, "employee_id": task.employee_id},
            )
        except Exception as e:
            logger.error(f"异议通知推送失败: {e}")
