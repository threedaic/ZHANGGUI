from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from app.utils.security import decode_token
from app.utils.audit_logger import set_audit_context


# Paths that do NOT require JWT auth token (M-006 fix)
# All API requests outside this whitelist will return 401 if no valid token.
#
# ⚠️ 维护规则：新增公开端点（无需登录的接口）时，必须同步在此添加路径。
#    忘记添加的后果：端点返回 401（安全失败，不会泄露数据）。
#    路径变更时（如 /wines → /wine-storage）也必须同步更新此处。
RLS_WHITELIST = {
    "/api/v1/auth/login",
    "/api/v1/auth/wework/login",    # WeCom OAuth callback (M-009 fix)
    "/api/v1/auth/wework/config",   # WeCom OAuth config for frontend redirect
    "/api/v1/auth/refresh",         # 使用 body 中的 refresh_token，不依赖 Authorization header
    "/api/v1/ratings",             # Guest QR code rating (POST submit, no auth)
    "/api/v1/wine-storage/h5/",    # Guest wine status + retrieve via H5 (prefix match)
    "/api/v1/wine-storage/guest",  # Guest list wines by phone
    "/api/v1/health",
    "/docs", "/openapi.json",       # Swagger UI（生产环境已通过 docs_url=None 关闭）
    "/redoc",
}


def _is_whitelisted(path: str) -> bool:
    """Check if path is in the RLS whitelist (supports prefix matching)."""
    for pattern in RLS_WHITELIST:
        if path == pattern or (pattern.endswith("/") and path.startswith(pattern)):
            return True
    return False


class RLSMiddleware(BaseHTTPMiddleware):
    """Inject store_id and user info from JWT into request scope.

    This middleware resolves the JWT token and stores user context in
    request.state. The get_db() dependency then reads these values and
    sets PostgreSQL session variables (SET app.store_id / app.user_id / app.role)
    so that Row-Level Security policies can filter rows automatically.

    Dual-layer RLS:
      - PG RLS: enforced at database level via current_setting() — cannot be bypassed
      - App-level: request.state values available for business logic checks

    M-006 fix: Non-whitelisted API requests without valid token are rejected
    with 401 instead of just logging a warning.
    """

    async def dispatch(self, request: Request, call_next):
        # Default: no store context
        request.state.store_id = None
        request.state.user_id = None
        request.state.role = None
        request.state.employee_id = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload and payload.get("type") in ("access", "refresh"):
                # 检查 token 是否已加入黑名单（logout 后失效）
                from app.utils.security import is_token_blacklisted
                if await is_token_blacklisted(token):
                    logger.info(f"RLS: blacklisted token blocked, path={request.url.path}")
                    if request.url.path.startswith("/api/") and not _is_whitelisted(request.url.path):
                        return JSONResponse(
                            status_code=401,
                            content={"code": 40100, "message": "token 已失效，请重新登录", "data": None, "request_id": None},
                        )
                request.state.user_id = payload.get("user_id")
                request.state.role = payload.get("role")
                request.state.store_id = payload.get("store_id")
                request.state.employee_id = payload.get("employee_id")
                logger.debug(f"RLS: user={payload.get('user_id')} store={payload.get('store_id')} role={payload.get('role')} path={request.url.path}")
                # 设置审计日志上下文
                set_audit_context(
                    user_id=payload.get("user_id"),
                    store_id=payload.get("store_id"),
                    request_id=getattr(request.state, "request_id", ""),
                    ip_address=request.client.host if request.client else "",
                    user_agent=request.headers.get("User-Agent", ""),
                )
            else:
                logger.warning(f"RLS: token decode failed or invalid type, path={request.url.path}, token_preview={token[:20]}...")
                # Token present but invalid → reject non-whitelisted API paths
                if request.url.path.startswith("/api/") and not _is_whitelisted(request.url.path):
                    return JSONResponse(
                        status_code=401,
                        content={"code": 40100, "message": "token 无效或已过期", "data": None, "request_id": None},
                    )
        elif request.url.path.startswith("/api/") and not _is_whitelisted(request.url.path):
            # No Authorization header on non-whitelisted API request → reject
            logger.warning(f"RLS: no Authorization header on API request, path={request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"code": 40100, "message": "未登录，请先登录", "data": None, "request_id": None},
            )

        response = await call_next(request)
        return response
