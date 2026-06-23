from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from loguru import logger
from app.config import get_settings
from app.database import engine, AsyncSessionLocal
from app.models import Base
from app.models.user import User
from app.models.store import Store
from app.utils.security import hash_password
from app.utils.redis_client import init_redis, close_redis
from app.utils.exceptions import AppError
from app.utils.exceptions import app_error_handler, unhandled_error_handler
from app.api.v1.auth import router as auth_router
from app.api.v1.kpi import router as kpi_router
from app.api.v1.schedules import router as schedule_router
from app.api.v1.wines import router as wines_router
from app.api.v1.wine_stocktake import router as wine_stocktake_router
from app.api.v1.tables import router as tables_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.approval import router as approval_router
from app.api.v1.notifications import router as notification_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.antifraud import router as antifraud_router
from app.api.v1.payroll import router as payroll_router
from app.api.v1.payroll_config import router as payroll_config_router
from app.api.v1.period import router as period_router
from app.api.v1.ranking import router as ranking_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.ai import router as ai_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.leaves import router as leaves_router
from app.api.v1.store import router as store_router
from app.api.v1.audit import router as audit_router
from app.api.v1.butler import router as butler_router
from app.api.v1.sign_tasks import router as sign_tasks_router
from app.api.v1.penalties import router as penalties_router
from app.middleware.rls import RLSMiddleware
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.tasks.scheduler import init_scheduler, shutdown_scheduler

import os

# Log path configurable via environment (m-008 fix)
_log_path = os.getenv("LOG_PATH", "logs/crush-zhanggui.log")
logger.add(_log_path, rotation="10 MB", retention="7 days")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables (new SPEC 2.0 schema with UUID IDs)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"create_all 部分失败: {e}")

    # Seed data in separate transaction
    try:
        async with engine.begin() as conn:
            await seed_default_data(conn)
    except Exception as e:
        logger.warning(f"seed_default_data 跳过: {e}")

    await init_redis()
    await init_scheduler()
    from app.utils.audit_logger import init_audit_logger
    init_audit_logger()
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    yield
    # Shutdown
    shutdown_scheduler()
    from app.utils.http_client import http_client
    await http_client.close()
    await close_redis()
    await engine.dispose()


async def seed_default_data(conn):
    """Insert demo data if tables are empty.

    SPEC 2.0：种子数据插入新表（shared_stores/shared_store_settings/shared_employees/sys_users）。
    """
    result = await conn.execute(text("SELECT user_id FROM sys_users LIMIT 1"))
    if result.scalar_one_or_none() is not None:
        return

    # Store (shared_stores) — 先插门店，拿到 store_id
    # 注意：raw SQL INSERT 不会触发 ORM 的 Python 端 default，必须显式提供所有 NOT NULL 字段
    store_result = await conn.execute(
        text(
            "INSERT INTO shared_stores (store_code, store_name, address, region, status, daily_booking_limit, brand_fee_rate) "
            "VALUES ('BJ-SLT-001', '北京三里屯店', "
            "'北京市朝阳区工人体育场北路4号80号楼一层113室', '北京', 'active', 30, 0.05) "
            "RETURNING store_id"
        )
    )
    store_id = store_result.scalar_one()

    # Store settings (shared_store_settings)
    await conn.execute(
        text(
            "INSERT INTO shared_store_settings (store_id) VALUES (:store_id)"
        ),
        {"store_id": store_id},
    )

    # Employees (shared_employees)
    employees = [
        ("EMP001", "老板", "boss", 8000.0, "day", True),
        ("EMP002", "张吧员", "bar_manager", 5000.0, "night", False),
        ("EMP003", "李服务员", "staff", 4000.0, "day", False),
        ("EMP004", "王厨师", "kitchen_manager", 4500.0, "day", False),
        ("EMP005", "赵店长", "store_manager", 6000.0, "day", True),
    ]
    emp_ids = []
    for code, name, role, salary, shift_group, is_manager in employees:
        res = await conn.execute(
            text(
                "INSERT INTO shared_employees (store_id, employee_code, name, role, base_salary, hire_date, status, shift_group, is_first_manager) "
                "VALUES (:store_id, :code, :name, :role, :salary, CURRENT_DATE, 'active', :shift_group, :is_mgr) "
                "RETURNING employee_id"
            ),
            {
                "store_id": store_id,
                "code": code,
                "name": name,
                "role": role,
                "salary": salary,
                "shift_group": shift_group,
                "is_mgr": is_manager,
            },
        )
        emp_ids.append((name, res.scalar_one()))

    # Admin user (sys_users) — 老板账号
    boss_emp_id = emp_ids[0][1]  # 老板的 employee_id
    await conn.execute(
        text(
            "INSERT INTO sys_users (store_id, employee_id, username, password_hash, role, is_active, must_change_password) "
            "VALUES (:store_id, :emp_id, :u, :p, 'boss', true, false)"
        ),
        {
            "store_id": store_id,
            "emp_id": boss_emp_id,
            "u": settings.SEED_BOSS_USERNAME,
            "p": hash_password(settings.SEED_BOSS_PASSWORD),
        }
    )
    # NOTE: do NOT call conn.commit() — engine.begin() manages the transaction

    # Seed default butler checklists
    await seed_default_checklists(conn, store_id)


async def seed_default_checklists(conn, store_id):
    """Insert default butler checklists if none exist for this store."""
    result = await conn.execute(
        text("SELECT template_id FROM butler_checklist_templates WHERE store_id = :store_id LIMIT 1"),
        {"store_id": store_id},
    )
    if result.scalar_one_or_none() is not None:
        return

    default_templates = [
        {
            "name": "店长闭店检查单",
            "session_type": "closing",
            "role_tag": "store_manager",
            "sort_order": 1,
            "items": [
                ("确认所有客人已离场", "photo"),
                ("检查洗手间是否有人", "checkbox"),
                ("核对当日营业额", "checkbox"),
                ("现金存入保险柜", "checkbox"),
                ("锁闭大门", "photo"),
                ("关闭所有灯光", "photo"),
                ("关闭音响", "photo"),
                ("关闭招牌", "photo"),
                ("检查后厨是否关闭", "photo"),
                ("设防/开启警报", "checkbox"),
            ],
        },
        {
            "name": "吧台长闭店检查单",
            "session_type": "closing",
            "role_tag": "bartender",
            "sort_order": 2,
            "items": [
                ("清空冰槽（烧冰）", "photo"),
                ("清洁吧台台面", "photo"),
                ("清洁苏打枪", "photo"),
                ("储存剩余水果和装饰物", "photo"),
                ("新开酒瓶标注日期", "photo"),
                ("清洗杯具并晾干", "photo"),
                ("清洁地面和地漏", "photo"),
                ("倒垃圾", "photo"),
            ],
        },
        {
            "name": "服务员闭店检查单",
            "session_type": "closing",
            "role_tag": "server",
            "sort_order": 3,
            "items": [
                ("清理所有桌面", "photo"),
                ("椅子归位", "photo"),
                ("扫地", "photo"),
                ("拖地", "photo"),
                ("清空垃圾桶并换袋", "photo"),
                ("清洁卫生间", "photo"),
            ],
        },
        {
            "name": "店长开店检查单",
            "session_type": "opening",
            "role_tag": "store_manager",
            "sort_order": 1,
            "items": [
                ("开门前检查门外是否有杂物", "photo"),
                ("检查店内是否有异常（异味、漏水等）", "checkbox"),
                ("开启灯光", "photo"),
                ("开启音响", "photo"),
                ("开启招牌灯", "photo"),
                ("检查POS机是否正常", "photo"),
                ("准备现金抽屉", "checkbox"),
                ("开晨会/班前会", "checkbox"),
            ],
        },
    ]

    for tpl in default_templates:
        result = await conn.execute(
            text(
                "INSERT INTO butler_checklist_templates (store_id, name, session_type, role_tag, sort_order, is_active) "
                "VALUES (:store_id, :name, :session_type, :role_tag, :sort_order, true) RETURNING template_id"
            ),
            {
                "store_id": store_id,
                "name": tpl["name"],
                "session_type": tpl["session_type"],
                "role_tag": tpl["role_tag"],
                "sort_order": tpl["sort_order"],
            },
        )
        tpl_id = result.scalar_one()

        for i, (item_name, item_type) in enumerate(tpl["items"]):
            await conn.execute(
                text(
                    "INSERT INTO butler_checklist_items (template_id, item_name, item_type, required_photo, sort_order) "
                    "VALUES (:template_id, :item_name, :item_type, :required_photo, :sort_order)"
                ),
                {
                    "template_id": tpl_id,
                    "item_name": item_name,
                    "item_type": item_type,
                    "required_photo": item_type == "photo",
                    "sort_order": i + 1,
                },
            )
    # NOTE: do NOT call conn.commit() — engine.begin() manages the transaction


# 生产环境关闭 API 文档（防止暴露接口结构）
_is_prod = settings.APP_ENV == "production"
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

# Middleware: order matters
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RLSMiddleware)
app.add_middleware(AuditMiddleware)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

# Request body size limit (I-002: 10 MB max)
MAX_BODY_SIZE = 10 * 1024 * 1024

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"code": 41300, "message": "请求体过大，最大 10 MB", "data": None, "request_id": None},
        )
    return await call_next(request)

# Routes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(kpi_router, prefix="/api/v1/kpi", tags=["KPI考核"])
app.include_router(schedule_router, prefix="/api/v1/schedules", tags=["排班管理"])
# 注意：stocktake 必须在 wines 之前注册，否则 /wine-storage/stocktake 会被 /wine-storage/{wine_id} 抢先匹配
app.include_router(wine_stocktake_router, prefix="/api/v1/wine-storage", tags=["存酒盘点"])
app.include_router(wines_router, prefix="/api/v1/wine-storage", tags=["存酒管理"])
app.include_router(tables_router, prefix="/api/v1/tables", tags=["桌位管理"])
app.include_router(bookings_router, prefix="/api/v1/reservations", tags=["订桌预约"])
app.include_router(ratings_router, prefix="/api/v1/ratings", tags=["桌面评分码"])
app.include_router(attendance_router, prefix="/api/v1/attendance", tags=["考勤管理"])
app.include_router(approval_router, prefix="/api/v1/approvals", tags=["审批管理"])
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["消息通知"])
app.include_router(contracts_router, prefix="/api/v1/contracts", tags=["合同系统"])
app.include_router(antifraud_router, prefix="/api/v1/antifraud", tags=["防飞单"])
app.include_router(payroll_router, prefix="/api/v1/payroll", tags=["工资计算"])
app.include_router(payroll_config_router, prefix="/api/v1/payroll-config", tags=["工资项配置"])
app.include_router(period_router, prefix="/api/v1/periods", tags=["账期管理"])
app.include_router(ranking_router, prefix="/api/v1/rankings", tags=["员工排名"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["数据看板"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["小C AI助手"])
app.include_router(store_router, prefix="/api/v1/stores", tags=["门店配置"])
app.include_router(leaves_router, prefix="/api/v1", tags=["假期余额"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["操作日志"])
app.include_router(butler_router, prefix="/api/v1/butler", tags=["开闭店管理"])
app.include_router(sign_tasks_router, prefix="/api/v1/sign-tasks", tags=["签收任务"])
app.include_router(penalties_router, prefix="/api/v1/penalties", tags=["处罚通知"])

# 静态文件服务（上传的图片等）
import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles
_uploads_root = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "uploads")
_os.makedirs(_uploads_root, exist_ok=True)
app.mount("/uploads", _StaticFiles(directory=_uploads_root), name="uploads")


@app.get("/health", tags=["system"])
async def health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        from app.utils.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        return {"status": "healthy", "db": "ok", "redis": "ok"}
    except Exception as e:
        # In production, hide internal details (m-002 fix)
        is_prod = settings.APP_ENV == "production"
        error_detail = "service degraded" if is_prod else str(e)
        return {"status": "degraded", "error": error_detail}
