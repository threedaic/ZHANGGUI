"""
全局定时任务调度器 (APScheduler)
在 lifespan 中启动，所有模块在此注册定时任务。
所有时间基于 Asia/Shanghai (UTC+8)。

班次检查时间：启动时读取 shift_configs 注册 cron；保存班次时实时更新。

多 worker 防护：当 uvicorn 以 --workers N 启动时，每个进程会各自启动 scheduler
导致定时任务重复执行。通过 SCHEDULER_ENABLED 环境变量控制只在指定 worker 启动。
单 worker 部署（当前腾讯云）默认启用；多 worker 时需设置 SCHEDULER_ENABLED=false
到除主 worker 外的其他进程，或改用 SQLAlchemyJobStore + Redis 分布式锁。
"""
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')


def schedule_shift_check(shift_code: str, start_time: str, shift_name: str = "") -> None:
    """注册/更新班次到岗检查 cron 任务：上班时间 + 1 小时。

    保存班次配置后由 API 直接调用，无需轮询。
    """
    from app.tasks.notification_jobs import shift_check_job
    from loguru import logger

    parts = start_time.split(":")
    h, m = int(parts[0]), int(parts[1]) + 60
    if m >= 60:
        h += 1
        m -= 60
    job_id = f"shift_check_{shift_code}"
    scheduler.add_job(
        shift_check_job,
        'cron',
        hour=h,
        minute=m,
        args=[shift_code],
        id=job_id,
        replace_existing=True,
    )
    name_str = f" ({shift_name})" if shift_name else ""
    logger.info(f"班次检查已注册: {shift_code}{name_str} -> 每天 {h:02d}:{m:02d}")


async def init_scheduler():
    """在 app lifespan startup 中调用。"""
    # 多 worker 防护：SCHEDULER_ENABLED=false 时不启动，避免重复执行
    if os.getenv("SCHEDULER_ENABLED", "true").lower() == "false":
        logger.info("SCHEDULER_ENABLED=false，跳过定时任务启动（多 worker 部署模式）")
        return

    from app.tasks.antifraud import run_daily_antifraud_scan
    from app.tasks.notification_jobs import (
        daily_attendance_report_job,
        auto_sync_checkin_job,
        auto_sync_wework_contacts_job,
        auto_push_workbench_job,
        monthly_attendance_confirm_job,
        cleanup_checkin_photos_job,
    )
    from app.tasks.wine_stocktake_job import monthly_wine_stocktake_job
    from app.tasks.butler_reminder import butler_opening_reminder_job, butler_closing_reminder_job
    from app.tasks.task_recurrence_job import task_recurrence_job
    from loguru import logger

    scheduler.add_job(auto_sync_checkin_job, 'cron', hour=10, minute=0, id='auto_sync_checkin_job', replace_existing=True)
    scheduler.add_job(auto_sync_wework_contacts_job, 'cron', hour=10, minute=3, id='auto_sync_wework_contacts_job', replace_existing=True)
    scheduler.add_job(daily_attendance_report_job, 'cron', hour=10, minute=5, id='daily_attendance_report_job', replace_existing=True)
    # 每日 00:05 自动生成周期任务（基于 oa_task_templates）
    scheduler.add_job(task_recurrence_job, 'cron', hour=0, minute=5, id='task_recurrence_job', replace_existing=True)
    # 每小时推送工作台数据（今日业绩/打卡状态）到所有员工
    scheduler.add_job(auto_push_workbench_job, 'interval', hours=1, id='auto_push_workbench_job', replace_existing=True)
    scheduler.add_job(run_daily_antifraud_scan, 'cron', hour=4, minute=0, id='run_daily_antifraud_scan', replace_existing=True)
    scheduler.add_job(monthly_attendance_confirm_job, 'cron', day=1, hour=2, minute=0, id='monthly_attendance_confirm_job', replace_existing=True)
    # 每天 04:00 清理过期打卡照片（保留WiFi/时间元数据，仅删照片文件）
    scheduler.add_job(cleanup_checkin_photos_job, 'cron', hour=4, minute=30, id='cleanup_checkin_photos_job', replace_existing=True)
    # 每月1号 02:30 自动生成存酒盘点单
    scheduler.add_job(monthly_wine_stocktake_job, 'cron', day=1, hour=2, minute=30, id='monthly_wine_stocktake_job', replace_existing=True)

    # 开闭店检查单超时提醒：读取各门店 schedule_time 注册 cron（默认 11:00 开店、23:00 闭店）
    await _register_butler_reminder_jobs()

    # 启动时从数据库读取所有班次配置，注册检查任务
    await _register_all_shift_checks()

    # 注册打印队列处理任务（每30秒执行一次）
    from app.tasks.print_queue_job import process_print_queue_job
    scheduler.add_job(
        process_print_queue_job,
        'interval',
        seconds=30,
        id='process_print_queue_job',
        replace_existing=True,
    )

    scheduler.start()

    jobs = scheduler.get_jobs()
    logger.info(f"定时任务已启动: {len(jobs)} 个")
    for job in jobs:
        logger.info(f"  - {job.name}: {job.next_run_time}")


async def _register_butler_reminder_jobs():
    """读取各门店的 butler_opening_overdue / butler_closing_overdue schedule_time，
    为每个不同的时间注册 cron job。未配置则用默认时间（11:00 / 23:00）。
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.notification import NotificationSetting
    from app.tasks.butler_reminder import butler_opening_reminder_job, butler_closing_reminder_job

    opening_times = set()  # {("11", "00"), ("10", "30"), ...}
    closing_times = set()

    async with AsyncSessionLocal() as session:
        # 读取所有门店的开闭店提醒 schedule_time
        result = await session.execute(
            select(NotificationSetting.setting_key, NotificationSetting.schedule_time)
            .where(NotificationSetting.setting_key.in_(
                ["butler_opening_overdue", "butler_closing_overdue"]
            ))
        )
        for key, st in result.all():
            if not st:
                continue
            try:
                parts = st.split(":")
                h, m = parts[0], parts[1]
                if key == "butler_opening_overdue":
                    opening_times.add((h, m))
                else:
                    closing_times.add((h, m))
            except Exception:
                pass

    # 默认时间
    opening_times.add(("11", "00"))
    closing_times.add(("23", "00"))

    for h, m in opening_times:
        job_id = f"butler_opening_reminder_{h}{m}"
        scheduler.add_job(
            butler_opening_reminder_job,
            'cron',
            hour=int(h), minute=int(m),
            id=job_id, replace_existing=True,
        )
        logger.info(f"开店检查单提醒已注册: {h}:{m}")

    for h, m in closing_times:
        job_id = f"butler_closing_reminder_{h}{m}"
        scheduler.add_job(
            butler_closing_reminder_job,
            'cron',
            hour=int(h), minute=int(m),
            id=job_id, replace_existing=True,
        )
        logger.info(f"闭店检查单提醒已注册: {h}:{m}")


def refresh_butler_reminder_jobs():
    """当推送设置变更后，重新注册开闭店提醒 cron job（同步版本，供 API 调用）。
    注意：此函数会先移除旧的 butler_*_reminder job，再重新注册。
    """
    import asyncio
    # 移除旧 job
    for job in scheduler.get_jobs():
        if job.id.startswith("butler_opening_reminder") or job.id.startswith("butler_closing_reminder"):
            scheduler.remove_job(job.id)
    # 重新注册（异步函数需在事件循环中执行）
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_register_butler_reminder_jobs())
        else:
            loop.run_until_complete(_register_butler_reminder_jobs())
    except Exception as e:
        logger.error(f"刷新开闭店提醒任务失败: {e}")


async def _register_all_shift_checks():
    """启动时从数据库读取所有门店的班次配置，注册检查任务。

    SPEC 2.0：store_id 是 UUID，不能硬编码 1。
    改为遍历所有门店的班次配置。
    """
    from app.database import AsyncSessionLocal
    from app.repositories.attendance import AttendanceRepository
    from sqlalchemy import select
    from app.models.store import Store

    async with AsyncSessionLocal() as session:
        try:
            # 查所有门店 ID（SPEC 2.0: UUID）
            store_result = await session.execute(select(Store.id))
            store_ids = [row[0] for row in store_result.fetchall()]
            from loguru import logger
            logger.info(f"班次检查注册: 发现 {len(store_ids)} 个门店")
            for sid in store_ids:
                repo = AttendanceRepository(session, str(sid))
                configs = await repo.get_shift_configs(active_only=True)
                for cfg in configs:
                    schedule_shift_check(cfg.shift_code, cfg.start_time, cfg.shift_name)
        except Exception as e:
            from loguru import logger
            logger.error(f"班次检查启动注册失败: {e}")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
