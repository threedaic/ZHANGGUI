"""
全局异常定义 + FastAPI 异常处理器
所有响应统一 {code, message, data, request_id} 格式。
"""
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppError(Exception):
    """业务异常基类，所有模块的错误都继承这个。"""
    def __init__(self, code: int, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status


# ---- 通用异常 ----

class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=40400, message=message, http_status=404)

class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或 Token 已过期"):
        super().__init__(code=40100, message=message, http_status=401)

class ForbiddenError(AppError):
    def __init__(self, message: str = "无权访问"):
        super().__init__(code=40300, message=message, http_status=403)

class ValidationError(AppError):
    def __init__(self, message: str = "参数校验失败"):
        super().__init__(code=40001, message=message, http_status=400)

class ConflictError(AppError):
    def __init__(self, message: str = "数据冲突"):
        super().__init__(code=40900, message=message, http_status=409)

class RateLimitError(AppError):
    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(code=42900, message=message, http_status=429)

class ExternalServiceError(AppError):
    """外部服务调用失败（企微/云打印机/SMS 等）。"""
    def __init__(self, message: str = "外部服务调用失败"):
        super().__init__(code=50200, message=message, http_status=502)


# ---- FastAPI 异常处理器 ----

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"[{exc.code}] {exc.message}  path={request.url.path}  request_id={request_id}")
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "request_id": request_id,
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(f"未处理异常: {exc}  path={request.url.path}  request_id={request_id}")

    # 异步推送到企微群（不阻断错误响应）
    try:
        import asyncio
        asyncio.create_task(_push_critical_alert(request, exc, request_id))
    except Exception as e:
        logger.warning(f"create critical alert task failed: {e}")

    return JSONResponse(
        status_code=500,
        content={
            "code": 50000,
            "message": "服务器内部错误",
            "data": None,
            "request_id": request_id,
        },
    )


async def _push_critical_alert(request: Request, exc: Exception, request_id: str | None):
    """推送严重异常到企微群，非阻塞。统一走 NotificationService。"""
    try:
        from app.services.notification_service import NotificationService
        from app.database import AsyncSessionLocal

        store_id = getattr(request.state, "store_id", None) or 1
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-500:]

        async with AsyncSessionLocal() as session:
            notif = NotificationService(session, store_id)
            content = (
                f"> 路径: {request.url.path}\n"
                f"> 类型: {type(exc).__name__}\n"
                f"> 详情: {str(exc)[:200]}\n"
                f"```\n{tb}\n```"
            )
            await notif.send_alert("system_error", "系统异常告警", content)
            await session.commit()
    except Exception:
        logger.exception("推送异常告警失败")
