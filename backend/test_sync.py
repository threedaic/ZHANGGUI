import asyncio
from app.database import AsyncSessionLocal
from app.services.wework import fetch_checkin_data

async def main():
    async with AsyncSessionLocal() as session:
        result = await fetch_checkin_data(session, 1, "2026-06-16")
        print("synced=" + str(result.get("synced", 0)))
        print("errors=" + str(result.get("errors", [])))
        for rec in result.get("records", []):
            print("  " + str(rec))
        await session.commit()

asyncio.run(main())
