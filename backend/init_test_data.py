"""初始化测试数据：创建员工记录、关联admin、插入桌位"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://crush:crush_dev_pwd@localhost:5432/crush_zhanggui"


async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 1. 创建 boss 员工记录
        result = await conn.execute(
            text(
                "INSERT INTO employees "
                "(store_id, employee_code, name, phone, role, base_salary, "
                "hire_date, status, is_first_manager, is_second_manager, is_third_manager) "
                "VALUES (1, :code, :name, :phone, :role, 0, CURRENT_DATE, "
                "'active', true, false, false) RETURNING id"
            ),
            {"code": "BOSS001", "name": "老板", "phone": "13800000001", "role": "boss"},
        )
        emp_id = result.fetchone()[0]
        print(f"Created employee id={emp_id}")

        # 2. 关联到 admin 用户
        await conn.execute(
            text("UPDATE users SET employee_id=:eid WHERE username=:u"),
            {"eid": emp_id, "u": "admin"},
        )
        print("Linked admin -> employee")

        # 3. 插入桌位测试数据
        tables = [
            ("大桌", "D1", 10), ("大桌", "D2", 10),
            ("八人桌", "B1", 8), ("八人桌", "B2", 8), ("八人桌", "B3", 8),
            ("六人桌", "S1", 6), ("六人桌", "S2", 6),
            ("六人桌", "S3", 6), ("六人桌", "S4", 6),
            ("四人桌", "F1", 4), ("四人桌", "F2", 4),
            ("四人桌", "F3", 4), ("四人桌", "F4", 4),
            ("四人桌", "F5", 4), ("四人桌", "F6", 4),
            ("卡座", "K1", 4), ("卡座", "K2", 4), ("卡座", "K3", 4),
            ("包间", "P1", 8), ("包间", "P2", 6),
        ]
        for area, no, cap in tables:
            await conn.execute(
                text(
                    "INSERT INTO tables (store_id, area, table_no, capacity, status) "
                    "VALUES (1, :a, :n, :c, 'active')"
                ),
                {"a": area, "n": no, "c": cap},
            )
        print(f"Inserted {len(tables)} tables")

    await engine.dispose()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
