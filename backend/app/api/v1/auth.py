from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.store import Store
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserInfo
from app.utils.security import verify_password, create_access_token, create_refresh_token, decode_token, is_token_blacklisted, hash_password
from app.utils.exceptions import UnauthorizedError, ForbiddenError
from app.utils.redis_client import get_redis
from app.utils.deps import make_response
from app.config import get_settings
import secrets

router = APIRouter()

# 登录失败锁定配置（从 config 读取）
settings = get_settings()
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOCK_DURATION = settings.LOGIN_LOCKOUT_MINUTES * 60  # 转换为秒


def _to_str(val) -> str | None:
    """将 UUID 对象转为字符串，None 保持 None。JWT payload 需要可序列化的值。"""
    if val is None:
        return None
    return str(val)


@router.post("/login", response_model=dict)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from loguru import logger
    logger.info(f"[LOGIN] 开始登录: username={body.username}")
    # 基于 IP + 用户名 的失败计数，防止暴力破解
    client_ip = request.client.host if request.client else "unknown"
    lock_key = f"login_lock:{body.username}"
    fail_key = f"login_fail:{body.username}:{client_ip}"

    redis = await get_redis()

    # 检查是否已被锁定
    if await redis.exists(lock_key):
        ttl = await redis.ttl(lock_key)
        raise ForbiddenError(f"账户已被锁定，请 {ttl // 60 + 1} 分钟后再试")

    logger.info("[LOGIN] 查询用户")
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    logger.info(f"[LOGIN] 用户查询完成: user={'找到' if user else '未找到'}")

    if not user or not verify_password(body.password, user.password_hash):
        # 记录失败次数
        attempts = await redis.incr(fail_key)
        await redis.expire(fail_key, LOCK_DURATION)
        remaining = MAX_LOGIN_ATTEMPTS - attempts
        if remaining <= 0:
            # 达到上限，锁定账户
            await redis.set(lock_key, "1", ex=LOCK_DURATION)
            await redis.delete(fail_key)
            raise ForbiddenError(f"连续失败 {MAX_LOGIN_ATTEMPTS} 次，账户已被锁定 {settings.LOGIN_LOCKOUT_MINUTES} 分钟")
        raise UnauthorizedError(f"用户名或密码错误，剩余尝试次数 {remaining}")

    if not user.is_active:
        raise ForbiddenError("账户已被禁用")

    # 登录成功，清除失败计数
    await redis.delete(fail_key)
    await redis.delete(lock_key)

    # 获取 store_id：优先从 user.store_id（新表 sys_users 已有 store_id 字段）
    store_id = _to_str(user.store_id)
    logger.info(f"[LOGIN] user.store_id={store_id}")

    # 如果 user 没有 store_id，尝试从 employee 获取
    if store_id is None and user.employee_id:
        logger.info("[LOGIN] 从 employee 获取 store_id")
        emp_result = await db.execute(select(Employee).where(Employee.id == user.employee_id))
        emp = emp_result.scalar_one_or_none()
        if emp:
            store_id = _to_str(emp.store_id)
            logger.info(f"[LOGIN] emp.store_id={store_id}")

    # 老板账号没有具体门店时，默认使用第一个门店
    if store_id is None and user.role == "boss":
        logger.info("[LOGIN] boss 账号查第一个门店")
        first_store = await db.execute(select(Store).order_by(Store.id.asc()).limit(1))
        first_store_obj = first_store.scalar_one_or_none()
        if first_store_obj:
            store_id = _to_str(first_store_obj.id)
            logger.info(f"[LOGIN] first_store.id={store_id}")

    token_data = {
        "user_id": _to_str(user.id),
        "username": user.username,
        "role": user.role,
        "employee_id": _to_str(user.employee_id),
        "store_id": store_id,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return make_response(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "must_change_password": user.must_change_password,
        "user": {
            "user_id": _to_str(user.id),
            "username": user.username,
            "role": user.role,
            "employee_id": _to_str(user.employee_id),
            "store_id": store_id,
            "must_change_password": user.must_change_password,
        },
    }, request=request)


@router.post("/refresh", response_model=dict)
async def refresh(body: RefreshRequest, request: Request):
    # 1. Decode token
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("无效的 refresh token")

    # 2. Check blacklist (M-001 fix)
    if await is_token_blacklisted(body.refresh_token):
        raise UnauthorizedError("token 已被登出")

    token_data = {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "role": payload.get("role"),
        "employee_id": payload.get("employee_id"),
        "store_id": payload.get("store_id"),
    }
    access_token = create_access_token(token_data)

    return make_response(data={
        "access_token": access_token,
        "token_type": "bearer",
    }, request=request)


@router.get("/me", response_model=dict)
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("未登录")

    payload = decode_token(auth_header[7:])
    if not payload:
        raise UnauthorizedError("token 无效")

    return make_response(data={
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "role": payload.get("role"),
        "employee_id": payload.get("employee_id"),
        "store_id": payload.get("store_id"),
    }, request=request)


# ==================== 企微 OAuth 免登录 ====================

@router.get("/wework/config")
async def wework_config(request: Request):
    """返回企微 corp_id 和 agent_id，供前端构造 OAuth 跳转 URL。全局配置，无需门店。"""
    from app.config import get_settings
    settings = get_settings()
    if not settings.WECOM_CORP_ID:
        return make_response(data=None, request=request)
    return make_response(data={
        "corp_id": settings.WECOM_CORP_ID,
        "agent_id": settings.WECOM_AGENT_ID,
    }, request=request)


@router.get("/wework/login")
async def wework_login(request: Request, db: AsyncSession = Depends(get_db)):
    """企微 OAuth 回调。从 code 获取用户身份，自动登录。"""
    from fastapi.responses import RedirectResponse
    from app.config import get_settings

    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url="/login")

    # 企微配置从环境变量读取（全局）
    settings = get_settings()
    if not settings.WECOM_CORP_ID:
        return RedirectResponse(url="/login?error=config")

    # 用 code 换取企微 userid（store_id 传空，_get_store_config 会走环境变量）
    from app.services.wework import get_userid_by_code
    try:
        wework_userid = await get_userid_by_code(db, None, code)
    except Exception as e:
        logger.warning(f"企微 OAuth 获取 userid 失败: {e}")
        return RedirectResponse(url="/login?error=oauth_fail")

    if not wework_userid:
        return RedirectResponse(url="/login?error=no_user")

    # 根据 wework_userid 查本地员工
    emp_result = await db.execute(
        select(Employee).where(Employee.wework_userid == wework_userid)
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        return RedirectResponse(url=f"/login?error=not_found&uid={wework_userid}")

    # 查或建用户账号
    user_result = await db.execute(select(User).where(User.employee_id == emp.id))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(
            store_id=emp.store_id,
            employee_id=emp.id,
            username=emp.name,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role=emp.role,
            is_active=True,
        )
        db.add(user)
        await db.flush()
    elif user.role != emp.role:
        # 每次 OAuth 登录时间步角色
        user.role = emp.role
        await db.flush()

    # 签发 JWT
    token_data = {
        "user_id": _to_str(user.id),
        "username": user.username,
        "role": user.role,
        "employee_id": _to_str(emp.id),
        "store_id": _to_str(emp.store_id),
    }
    access_token_str = create_access_token(token_data)
    refresh_token_str = create_refresh_token(token_data)

    await db.commit()

    frontend_url = (
        f"/auth-callback"
        f"?access_token={access_token_str}"
        f"&refresh_token={refresh_token_str}"
        f"&role={user.role}"
    )
    return RedirectResponse(url=frontend_url)
