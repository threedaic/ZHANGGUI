"""
请求频率限制中间件
基于 Redis 滑动窗口，多 worker 共享计数。

限流规则:
  - /api/v1/auth/login  → 10次/分钟/IP
  - 其他 /api/v1/* 路由  → 60次/分钟/IP（业务模块可按需覆盖）
"""
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.utils.exceptions import RateLimitError

# 限流配置: path_prefix → (max_requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (10, 60),
}
DEFAULT_LIMIT = (60, 60)  # 60次/分钟

# 白名单路径前缀 — 不做限流（公开 OAuth 接口、健康检查等）
RATE_LIMIT_WHITELIST: list[str] = [
    "/api/v1/auth/wework/config",
    "/api/v1/auth/wework/login",
    "/health",
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # 白名单路径跳过限流
        for prefix in RATE_LIMIT_WHITELIST:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        max_requests, window = _get_limit(request.url.path)
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}:{request.url.path}"

        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()

            # Sliding window via sorted set
            now = time.time()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            count = results[2]
            if count > max_requests:
                raise RateLimitError("请求过于频繁，请稍后再试")

        except RateLimitError:
            raise
        except Exception:
            # Redis unavailable → fall back to allow (fail-open)
            # Don't block all traffic because Redis is down
            logger.warning("Rate limiter: Redis unavailable, skipping limit")

        return await call_next(request)


def _get_limit(path: str) -> tuple[int, int]:
    """Return (max_requests, window_seconds) for the given path."""
    for prefix, limit in RATE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return DEFAULT_LIMIT
