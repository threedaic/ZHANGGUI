"""
消息通知定时任务
"""
from datetime import date, timedelta
from app.database import AsyncSessionLocal
from app.services.attendance_push import push_daily_report
from app.services.wework import fetch_checkin_data
from app.repositories.notification import NotificationRepository
from loguru import logger


async def get_active_store_ids(session) -> list[int]:
    """获取所有启用的门店 ID"""
    from sqlalchemy import select
    from app.models.store import Store
    result = await session.execute(
        select(Store.id).where(Store.status == "active")
    )
    return [row[0] for row in result.all()]


async def auto_sync_checkin_job() -> None:
    """每天 10:00 同步前一天的完整打卡数据（日班+晚班均已完成）。"""
    from app.models.store import Store
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        try:
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            store_result = await session.execute(
                select(Store).where(Store.status == "active")
            )
            stores = store_result.scalars().all()
            for store in stores:
                if not store.wework_corp_id:
                    continue
                try:
                    result = await fetch_checkin_data(session, store.id, yesterday)
                    synced = result.get("synced", 0)
                    if synced > 0:
                        logger.info(f"自动同步打卡: 门店={store.name} 同步{synced}条")
                    await session.commit()
                except Exception as e:
                    logger.warning(f"自动同步打卡失败 门店={store.name}: {e}")
                    await session.rollback()
        except Exception as e:
            logger.error(f"自动同步打卡总任务失败: {e}")


async def daily_attendance_report_job() -> None:
    """每日考勤日报 — 改为 10:05 发送（跟 auto_sync 之后，数据完整）"""
    async with AsyncSessionLocal() as session:
        try:
            stores = await get_active_store_ids(session)
            for sid in stores:
                await push_daily_report(session, sid, date.today() - timedelta(days=1))
            await session.commit()
        except Exception as e:
            logger.error(f"每日考勤日报任务失败: {e}")
            await session.rollback()


async def shift_check_job(shift_code: str) -> None:
    """班次到岗检查：同步打卡 + 统计到岗情况 + 推送。

    使用独立 session 避免 commit 后 session 失效。
    """
    today = date.today().isoformat()

    # Phase 1: 拉打卡数据（独立 session，用完即关）
    from app.models.store import Store
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        try:
            store_result = await session.execute(
                select(Store).where(Store.status == "active")
            )
            stores = store_result.scalars().all()
            for store in stores:
                if store.wework_corp_id:
                    try:
                        await fetch_checkin_data(session, store.id, today)
                        await session.commit()
                    except Exception as e:
                        logger.warning(f"班次检查-同步打卡失败 门店={store.name}: {e}")
                        await session.rollback()
        except Exception as e:
            logger.error(f"班次检查-同步打卡总失败: {e}")

    # Phase 2: 推送到岗通知（全新 session）
    from app.services.attendance_push import push_shift_status

    async with AsyncSessionLocal() as session:
        try:
            await push_shift_status(session, 1, today, shift_code)
            await session.commit()
            logger.info(f"班次到岗通知已推送: {shift_code}")
        except Exception as e:
            logger.error(f"班次到岗检查失败 ({shift_code}): {e}")
            await session.rollback()


async def monthly_attendance_confirm_job() -> None:
    """每月 1 号凌晨 2:00 自动为所有员工生成上月考勤确认签收任务。"""
    from app.models.employee import Employee
    from app.models.attendance import AttendanceRecord
    from app.services.sign_task import SignTaskService
    from sqlalchemy import select, and_, func

    async with AsyncSessionLocal() as session:
        try:
            # 上月
            today = date.today()
            if today.month == 1:
                last_month = date(today.year - 1, 12, 1)
            else:
                last_month = date(today.year, today.month - 1, 1)
            period = last_month.strftime("%Y-%m")

            # 获取所有在职员工
            emp_result = await session.execute(
                select(Employee).where(and_(Employee.status == "active"))
            )
            employees = emp_result.scalars().all()
            if not employees:
                logger.info("考勤确认任务: 无在职员工，跳过")
                return

            # 查店长 employee_id 作为 issued_by
            from app.models.user import User
            boss_result = await session.execute(
                select(User.employee_id).where(
                    and_(User.role == "boss", User.is_active.is_(True))
                ).limit(1)
            )
            boss_emp_id = boss_result.scalar_one_or_none()

            created = 0

            for emp in employees:
                try:
                    # 按员工所属门店创建签收服务
                    sign_service = SignTaskService(session, store_id=emp.store_id)
                    title = f"考勤确认单 - {period}"
                    task = await sign_service.create_task(
                        employee_id=emp.id,
                        task_type="attendance_confirm",
                        title=title,
                        ref_type="attendance_summary",
                        ref_id=emp.id,  # 用 employee_id 作为 ref
                        issued_by=boss_emp_id or 1,
                        extra={"period": period},
                    )
                    created += 1
                except Exception as e:
                    logger.warning(f"考勤确认任务创建失败 employee={emp.id}: {e}")

            await session.commit()
            logger.info(f"考勤确认任务完成: 为 {created}/{len(employees)} 名员工创建签收任务")
        except Exception as e:
            logger.error(f"考勤确认任务总失败: {e}")
            await session.rollback()
