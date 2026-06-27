"""
OA 任务数据访问层
"""
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import OaTask, OaTaskTemplate, OaTaskAttachment


class TaskRepository:
    def __init__(self, db: AsyncSession, store_id: str):
        self.db = db
        self.store_id = store_id

    # ===================== 任务 =====================

    async def create_task(self, title: str, description: str, priority: str,
                          task_type: str, created_by: str, assignee_id: str | None = None,
                          due_date: str | None = None, template_id: str | None = None,
                          require_photo: bool = False, require_note: bool = False,
                          requirements: str | None = None) -> OaTask:
        task = OaTask(
            store_id=uuid.UUID(self.store_id),
            title=title,
            description=description,
            priority=priority,
            task_type=task_type,
            created_by=uuid.UUID(created_by),
            assignee_id=uuid.UUID(assignee_id) if assignee_id else None,
            due_date=date.fromisoformat(due_date) if due_date else None,
            template_id=uuid.UUID(template_id) if template_id else None,
            require_photo=require_photo,
            require_note=require_note,
            requirements=requirements,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_task(self, task_id: str) -> OaTask | None:
        result = await self.db.execute(
            select(OaTask).where(
                OaTask.id == uuid.UUID(task_id),
                OaTask.store_id == uuid.UUID(self.store_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_tasks(self, status: str | None = None, task_type: str | None = None,
                         priority: str | None = None, assignee_id: str | None = None,
                         page: int = 1, page_size: int = 20) -> tuple[list[OaTask], int]:
        conditions = [OaTask.store_id == uuid.UUID(self.store_id)]
        if status:
            conditions.append(OaTask.status == status)
        if task_type:
            conditions.append(OaTask.task_type == task_type)
        if priority:
            conditions.append(OaTask.priority == priority)
        if assignee_id:
            conditions.append(OaTask.assignee_id == uuid.UUID(assignee_id))

        where = and_(*conditions)

        # Count
        count_q = select(func.count()).select_from(OaTask).where(where)
        total = (await self.db.execute(count_q)).scalar() or 0

        # Page
        q = select(OaTask).where(where).order_by(
            OaTask.status == 'pending',  # 待处理排前面
            OaTask.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        tasks = list(result.scalars().all())

        return tasks, total

    async def list_pool_tasks(self, page: int = 1, page_size: int = 20) -> tuple[list[OaTask], int]:
        """认领池：task_type=pool 且 assignee_id IS NULL 且 status=pending"""
        where = and_(
            OaTask.store_id == uuid.UUID(self.store_id),
            OaTask.task_type == "pool",
            OaTask.assignee_id.is_(None),
            OaTask.status == "pending",
        )
        count_q = select(func.count()).select_from(OaTask).where(where)
        total = (await self.db.execute(count_q)).scalar() or 0

        q = select(OaTask).where(where).order_by(OaTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def update_task(self, task_id: str, updates: dict):
        if "due_date" in updates and isinstance(updates["due_date"], str) and updates["due_date"]:
            updates["due_date"] = date.fromisoformat(updates["due_date"])
        if "assignee_id" in updates and isinstance(updates["assignee_id"], str) and updates["assignee_id"]:
            updates["assignee_id"] = uuid.UUID(updates["assignee_id"])
        elif "assignee_id" in updates and updates["assignee_id"] is None:
            updates["assignee_id"] = None
        updates["updated_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(OaTask).where(
                OaTask.id == uuid.UUID(task_id),
                OaTask.store_id == uuid.UUID(self.store_id),
            ).values(**updates)
        )
        await self.db.flush()

    # ===================== 附件 =====================

    async def create_attachment(self, task_id: str, uploaded_by: str,
                                file_url: str, file_name: str | None,
                                file_size: int | None, stage: str) -> OaTaskAttachment:
        att = OaTaskAttachment(
            task_id=uuid.UUID(task_id),
            uploaded_by=uuid.UUID(uploaded_by),
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            stage=stage,
        )
        self.db.add(att)
        await self.db.flush()
        return att

    async def get_attachment(self, att_id: str) -> OaTaskAttachment | None:
        result = await self.db.execute(
            select(OaTaskAttachment).where(OaTaskAttachment.id == uuid.UUID(att_id))
        )
        return result.scalar_one_or_none()

    async def get_attachments(self, task_id: str) -> list[OaTaskAttachment]:
        result = await self.db.execute(
            select(OaTaskAttachment).where(OaTaskAttachment.task_id == uuid.UUID(task_id)).order_by(OaTaskAttachment.created_at)
        )
        return list(result.scalars().all())

    async def count_attachments(self, task_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(OaTaskAttachment).where(OaTaskAttachment.task_id == uuid.UUID(task_id))
        )
        return result.scalar() or 0

    async def count_attachments_batch(self, task_ids: list[str]) -> dict:
        """批量查询附件数，返回 {task_id_str: count} 映射，解决 N+1"""
        if not task_ids:
            return {}
        result = await self.db.execute(
            select(OaTaskAttachment.task_id, func.count()).where(
                OaTaskAttachment.task_id.in_([uuid.UUID(tid) for tid in task_ids])
            ).group_by(OaTaskAttachment.task_id)
        )
        return {str(row[0]): row[1] for row in result.all()}

    async def delete_attachment(self, att_id: str):
        await self.db.execute(
            delete(OaTaskAttachment).where(OaTaskAttachment.id == uuid.UUID(att_id))
        )
        await self.db.flush()

    # ===================== 模板 =====================

    async def create_template(self, title: str, description: str, priority: str,
                              assignee_id: str, due_time: str | None, recurrence_type: str,
                              recurrence_rule: dict, created_by: str,
                              require_photo: bool = False, require_note: bool = False,
                              requirements: str | None = None) -> OaTaskTemplate:
        tpl = OaTaskTemplate(
            store_id=uuid.UUID(self.store_id),
            title=title,
            description=description,
            priority=priority,
            assignee_id=uuid.UUID(assignee_id),
            due_time=due_time,
            recurrence_type=recurrence_type,
            recurrence_rule=recurrence_rule,
            created_by=uuid.UUID(created_by),
            require_photo=require_photo,
            require_note=require_note,
            requirements=requirements,
        )
        self.db.add(tpl)
        await self.db.flush()
        return tpl

    async def get_template(self, template_id: str) -> OaTaskTemplate | None:
        result = await self.db.execute(
            select(OaTaskTemplate).where(
                OaTaskTemplate.id == uuid.UUID(template_id),
                OaTaskTemplate.store_id == uuid.UUID(self.store_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(self) -> list[OaTaskTemplate]:
        result = await self.db.execute(
            select(OaTaskTemplate).where(
                OaTaskTemplate.store_id == uuid.UUID(self.store_id)
            ).order_by(OaTaskTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_template(self, template_id: str, updates: dict):
        updates["updated_at"] = datetime.now(timezone.utc)
        if "assignee_id" in updates and isinstance(updates["assignee_id"], str):
            updates["assignee_id"] = uuid.UUID(updates["assignee_id"])
        await self.db.execute(
            update(OaTaskTemplate).where(
                OaTaskTemplate.id == uuid.UUID(template_id),
                OaTaskTemplate.store_id == uuid.UUID(self.store_id),
            ).values(**updates)
        )
        await self.db.flush()

    async def delete_template(self, template_id: str):
        await self.db.execute(
            delete(OaTaskTemplate).where(
                OaTaskTemplate.id == uuid.UUID(template_id),
                OaTaskTemplate.store_id == uuid.UUID(self.store_id),
            )
        )
        await self.db.flush()

    # ===================== 名称查询 =====================

    async def get_user_names(self, user_ids: list[str]) -> list:
        from app.models.user import User
        from app.models.employee import Employee
        result = await self.db.execute(
            select(User.id, Employee.name).join(Employee, User.employee_id == Employee.id).where(
                User.id.in_([uuid.UUID(uid) for uid in user_ids])
            )
        )
        return list(result.all())

    async def get_employee_names(self, employee_ids: list[str]) -> list:
        from app.models.employee import Employee
        result = await self.db.execute(
            select(Employee.id, Employee.name).where(
                Employee.id.in_([uuid.UUID(eid) for eid in employee_ids])
            )
        )
        return list(result.all())

    async def list_active_employees(self) -> list:
        from app.models.employee import Employee
        role_labels = {
            "boss": "老板", "store_manager": "店长", "bar_manager": "吧台长",
            "kitchen_manager": "厨房主管", "service_manager": "前厅主管",
            "staff": "员工", "accountant": "会计",
            "system_admin": "系统管理员", "admin": "管理员",
        }
        # 排除管理角色（不属于门店日常任务执行人）
        excluded_roles = ("boss", "admin", "system_admin")
        result = await self.db.execute(
            select(Employee.id, Employee.name, Employee.role).where(
                Employee.store_id == uuid.UUID(self.store_id),
                Employee.status == "active",
                ~Employee.role.in_(excluded_roles),
            ).order_by(Employee.name)
        )
        rows = result.all()
        return [(r[0], r[1], r[2], role_labels.get(r[2], r[2])) for r in rows]
