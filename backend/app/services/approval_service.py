"""
统一审批 Service
- 请假、补卡、调班、加班、报销
- 审批通过后联动排班/考勤/工资
"""
from datetime import date, datetime
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.approval import ApprovalRequest
from app.models.attendance import AttendanceRecord
from app.repositories.approval import ApprovalRepository
from app.repositories.attendance import AttendanceRepository
from app.utils.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.services.attendance_push import push_approval_notification
from loguru import logger

TYPE_LABELS = {"leave": "请假", "makeup": "补卡", "swap": "调班", "expense": "报销"}


class ApprovalService:
    """审批 Service"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id
        self.repo = ApprovalRepository(session, store_id)
        self.attendance_repo = AttendanceRepository(session, store_id)

    async def create_approval(
        self,
        employee_id: int,
        approval_type: str,
        start_date: date | None,
        end_date: date | None,
        reason: str,
        extra: dict[str, Any] | None = None,
        approver_id: int | None = None,
    ) -> ApprovalRequest:
        if approval_type not in ("leave", "makeup", "swap", "expense"):
            raise ValidationError(f"不支持的审批类型: {approval_type}")

        # 类型相关必填校验
        if approval_type == "leave":
            if not start_date or not end_date:
                raise ValidationError("请假必须填写起止日期")
            if not extra or not extra.get("leave_type"):
                raise ValidationError("请选择请假类型")
            # 岗位覆盖率校验（病假除外）
            leave_type = extra.get("leave_type")
            if leave_type != "sick":
                await self._check_position_coverage(employee_id, start_date, end_date)
        elif approval_type == "makeup":
            if not extra or not extra.get("date"):
                raise ValidationError("补卡必须选择日期")
            if not extra.get("clock_in") and not extra.get("clock_out"):
                raise ValidationError("请至少填写上班或下班时间")
        elif approval_type == "swap":
            if not extra or not extra.get("to_employee_id"):
                raise ValidationError("请选择调班对象")
            if not extra.get("date"):
                raise ValidationError("请选择调班日期")
        elif approval_type == "expense":
            if not extra or extra.get("amount") is None:
                raise ValidationError("请填写报销金额")
            try:
                amount = float(extra.get("amount"))
                if amount <= 0:
                    raise ValueError()
            except (TypeError, ValueError):
                raise ValidationError("报销金额必须为正数")

        approval = ApprovalRequest(
            store_id=self.store_id,
            employee_id=employee_id,
            type=approval_type,
            status="pending",
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            extra=extra or {},
            approver_id=approver_id,
        )

        # 调班：自动指定被调班员工作为审批人
        if approval_type == "swap" and extra and extra.get("to_employee_id"):
            try:
                from sqlalchemy import select as sa_select
                from app.models.user import User
                to_emp_id = extra.get("to_employee_id")
                user_row = await self.session.execute(
                    sa_select(User.id).where(User.employee_id == to_emp_id)
                )
                to_user_id = user_row.scalar()
                if to_user_id:
                    approval.approver_id = to_user_id
            except Exception:
                logger.opt(exception=True).warning("查询被调班员工用户ID失败")

        result = await self.repo.create_approval(approval)
        await self.session.commit()

        # 通知审批人
        try:
            type_label = TYPE_LABELS.get(approval_type, approval_type)
            if approval_type == "swap" and approval.approver_id:
                # 调班：定向通知被调班员工
                from app.services.notification_service import NotificationService
                from app.models.employee import Employee
                from_emp_row = await self.session.execute(
                    sa_select(Employee.name).where(Employee.id == employee_id)
                )
                from_name = from_emp_row.scalar() or "员工"
                notif_svc = NotificationService(self.session, self.store_id)
                await notif_svc.send(
                    notification_type="approval_pending",
                    title=f"{from_name} 申请与您调班",
                    content=f"{from_name} 申请在 {extra.get('date')} 与您调班，请确认是否同意。",
                    target_user_ids=[approval.approver_id],
                    channel="all",
                    extra={"approval_id": result.id, "type": "swap"},
                )
            else:
                await push_approval_notification(
                    self.session, self.store_id, "approval",
                    f"新的{type_label}审批",
                    f"员工申请{type_label}，点击查看详情",
                )
        except Exception:
            logger.opt(exception=True).warning("创建审批通知发送失败，不阻断业务")

        return result

    async def approve(self, approval_id: int, approver_id: int) -> ApprovalRequest:
        approval = await self.repo.get_approval_by_id(approval_id)
        if not approval:
            raise NotFoundError("审批记录不存在")

        approval = await self.repo.update_approval(
            approval,
            status="approved",
            approver_id=approver_id,
            approved_at=datetime.now(),
        )

        # 联动处理
        await self._apply_approval(approval)
        await self.session.commit()

        # 通知提交人
        try:
            type_label = TYPE_LABELS.get(approval.type, approval.type)
            user_ids = await self._resolve_user_ids(approval.employee_id)
            if user_ids:
                await push_approval_notification(
                    self.session, self.store_id, "approval",
                    f"{type_label}审批已通过",
                    f"您的{type_label}申请已通过",
                    target_user_ids=user_ids,
                )
        except Exception:
            logger.opt(exception=True).warning(f"审批通过通知发送失败 approval_id={approval_id}")

        return approval

    async def _check_position_coverage(self, employee_id: int, start_date: date, end_date: date) -> None:
        """岗位覆盖率校验：请假后同岗位在岗比例不得低于配置阈值"""
        from sqlalchemy import select as sa_select, func, and_
        from app.models.employee import Employee
        from app.models.store import StoreSettings

        # 获取申请人岗位
        emp_row = await self.session.execute(
            sa_select(Employee.role).where(
                and_(Employee.id == employee_id, Employee.store_id == self.store_id)
            )
        )
        role = emp_row.scalar_one_or_none()
        if not role:
            return  # 找不到员工，跳过校验

        # 获取门店设置中的最低覆盖率
        settings_row = await self.session.execute(
            sa_select(StoreSettings.min_position_coverage_percent).where(
                StoreSettings.store_id == self.store_id
            )
        )
        min_percent = settings_row.scalar_one_or_none()
        if min_percent is None or min_percent <= 0:
            return  # 未配置或为0，跳过校验

        # 同岗位在职员工总数
        total_row = await self.session.execute(
            sa_select(func.count(Employee.id)).where(
                and_(
                    Employee.store_id == self.store_id,
                    Employee.role == role,
                    Employee.status == "active",
                )
            )
        )
        total_in_role = total_row.scalar() or 0
        if total_in_role <= 1:
            return  # 该岗位只有1人，无法限制

        # 查询该日期范围内，同岗位已批准请假的员工数（去重）
        # 已批准请假 = ApprovalRequest type=leave, status=approved, 日期有重叠
        from app.models.approval import ApprovalRequest
        overlap_row = await self.session.execute(
            sa_select(func.count(func.distinct(ApprovalRequest.employee_id))).where(
                and_(
                    ApprovalRequest.store_id == self.store_id,
                    ApprovalRequest.type == "leave",
                    ApprovalRequest.status == "approved",
                    ApprovalRequest.start_date <= end_date,
                    ApprovalRequest.end_date >= start_date,
                    ApprovalRequest.employee_id != employee_id,
                    ApprovalRequest.employee_id.in_(
                        sa_select(Employee.id).where(
                            and_(Employee.store_id == self.store_id, Employee.role == role)
                        )
                    ),
                )
            )
        )
        already_on_leave = overlap_row.scalar() or 0

        # 加上当前申请人，计算请假后的在岗覆盖率
        on_duty = total_in_role - already_on_leave - 1  # 减去已请假和当前申请人
        coverage_percent = (on_duty / total_in_role) * 100

        if coverage_percent < min_percent:
            raise ValidationError(
                f"岗位覆盖率不足：{role} 共 {total_in_role} 人，"
                f"此时段已有 {already_on_leave} 人请假，再请假将导致在岗率 "
                f"{coverage_percent:.0f}%，低于最低要求 {min_percent}%。"
                f"如确需请假，请改选病假或调整日期。"
            )

    async def reject(self, approval_id: int, approver_id: int, reject_reason: str | None = None) -> ApprovalRequest:
        approval = await self.repo.get_approval_by_id(approval_id)
        if not approval:
            raise NotFoundError("审批记录不存在")

        approval = await self.repo.update_approval(
            approval,
            status="rejected",
            approver_id=approver_id,
            approved_at=datetime.now(),
            reject_reason=reject_reason,
        )
        await self.session.commit()

        # 通知提交人
        try:
            type_label = TYPE_LABELS.get(approval.type, approval.type)
            user_ids = await self._resolve_user_ids(approval.employee_id)
            content = f"您的{type_label}申请已被驳回"
            if reject_reason:
                content += f"，原因：{reject_reason}"
            if user_ids:
                await push_approval_notification(
                    self.session, self.store_id, "approval",
                    f"{type_label}审批已驳回",
                    content,
                    target_user_ids=user_ids,
                )
        except Exception:
            logger.opt(exception=True).warning(f"审批驳回通知发送失败 approval_id={approval_id}")

        return approval

    async def _resolve_user_ids(self, employee_id: int) -> list[int]:
        from sqlalchemy import select as sa_select, and_
        from app.models.user import User
        stmt = sa_select(User.id).where(
            and_(User.employee_id == employee_id, User.is_active.is_(True))
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def _apply_approval(self, approval: ApprovalRequest) -> None:
        """审批通过后联动业务数据"""
        if approval.type == "leave" and approval.start_date and approval.end_date:
            current = approval.start_date
            while current <= approval.end_date:
                existing = await self.attendance_repo.get_record_by_employee_date(
                    approval.employee_id, current
                )
                if existing:
                    existing.scheduled_shift = "请假"
                    existing.status = "leave"
                else:
                    record = AttendanceRecord(
                        store_id=self.store_id,
                        employee_id=approval.employee_id,
                        date=current,
                        scheduled_shift="请假",
                        status="leave",
                        source="manual",
                    )
                    self.session.add(record)
                current += date.resolution

            # 扣减假期余额
            from app.repositories.leave_balance import LeaveBalanceRepository
            lb_repo = LeaveBalanceRepository(self.session, self.store_id)
            leave_type_bal = approval.extra.get("leave_type", "annual") if approval.extra else "annual"
            leave_days = ((approval.end_date - approval.start_date).days) + 1
            await lb_repo.deduct_leave(approval.employee_id, approval.start_date.year, leave_type_bal, float(leave_days))

        elif approval.type == "makeup" and approval.extra:
            target_date = approval.extra.get("date")
            clock_in = approval.extra.get("clock_in")
            clock_out = approval.extra.get("clock_out")
            if target_date:
                # 校验日期格式
                try:
                    if isinstance(target_date, str):
                        target_date = date.fromisoformat(target_date)
                    elif not isinstance(target_date, date):
                        raise ValueError
                except (ValueError, TypeError):
                    raise ValidationError(f"补签日期格式无效: {target_date}")
                existing = await self.attendance_repo.get_record_by_employee_date(
                    approval.employee_id, target_date
                )
                if existing:
                    if clock_in:
                        existing.clock_in = clock_in
                    if clock_out:
                        existing.clock_out = clock_out
                    existing.source = "makeup"
                else:
                    record = AttendanceRecord(
                        store_id=self.store_id,
                        employee_id=approval.employee_id,
                        date=target_date,
                        clock_in=clock_in,
                        clock_out=clock_out,
                        source="makeup",
                        status="unknown",
                    )
                    self.session.add(record)

        elif approval.type == "swap" and approval.extra:
            # 调班：交换双方某天的排班
            from_employee_id = approval.employee_id
            to_employee_id = approval.extra.get("to_employee_id")
            swap_date = approval.extra.get("date")
            if from_employee_id and to_employee_id and swap_date:
                from_record = await self.attendance_repo.get_record_by_employee_date(
                    from_employee_id, swap_date
                )
                to_record = await self.attendance_repo.get_record_by_employee_date(
                    to_employee_id, swap_date
                )
                from_shift = from_record.scheduled_shift if from_record else "休息"
                to_shift = to_record.scheduled_shift if to_record else "休息"

                if from_record:
                    from_record.scheduled_shift = to_shift
                else:
                    self.session.add(AttendanceRecord(
                        store_id=self.store_id,
                        employee_id=from_employee_id,
                        date=swap_date,
                        scheduled_shift=to_shift,
                        status="unknown",
                    ))

                if to_record:
                    to_record.scheduled_shift = from_shift
                else:
                    self.session.add(AttendanceRecord(
                        store_id=self.store_id,
                        employee_id=to_employee_id,
                        date=swap_date,
                        scheduled_shift=from_shift,
                        status="unknown",
                    ))

        await self.session.flush()
