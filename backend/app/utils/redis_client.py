from redis.asyncio import Redis
from app.config import get_settings

settings = get_settings()

# Global Redis connection pool.
# NOTE: Using a module-level global is acceptable here because:
# 1. Redis client (redis.asyncio.Redis) is connection-pool-backed and thread-safe
# 2. All FastAPI async handlers share the same event loop
# 3. If migrating to multiple workers, consider app.state.redis via FastAPI dependency
redis: Redis | None = None


async def init_redis():
    global redis
    redis = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis.ping()


async def close_redis():
    global redis
    if redis:
        await redis.close()
        redis = None


async def get_redis() -> Redis:
    if redis is None:
        await init_redis()
    return redis
