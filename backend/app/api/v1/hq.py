"""总店后台 API 路由（HQ — Headquarters）

前缀: /api/v1/hq (由 main.py 提供)

权限: 仅 system_admin（系统管理员/管理群成员）可访问。
      参见 SPEC §0：管理群成员 = system_admin，管全品牌全部门店。

端点:
  GET  "/stores"     → 全部门店列表（含员工数+今日营收）
  POST "/stores"     → 新建门店
  GET  "/dashboard"  → 全品牌数据看板（汇总全部门店）
  GET  "/employees"  → 全品牌员工列表
"""

from datetime import date
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from loguru import logger

from app.database import AsyncSessionLocal, set_session_context
from app.models.store import Store, StoreSettings
from app.models.employee import Employee
from app.utils.deps import make_response
from app.utils.exceptions import ForbiddenError, ValidationError, NotFoundError
from app.schemas.store import StoreCreate

router = APIRouter()


# ============================================================
# 专用 DB 依赖：system_admin 用 admin 权限绕过 RLS，可看全部门店
# ============================================================
async def get_db_hq(request: Request):
    """HQ 专用数据库 session。

    安全设计：
    1. API 层：检查 request.state.role == 'system_admin'，非系统管理员直接 403
    2. DB 层：将 session 角色设为 'admin'，绕过 RLS 行级安全策略
    这样 system_admin 可以跨门店查询全品牌数据。
    """
    role = getattr(request.state, "role", None)
    if role != "system_admin":
        raise ForbiddenError("仅系统管理员可访问总店后台")

    user_id = getattr(request.state, "user_id", None)
    async with AsyncSessionLocal() as session:
        # 用 admin 角色绕过 RLS，可以查询全部门店数据
        await set_session_context(session, store_id=None, user_id=user_id, role="admin")
        yield session


# ============================================================
# 门店管理
# ============================================================
@router.get("/stores")
async def list_all_stores(
    request: Request,
    db: AsyncSession = Depends(get_db_hq),
):
    """全部门店列表（含每店员工数、今日营收）。仅 system_admin。"""
    # 查全部门店
    stmt = select(Store).order_by(Store.opened_at.asc().nullslast())
    result = await db.execute(stmt)
    stores = result.scalars().all()

    store_ids = [s.id for s in stores]

    # 批量查每店员工数
    emp_counts = {}
    if store_ids:
        emp_stmt = (
            select(Employee.store_id, func.count(Employee.id))
            .where(Employee.store_id.in_(store_ids), Employee.status == "active")
            .group_by(Employee.store_id)
        )
        emp_result = await db.execute(emp_stmt)
        for sid, cnt in emp_result.all():
            emp_counts[str(sid)] = cnt

    # 批量查每店今日营收
    revenue_map = {}
    if store_ids:
        rev_stmt = text(
            "SELECT store_id, COALESCE(SUM("
            "  COALESCE(pos_revenue,0) + COALESCE(wecom_revenue,0) + "
            "  COALESCE(cash_revenue,0) + COALESCE(member_revenue,0)"
            "), 0) as revenue "
            "FROM fin_daily_revenue WHERE date = :today "
            "GROUP BY store_id"
        )
        rev_result = await db.execute(rev_stmt, {"today": date.today()})
        for row in rev_result:
            revenue_map[str(row[0])] = float(row[1])

    stores_data = []
    for s in stores:
        sid = str(s.id)
        stores_data.append({
            "id": sid,
            "name": s.name,
            "store_code": s.store_code,
            "city": s.city,
            "address": s.address,
            "status": s.status,
            "opened_at": s.opened_at.isoformat() if s.opened_at else None,
            "employee_count": emp_counts.get(sid, 0),
            "today_revenue": revenue_map.get(sid, 0),
            "wework_department_id": s.wework_department_id,
            "wework_status": s.wework_status,
        })

    return make_response(data=stores_data, request=request)


@router.post("/stores")
async def create_store(
    body: StoreCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_hq),
):
    """新建门店。仅 system_admin。

    创建后会自动初始化 StoreSettings 默认配置行。
    """
    # 检查 store_code 唯一性
    existing = await db.execute(
        select(Store).where(Store.store_code == body.store_code)
    )
    if existing.scalar_one_or_none():
        raise ValidationError(f"门店编号 {body.store_code} 已存在")

    # 创建门店
    store = Store(
        store_code=body.store_code,
        name=body.name,
        city=body.city,
        address=body.address,
        wework_department_id=body.wework_department_id,
        status="active",
        daily_booking_limit=30,
        brand_fee_rate=0.05,
        wework_status="pending" if body.wework_department_id else None,
    )
    db.add(store)
    await db.flush()  # 拿到 store.id

    # 初始化默认 StoreSettings
    settings = StoreSettings(store_id=store.id)
    db.add(settings)

    await db.commit()
    logger.info(f"[HQ] 新建门店: {store.name} ({store.store_code}) id={store.id}")

    return make_response(
        message=f"门店「{store.name}」创建成功",
        data={
            "id": str(store.id),
            "name": store.name,
            "store_code": store.store_code,
            "city": store.city,
            "address": store.address,
            "wework_department_id": store.wework_department_id,
        },
        request=request,
    )


# ============================================================
# 全局看板
# ============================================================
@router.get("/dashboard")
async def global_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db_hq),
):
    """全品牌数据看板（汇总全部门店）。仅 system_admin。"""
    today = date.today()

    # 门店总数
    store_count_result = await db.execute(
        select(func.count(Store.id)).where(Store.status == "active")
    )
    store_count = store_count_result.scalar() or 0

    # 全品牌员工总数
    emp_count_result = await db.execute(
        select(func.count(Employee.id)).where(Employee.status == "active")
    )
    emp_count = emp_count_result.scalar() or 0

    # 全品牌今日营收
    # fin_daily_revenue 没有 total_revenue 列，需手动相加四项
    rev_sum = ("COALESCE(pos_revenue,0) + COALESCE(wecom_revenue,0) + "
               "COALESCE(cash_revenue,0) + COALESCE(member_revenue,0)")
    today_revenue_result = await db.execute(
        text(
            f"SELECT COALESCE(SUM({rev_sum}), 0) FROM fin_daily_revenue "
            "WHERE date = :today"
        ),
        {"today": today},
    )
    today_revenue = float(today_revenue_result.scalar() or 0)

    # 全品牌昨日营收（算增长率）
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    yesterday_revenue_result = await db.execute(
        text(
            f"SELECT COALESCE(SUM({rev_sum}), 0) FROM fin_daily_revenue "
            "WHERE date = :yesterday"
        ),
        {"yesterday": yesterday},
    )
    yesterday_revenue = float(yesterday_revenue_result.scalar() or 0)

    growth_rate = 0
    if yesterday_revenue > 0:
        growth_rate = round(
            (today_revenue - yesterday_revenue) / yesterday_revenue * 100, 1
        )

    # 近7天营收趋势（全品牌汇总）
    chart_result = await db.execute(
        text(
            f"SELECT date, COALESCE(SUM({rev_sum}), 0) as revenue "
            "FROM fin_daily_revenue "
            "WHERE date >= :start_date "
            "GROUP BY date ORDER BY date"
        ),
        {"start_date": today - timedelta(days=6)},
    )
    chart = [
        {"date": str(row[0]), "revenue": float(row[1])}
        for row in chart_result
    ]

    # 各店今日营收明细
    store_revenue_result = await db.execute(
        text(
            "SELECT s.store_id, s.store_name, COALESCE(r.revenue, 0) as revenue, "
            "COALESCE(e.emp_count, 0) as emp_count "
            "FROM shared_stores s "
            f"LEFT JOIN (SELECT store_id, SUM({rev_sum}) as revenue "
            "  FROM fin_daily_revenue WHERE date = :today GROUP BY store_id) r "
            "  ON s.store_id = r.store_id "
            "LEFT JOIN (SELECT store_id, COUNT(*) as emp_count "
            "  FROM shared_employees WHERE status = 'active' GROUP BY store_id) e "
            "  ON s.store_id = e.store_id "
            "WHERE s.status = 'active' ORDER BY s.opened_at ASC NULLS LAST"
        ),
        {"today": today},
    )
    store_breakdown = [
        {
            "store_id": str(row[0]),
            "store_name": row[1],
            "today_revenue": float(row[2]),
            "employee_count": int(row[3]),
        }
        for row in store_revenue_result
    ]

    return make_response(data={
        "store_count": store_count,
        "employee_count": emp_count,
        "today_revenue": today_revenue,
        "yesterday_revenue": yesterday_revenue,
        "growth_rate": growth_rate,
        "chart": chart,
        "store_breakdown": store_breakdown,
    }, request=request)


# ============================================================
# 全局员工
# ============================================================
@router.get("/employees")
async def list_all_employees(
    request: Request,
    db: AsyncSession = Depends(get_db_hq),
):
    """全品牌员工列表（跨门店）。仅 system_admin。"""
    stmt = (
        select(
            Employee.id,
            Employee.name,
            Employee.role,
            Employee.store_id,
            Store.name.label("store_name"),
            Employee.status,
            Employee.phone,
        )
        .outerjoin(Store, Employee.store_id == Store.id)
        .where(Employee.status == "active")
        .order_by(Store.name, Employee.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    employees = [
        {
            "id": str(row[0]),
            "name": row[1],
            "role": row[2],
            "store_id": str(row[3]) if row[3] else None,
            "store_name": row[4] or "未分配",
            "status": row[5],
            "phone": row[6],
        }
        for row in rows
    ]

    return make_response(data=employees, request=request)
