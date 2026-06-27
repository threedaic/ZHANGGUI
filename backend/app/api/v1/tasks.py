"""
OA 任务管理 API

路由映射：
GET  /              任务列表（管理端）
POST /              创建任务
GET  /my            我的任务
GET  /pool          认领池
GET  /{task_id}     任务详情
PATCH /{task_id}    编辑任务
PATCH /{task_id}/status  更新状态
POST /{task_id}/claim    认领
POST /{task_id}/attachments  上传照片
GET  /{task_id}/attachments  获取照片
DELETE /{task_id}/attachments/{att_id}  删除照片

周期模板：
GET  /templates          模板列表
POST /templates          创建模板
PATCH /templates/{id}    编辑模板
PATCH /templates/{id}/toggle  启用/停用
DELETE /templates/{id}   删除模板
"""
import uuid
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.database import get_db
from app.models.task import OaTask, OaTaskTemplate, OaTaskAttachment
from app.repositories.task import TaskRepository
from app.utils.deps import get_store_id, get_user_id, get_employee_id, require_role, make_response
from app.utils.exceptions import ValidationError, NotFoundError, ForbiddenError, ConflictError

router = APIRouter()

# ===================== 工具函数 =====================

def _task_to_dict(task, creator_name="", assignee_name="", attachments_count=0) -> dict:
    return {
        "id": task.id,
        "store_id": task.store_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "priority_label": {"high": "紧急", "medium": "普通", "low": "低"}.get(task.priority, "普通"),
        "status": task.status,
        "status_label": {"pending": "待处理", "in_progress": "进行中", "completed": "已完成", "cancelled": "已取消"}.get(task.status, ""),
        "task_type": task.task_type,
        "task_type_label": {"direct": "指派任务", "pool": "认领任务", "recurring": "周期任务"}.get(task.task_type, ""),
        "created_by": task.created_by,
        "created_by_name": creator_name,
        "assignee_id": task.assignee_id,
        "assignee_name": assignee_name,
        "due_date": str(task.due_date) if task.due_date else None,
        "template_id": task.template_id,
        "created_at": str(task.created_at) if task.created_at else None,
        "updated_at": str(task.updated_at) if task.updated_at else None,
        "completed_at": str(task.completed_at) if task.completed_at else None,
        "attachments_count": attachments_count,
        # 完成要求
        "require_photo": getattr(task, "require_photo", False) or False,
        "require_note": getattr(task, "require_note", False) or False,
        "requirements": getattr(task, "requirements", None),
        "completion_note": getattr(task, "completion_note", None),
    }


async def _build_name_maps(repo, tasks):
    """构建创建人和执行人名字映射"""
    creator_ids = set()
    assignee_ids = set()
    for t in tasks:
        if t.created_by:
            creator_ids.add(str(t.created_by))
        if t.assignee_id:
            assignee_ids.add(str(t.assignee_id))

    creator_map = {}
    assignee_map = {}
    if creator_ids:
        rows = await repo.get_user_names(list(creator_ids))
        creator_map = {str(r[0]): r[1] for r in rows}
    if assignee_ids:
        rows = await repo.get_employee_names(list(assignee_ids))
        assignee_map = {str(r[0]): r[1] for r in rows}
    return creator_map, assignee_map


# ===================== 任务 CRUD =====================

@router.get("")
async def list_tasks(
    request: Request,
    status: str | None = Query(None),
    task_type: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """任务列表（管理端：店长/老板看全店，staff 看自己的）"""
    store_id = get_store_id(request)
    role = getattr(request.state, "role", "staff")
    employee_id = getattr(request.state, "employee_id", None)

    repo = TaskRepository(db, store_id)

    if role in ("boss", "store_manager", "system_admin", "admin"):
        tasks, total = await repo.list_tasks(
            status=status, task_type=task_type, priority=priority,
            assignee_id=assignee_id, page=page, page_size=page_size
        )
    else:
        tasks, total = await repo.list_tasks(
            status=status, task_type=task_type, priority=priority,
            assignee_id=employee_id, page=page, page_size=page_size
        )

    creator_map, assignee_map = await _build_name_maps(repo, tasks)
    att_count_map = await repo.count_attachments_batch([str(t.id) for t in tasks])
    items = []
    for t in tasks:
        items.append(_task_to_dict(
            t,
            creator_name=creator_map.get(str(t.created_by), ""),
            assignee_name=assignee_map.get(str(t.assignee_id), "") if t.assignee_id else "",
            attachments_count=att_count_map.get(str(t.id), 0),
        ))

    return make_response(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/my")
async def my_tasks(
    request: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """我的任务（所有角色）"""
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)
    repo = TaskRepository(db, store_id)

    tasks, total = await repo.list_tasks(
        status=status, assignee_id=employee_id, page=page, page_size=page_size
    )
    creator_map, assignee_map = await _build_name_maps(repo, tasks)
    att_count_map = await repo.count_attachments_batch([str(t.id) for t in tasks])
    items = []
    for t in tasks:
        items.append(_task_to_dict(t, creator_map.get(str(t.created_by), ""), assignee_map.get(str(t.assignee_id), ""), att_count_map.get(str(t.id), 0)))

    return make_response(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/pool")
async def task_pool(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """认领池（所有角色可看）"""
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)
    tasks, total = await repo.list_pool_tasks(page=page, page_size=page_size)
    creator_map, _ = await _build_name_maps(repo, tasks)
    items = [_task_to_dict(t, creator_map.get(str(t.created_by), "")) for t in tasks]
    return make_response(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.post("")
async def create_task(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建任务（仅店长/老板）"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)

    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        raise ValidationError("任务标题不能为空")
    if len(title) > 200:
        raise ValidationError("任务标题不能超过200字")

    task_type = body.get("task_type", "direct")
    if task_type not in ("direct", "pool"):
        raise ValidationError("任务类型只能是 direct 或 pool")
    assignee_id = body.get("assignee_id")
    if task_type == "direct" and not assignee_id:
        raise ValidationError("指派任务必须指定执行人")

    priority = body.get("priority", "medium")
    if priority not in ("high", "medium", "low"):
        priority = "medium"

    repo = TaskRepository(db, store_id)
    task = await repo.create_task(
        title=title,
        description=body.get("description", ""),
        priority=priority,
        task_type=task_type,
        created_by=user_id,
        assignee_id=assignee_id,
        due_date=body.get("due_date"),
        require_photo=bool(body.get("require_photo", False)),
        require_note=bool(body.get("require_note", False)),
        requirements=body.get("requirements") or None,
    )
    await db.commit()

    return make_response(message="任务创建成功", data=_task_to_dict(task))


# ===================== 周期模板（静态路由，必须在 /{task_id} 之前） =====================

@router.get("/templates")
async def list_templates(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """模板列表"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)
    templates = await repo.list_templates()

    # 获取执行人名称
    assignee_ids = [str(t.assignee_id) for t in templates]
    name_map = {}
    if assignee_ids:
        rows = await repo.get_employee_names(assignee_ids)
        name_map = {str(r[0]): r[1] for r in rows}

    items = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "assignee_id": t.assignee_id,
            "assignee_name": name_map.get(str(t.assignee_id), ""),
            "due_time": t.due_time,
            "recurrence_type": t.recurrence_type,
            "recurrence_type_label": {"daily": "每天", "weekly": "每周", "monthly": "每月"}.get(t.recurrence_type, ""),
            "recurrence_rule": t.recurrence_rule,
            "enabled": t.enabled,
            "created_at": str(t.created_at) if t.created_at else None,
            "last_generated_at": str(t.last_generated_at) if t.last_generated_at else None,
            "require_photo": getattr(t, "require_photo", False) or False,
            "require_note": getattr(t, "require_note", False) or False,
            "requirements": getattr(t, "requirements", None),
        }
        for t in templates
    ]
    return make_response(data=items)


@router.post("/templates")
async def create_template(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建周期模板"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)

    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        raise ValidationError("模板标题不能为空")

    recurrence_type = body.get("recurrence_type")
    if recurrence_type not in ("daily", "weekly", "monthly"):
        raise ValidationError("周期类型只能是 daily/weekly/monthly")

    assignee_id = body.get("assignee_id")
    if not assignee_id:
        raise ValidationError("必须指定执行人")

    repo = TaskRepository(db, store_id)
    tpl = await repo.create_template(
        title=title,
        description=body.get("description", ""),
        priority=body.get("priority", "medium"),
        assignee_id=assignee_id,
        due_time=body.get("due_time"),
        recurrence_type=recurrence_type,
        recurrence_rule=body.get("recurrence_rule", {}),
        created_by=user_id,
        require_photo=bool(body.get("require_photo", False)),
        require_note=bool(body.get("require_note", False)),
        requirements=body.get("requirements") or None,
    )
    await db.commit()

    return make_response(message="模板创建成功", data={"id": tpl.id})


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """编辑模板"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)

    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")

    body = await request.json()
    updates = {}
    if "title" in body:
        updates["title"] = body["title"].strip()
    if "description" in body:
        updates["description"] = body["description"]
    if "priority" in body:
        updates["priority"] = body["priority"]
    if "assignee_id" in body:
        updates["assignee_id"] = body["assignee_id"]
    if "due_time" in body:
        updates["due_time"] = body["due_time"]
    if "recurrence_type" in body:
        updates["recurrence_type"] = body["recurrence_type"]
    if "recurrence_rule" in body:
        updates["recurrence_rule"] = body["recurrence_rule"]
    if "require_photo" in body:
        updates["require_photo"] = bool(body["require_photo"])
    if "require_note" in body:
        updates["require_note"] = bool(body["require_note"])
    if "requirements" in body:
        updates["requirements"] = body["requirements"] or None

    if updates:
        await repo.update_template(template_id, updates)
        await db.commit()

    return make_response(message="更新成功")


@router.patch("/templates/{template_id}/toggle")
async def toggle_template(
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """启用/停用模板"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)

    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")

    await repo.update_template(template_id, {"enabled": not tpl.enabled})
    await db.commit()
    return make_response(message="已启用" if not tpl.enabled else "已停用")


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除模板"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)

    tpl = await repo.get_template(template_id)
    if not tpl:
        raise NotFoundError("模板不存在")

    await repo.delete_template(template_id)
    await db.commit()
    return make_response(message="删除成功")


# ===================== 员工列表（静态路由，必须在 /{task_id} 之前） =====================

@router.get("/employees")
async def list_employees(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取门店员工列表（用于分配任务）"""
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)
    employees = await repo.list_active_employees()
    items = [
        {"id": str(e[0]), "name": e[1], "role": e[2], "role_label": e[3]}
        for e in employees
    ]
    return make_response(data=items)


# ===================== 任务详情/编辑/状态（动态路由，必须在静态路由之后） =====================

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """任务详情"""
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    creator_map, assignee_map = await _build_name_maps(repo, [task])
    attachments = await repo.get_attachments(task_id)
    att_list = [
        {"id": a.id, "file_url": a.file_url, "file_name": a.file_name,
         "stage": a.stage, "uploaded_by": a.uploaded_by,
         "created_at": str(a.created_at) if a.created_at else None}
        for a in attachments
    ]

    result = _task_to_dict(
        task,
        creator_map.get(str(task.created_by), ""),
        assignee_map.get(str(task.assignee_id), "") if task.assignee_id else "",
        len(attachments),
    )
    result["attachments"] = att_list
    return make_response(data=result)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """编辑任务（仅创建人）"""
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = TaskRepository(db, store_id)

    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")
    if str(task.created_by) != user_id:
        raise ForbiddenError("仅创建人可编辑")

    body = await request.json()
    updates = {}
    if "title" in body:
        t = body["title"].strip()
        if not t:
            raise ValidationError("标题不能为空")
        updates["title"] = t
    if "description" in body:
        updates["description"] = body["description"]
    if "priority" in body and body["priority"] in ("high", "medium", "low"):
        updates["priority"] = body["priority"]
    if "due_date" in body:
        updates["due_date"] = body["due_date"]
    if "assignee_id" in body:
        updates["assignee_id"] = body["assignee_id"]
    if "require_photo" in body:
        updates["require_photo"] = bool(body["require_photo"])
    if "require_note" in body:
        updates["require_note"] = bool(body["require_note"])
    if "requirements" in body:
        updates["requirements"] = body["requirements"] or None

    if updates:
        await repo.update_task(task_id, updates)
        await db.commit()

    task = await repo.get_task(task_id)
    return make_response(message="更新成功", data=_task_to_dict(task))


@router.patch("/{task_id}/status")
async def update_status(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新任务状态"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    role = getattr(request.state, "role", "staff")
    employee_id = getattr(request.state, "employee_id", None)

    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    body = await request.json()
    new_status = body.get("status")
    if new_status not in ("in_progress", "completed", "cancelled"):
        raise ValidationError("无效的状态")

    # 权限检查
    is_creator = str(task.created_by) == user_id
    is_assignee = task.assignee_id and str(task.assignee_id) == employee_id
    is_admin = role in ("boss", "store_manager", "system_admin", "admin")

    if new_status == "cancelled":
        if not is_creator and not is_admin:
            raise ForbiddenError("仅创建人可取消任务")
    elif not is_assignee and not is_creator and not is_admin:
        raise ForbiddenError("无权操作此任务")

    # 状态流转检查
    if task.status == "completed" and new_status != "completed":
        raise ConflictError("已完成的任务不可修改")
    if task.status == "cancelled":
        raise ConflictError("已取消的任务不可修改")

    from datetime import datetime, timezone
    updates = {"status": new_status}
    if new_status == "completed":
        updates["completed_at"] = datetime.now(timezone.utc)
        # 完成校验：require_photo=true 必须先上传至少一张照片
        if getattr(task, "require_photo", False):
            att_count = await repo.count_attachments(task_id)
            if att_count == 0:
                raise ValidationError("此任务要求完成时上传照片，请先上传至少一张照片")
        # 完成校验：require_note=true 必须有完成说明（已暂存 note 优先，否则用 body 传的）
        if getattr(task, "require_note", False):
            existing_note = (getattr(task, "completion_note", "") or "").strip()
            new_note = (body.get("completion_note") or "").strip()
            note = new_note or existing_note
            if not note:
                raise ValidationError("此任务要求填写完成说明，请补充完成说明后再标记完成")
            updates["completion_note"] = note
        elif "completion_note" in body:
            # 即使不强制 require_note，也允许完成时附带 note
            note = (body.get("completion_note") or "").strip()
            if note:
                updates["completion_note"] = note

    await repo.update_task(task_id, updates)
    await db.commit()
    task = await repo.get_task(task_id)
    return make_response(message="状态已更新", data=_task_to_dict(task))


@router.patch("/{task_id}/note")
async def update_note(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """执行人暂存执行反馈文字（completion_note），不限任务状态。

    - 权限：执行人本人 / 创建人 / admin 角色
    - 任务已完成/已取消时拒绝修改
    - 完成任务时如果 require_note=true，已暂存的 note 直接生效，不再要求重填
    """
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    role = getattr(request.state, "role", "staff")
    employee_id = getattr(request.state, "employee_id", None)

    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    if task.status in ("completed", "cancelled"):
        raise ConflictError("任务已结束，无法修改反馈")

    is_assignee = task.assignee_id and str(task.assignee_id) == employee_id
    is_creator = str(task.created_by) == user_id
    is_admin = role in ("boss", "store_manager", "system_admin", "admin")
    if not (is_assignee or is_creator or is_admin):
        raise ForbiddenError("仅执行人/创建人/管理员可编辑反馈")

    body = await request.json()
    note = (body.get("completion_note") or "").strip()
    if len(note) > 2000:
        raise ValidationError("反馈内容不能超过 2000 字")

    await repo.update_task(task_id, {"completion_note": note})
    await db.commit()
    task = await repo.get_task(task_id)
    return make_response(message="已保存", data=_task_to_dict(task))


@router.post("/{task_id}/claim")
async def claim_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """认领任务"""
    store_id = get_store_id(request)
    employee_id = get_employee_id(request)

    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")
    if task.task_type != "pool":
        raise ConflictError("该任务不是认领类型")
    if task.assignee_id:
        raise ConflictError("该任务已被认领")
    if task.status != "pending":
        raise ConflictError("该任务不在待认领状态")

    await repo.update_task(task_id, {
        "assignee_id": employee_id,
        "status": "in_progress",
    })
    await db.commit()
    task = await repo.get_task(task_id)
    return make_response(message="认领成功", data=_task_to_dict(task))


# ===================== 附件 =====================

@router.post("/{task_id}/attachments")
async def upload_attachment(
    task_id: str,
    request: Request,
    stage: str = Form("progress"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传任务照片"""
    import os, uuid as _uuid, asyncio
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    employee_id = get_employee_id(request)

    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    if task.assignee_id and str(task.assignee_id) != employee_id:
        role = getattr(request.state, "role", "staff")
        if role not in ("boss", "store_manager", "system_admin", "admin"):
            raise ForbiddenError("仅执行人可上传照片")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise ValidationError("仅支持 JPG/PNG/WebP 格式")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise ValidationError("文件大小不能超过 10MB")

    # 扩展名从 content_type 推导，不信任客户端 filename，防 XSS
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")
    filename = f"task_{task_id[:8]}_{_uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "tasks")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    # 异步写文件，避免阻塞事件循环
    await asyncio.to_thread(_write_file_sync, filepath, contents)

    file_url = f"/uploads/tasks/{filename}"

    attachment = await repo.create_attachment(
        task_id=task_id,
        uploaded_by=user_id,
        file_url=file_url,
        file_name=file.filename,
        file_size=len(contents),
        stage=stage,
    )
    await db.commit()

    return make_response(message="上传成功", data={"id": str(attachment.id), "file_url": file_url})


def _write_file_sync(filepath: str, contents: bytes):
    """同步写文件辅助函数，供 asyncio.to_thread 调用"""
    with open(filepath, "wb") as f:
        f.write(contents)


@router.get("/{task_id}/attachments")
async def list_attachments(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取任务照片列表"""
    store_id = get_store_id(request)
    repo = TaskRepository(db, store_id)
    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    attachments = await repo.get_attachments(task_id)
    items = [
        {"id": str(a.id), "file_url": a.file_url, "file_name": a.file_name,
         "file_size": a.file_size, "stage": a.stage,
         "uploaded_by": str(a.uploaded_by),
         "created_at": str(a.created_at) if a.created_at else None}
        for a in attachments
    ]
    return make_response(data=items)


@router.delete("/{task_id}/attachments/{att_id}")
async def delete_attachment(
    task_id: str,
    att_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除照片"""
    store_id = get_store_id(request)
    user_id = get_user_id(request)
    repo = TaskRepository(db, store_id)

    task = await repo.get_task(task_id)
    if not task:
        raise NotFoundError("任务不存在")

    att = await repo.get_attachment(att_id)
    if not att or str(att.task_id) != task_id:
        raise NotFoundError("附件不存在")

    # 仅上传人和创建人可删
    role = getattr(request.state, "role", "staff")
    if str(att.uploaded_by) != user_id and str(task.created_by) != user_id:
        if role not in ("boss", "store_manager", "system_admin", "admin"):
            raise ForbiddenError("无权删除此附件")

    await repo.delete_attachment(att_id)
    await db.commit()
    return make_response(message="删除成功")
