"""更新员工角色为 SPEC 标准角色"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://crush:crush_dev_pwd@localhost:5432/crush_zhanggui"


async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 将 bartender/chef/waiter 统一改为 staff
        result = await conn.execute(
            text("UPDATE employees SET role='staff' WHERE role IN ('bartender','chef','waiter') RETURNING name, role")
        )
        updated = result.fetchall()
        print(f"已更新 {len(updated)} 个员工角色为 staff:")
        for row in updated:
            print(f"  - {row[0]}")

        # 验证
        result = await conn.execute(
            text("SELECT name, role FROM employees WHERE status='active' ORDER BY role, name")
        )
        print("\n所有在职员工:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}")

    await engine.dispose()
    print("\n完成!")


if __name__ == "__main__":
    asyncio.run(main())
