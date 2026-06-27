"""
周期任务自动生成 Job

每日 00:05 扫描所有启用的 oa_task_templates，根据 recurrence_type + recurrence_rule
判断今日是否需要生成新任务，生成后更新 last_generated_at。

recurrence_rule 约定（与前端一致）：
- daily:  {} 空字典
- weekly: {"days_of_week": [0-6], "interval": 1}  # 0=周日（JS getDay 风格）
- monthly:{"day_of_month": 1-31, "interval": 1}
"""
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, set_session_context
from app.models.task import OaTaskTemplate, OaTask


def _js_weekday_to_py(js_day: int) -> int:
    """JS getDay() (0=周日) 转 Python weekday() (0=周一)。
    0(日)->6, 1(一)->0, 2(二)->1, ..., 6(六)->5
    """
    return (js_day - 1) % 7


def _should_generate_today(template: OaTaskTemplate, now: datetime) -> bool:
    """判断今天是否需要根据模板生成任务。"""
    today = now.date()
    # 已经在今天生成过则跳过
    if template.last_generated_at:
        # 转 +08:00 后比较日期
        local_ts = template.last_generated_at
        if local_ts.tzinfo is None:
            local_ts = local_ts.replace(tzinfo=timezone.utc)
        local_ts = local_ts.astimezone(timezone(timedelta(hours=8)))
        if local_ts.date() == today:
            return False

    rtype = template.recurrence_type
    rule = template.recurrence_rule or {}

    if rtype == "daily":
        return True

    if rtype == "weekly":
        days_of_week = rule.get("days_of_week") or []
        if not days_of_week:
            return False
        # today.weekday(): 0=周一 ... 6=周日
        # days_of_week: 0=周日 ... 6=周六（JS 风格）
        today_js_day = (today.weekday() + 1) % 7  # 周一(0) -> 1, 周日(6) -> 0
        return today_js_day in days_of_week

    if rtype == "monthly":
        dom = rule.get("day_of_month")
        if not dom or not (1 <= int(dom) <= 31):
            return False
        # 月末处理：dom > 当月最后一天时，在最后一天触发
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == int(dom) or (int(dom) > last_day and today.day == last_day)

    return False


def _compute_due_date(template: OaTaskTemplate, now: datetime):
    """根据模板 due_time 计算任务 due_date（datetime）。
    due_time 格式 "HH:MM"，返回当日 + 时分；为空返回 None。
    """
    if not template.due_time:
        return None
    try:
        h, m = template.due_time.split(":")
        # 当日 23:59 截止（避免跨日复杂度）
        return now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    except Exception:
        return None


async def task_recurrence_job():
    """每日凌晨扫描所有启用模板，生成周期任务。"""
    now = datetime.now(timezone(timedelta(hours=8)))  # Asia/Shanghai
    logger.info(f"[task_recurrence_job] 开始扫描周期任务模板 {now.isoformat()}")

    created_count = 0
    skipped_count = 0

    # job 直接使用 AsyncSessionLocal，不依赖 request 上下文（RLS 通过 admin 角色绕过）
    async with AsyncSessionLocal() as session:
        # 用 admin 角色绕过 RLS，避免门店过滤
        await set_session_context(session, role="admin")

        result = await session.execute(
            select(OaTaskTemplate).where(OaTaskTemplate.enabled == True)
        )
        templates = result.scalars().all()
        logger.info(f"[task_recurrence_job] 启用模板: {len(templates)} 个")

        for tpl in templates:
            try:
                if not _should_generate_today(tpl, now):
                    skipped_count += 1
                    continue

                # 检查今日是否已生成过（双重保险，防止 job 重复执行）
                existing = await session.execute(
                    select(OaTask.id).where(
                        OaTask.template_id == tpl.id,
                        OaTask.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
                    ).limit(1)
                )
                if existing.scalar_one_or_none():
                    skipped_count += 1
                    continue

                # 生成新任务
                due_at = _compute_due_date(tpl, now)
                task = OaTask(
                    store_id=tpl.store_id,
                    title=tpl.title,
                    description=tpl.description,
                    priority=tpl.priority,
                    status="pending",
                    task_type="recurring",
                    created_by=tpl.created_by,
                    assignee_id=tpl.assignee_id,
                    due_date=due_at.date() if due_at else None,
                    template_id=tpl.id,
                    # 完成要求从模板复制
                    require_photo=getattr(tpl, "require_photo", False) or False,
                    require_note=getattr(tpl, "require_note", False) or False,
                    requirements=getattr(tpl, "requirements", None),
                )
                session.add(task)
                tpl.last_generated_at = datetime.now(timezone.utc)
                created_count += 1
                logger.info(
                    f"[task_recurrence_job] 生成: tpl={tpl.id} title={tpl.title} store={tpl.store_id}"
                )
            except Exception as e:
                logger.exception(f"[task_recurrence_job] 模板 {tpl.id} 生成失败: {e}")

        await session.commit()

    logger.info(
        f"[task_recurrence_job] 完成: 生成 {created_count} 条, 跳过 {skipped_count} 条"
    )
