"""修复桌台状态：idle -> active，并清 Redis 看板缓存"""
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text
from app.utils.redis_client import get_redis
from app.models.store import Store
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("UPDATE shared_tables SET status='active' WHERE status='idle'"))
        await s.commit()
        print(f"已更新 {r.rowcount} 个桌台状态: idle -> active")

        store = (await s.execute(select(Store).order_by(Store.created_at).limit(1))).scalar_one()
        redis = await get_redis()
        await redis.delete(f"dashboard:{store.id}")
        print(f"已清 Redis 看板缓存 (dashboard:{store.id})")

asyncio.run(main())
