from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from loguru import logger
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"ssl": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _sanitize_session_value(value: str) -> str:
    """净化 session 变量值，防止 SQL 注入。

    PG SET 命令不支持参数绑定，必须用 f-string，但值必须净化。
    允许字符：字母、数字、下划线、连字符、UUID 的连字符。
    """
    return "".join(c for c in str(value) if c.isalnum() or c in ("_", "-"))


async def set_session_context(
    session: AsyncSession,
    store_id: str | int | None = None,
    user_id: str | int | None = None,
    role: str | None = None,
) -> None:
    """Set PostgreSQL session variables for Row-Level Security.

    依据 SPEC 2.0 §3.3：
    - 使用 SET LOCAL（事务内生效）
    - 变量名：app.current_store_id / app.current_user_id / app.current_role
    - RLS 策略：current_setting('app.current_store_id', true)::uuid
    - admin 角色豁免：current_setting('app.current_role', true) = 'admin'

    支持 UUID（Crush 2.0 新表）和 int（旧表）两种 store_id 格式。
    """
    # app.current_store_id — 支持 UUID 或 int
    try:
        if store_id is not None:
            safe_store = _sanitize_session_value(store_id)
            await session.execute(text(f"SET LOCAL app.current_store_id = '{safe_store}'"))
        else:
            await session.execute(text("SET LOCAL app.current_store_id = ''"))
    except Exception as e:
        logger.warning(f"SET LOCAL app.current_store_id failed: {e}")

    # app.current_user_id
    try:
        if user_id is not None:
            safe_user = _sanitize_session_value(user_id)
            await session.execute(text(f"SET LOCAL app.current_user_id = '{safe_user}'"))
        else:
            await session.execute(text("SET LOCAL app.current_user_id = ''"))
    except Exception as e:
        logger.warning(f"SET LOCAL app.current_user_id failed: {e}")

    # app.current_user_role — SPEC 2.0 角色名（admin/boss/store_manager 等）
    # 注：不能用 app.current_role，因为 current_role 是 PG 保留关键字，
    # SET app.current_role = ... 会报语法错误。
    # 所有 RLS 策略统一读取 app.current_user_role。
    try:
        if role is not None:
            safe_role = _sanitize_session_value(role)
            await session.execute(text(f"SET LOCAL app.current_user_role = '{safe_role}'"))
        else:
            await session.execute(text("SET LOCAL app.current_user_role = ''"))
    except Exception as e:
        logger.warning(f"SET LOCAL app.current_user_role failed: {e}")


async def get_db(request: Request = None) -> AsyncSession:
    """Yield a database session with RLS context set from request.

    依据 SPEC 2.0 §3.3：每个请求开始时设置 session 变量，
    使 PostgreSQL RLS 策略能自动按门店隔离数据。

    双层隔离：
    - PG RLS：数据库层强制，无法绕过
    - 应用层：request.state 供业务逻辑判断
    """
    async with AsyncSessionLocal() as session:
        # Always set PG session context for RLS (even on public endpoints)
        store_id = None
        user_id = None
        role = None
        if request is not None:
            store_id = getattr(request.state, "store_id", None)
            user_id = getattr(request.state, "user_id", None)
            role = getattr(request.state, "role", None)
        await set_session_context(session, store_id, user_id, role)
        yield session
