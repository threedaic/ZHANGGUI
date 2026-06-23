"""初始化排班测试数据：添加员工 + 班次配置"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://crush:crush_dev_pwd@localhost:5432/crush_zhanggui"


async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 1. 检查现有员工数量
        result = await conn.execute(text("SELECT COUNT(*) FROM employees WHERE status='active'"))
        count = result.fetchone()[0]
        print(f"当前在职员工数: {count}")

        # 2. 添加测试员工（如果不足）
        if count < 5:
            employees = [
                ("SM001", "张店长", "13800000002", "store_manager", True, False, False),
                ("ST001", "小李", "13800000003", "staff", False, False, False),
                ("ST002", "小王", "13800000004", "staff", False, False, False),
                ("ST003", "小陈", "13800000005", "staff", False, False, False),
                ("ST004", "小刘", "13800000006", "staff", False, False, False),
                ("ST005", "小赵", "13800000007", "staff", False, False, False),
                ("ST006", "小周", "13800000008", "staff", False, False, False),
                ("ST007", "小吴", "13800000009", "staff", False, False, False),
            ]
            for code, name, phone, role, is1, is2, is3 in employees:
                # 检查是否已存在
                exists = await conn.execute(
                    text("SELECT id FROM employees WHERE employee_code=:code"),
                    {"code": code},
                )
                if not exists.fetchone():
                    await conn.execute(
                        text(
                            "INSERT INTO employees "
                            "(store_id, employee_code, name, phone, role, base_salary, "
                            "hire_date, status, is_first_manager, is_second_manager, is_third_manager) "
                            "VALUES (1, :code, :name, :phone, :role, 5000, CURRENT_DATE, "
                            "'active', :is1, :is2, :is3)"
                        ),
                        {"code": code, "name": name, "phone": phone, "role": role,
                         "is1": is1, "is2": is2, "is3": is3},
                    )
                    print(f"  添加员工: {name} ({role})")
                else:
                    print(f"  已存在: {name}")

        # 3. 添加班次配置
        result = await conn.execute(text("SELECT COUNT(*) FROM shift_configs WHERE store_id=1"))
        shift_count = result.fetchone()[0]
        print(f"\n当前班次配置数: {shift_count}")

        if shift_count == 0:
            shifts = [
                ("day", "白班", "10:00", "18:00", False, "#FB0079", 1),
                ("night", "晚班", "18:00", "02:00", True, "#FB0079", 2),
            ]
            for code, name, start, end, overnight, color, order in shifts:
                await conn.execute(
                    text(
                        "INSERT INTO shift_configs "
                        "(store_id, shift_code, shift_name, start_time, end_time, "
                        "is_overnight, color, sort_order, is_active) "
                        "VALUES (1, :code, :name, :start, :end, :overnight, :color, :order, true)"
                    ),
                    {"code": code, "name": name, "start": start, "end": end,
                     "overnight": overnight, "color": color, "order": order},
                )
                print(f"  添加班次: {name} ({code}) {start}-{end}")

        # 4. 验证
        result = await conn.execute(
            text("SELECT name, role FROM employees WHERE status='active' AND store_id=1 ORDER BY role, name")
        )
        print("\n所有在职员工:")
        for row in result.fetchall():
            print(f"  - {row[0]} ({row[1]})")

        result = await conn.execute(
            text("SELECT shift_code, shift_name, start_time, end_time FROM shift_configs WHERE store_id=1")
        )
        print("\n班次配置:")
        for row in result.fetchall():
            print(f"  - {row[1]} ({row[0]}): {row[2]}-{row[3]}")

    await engine.dispose()
    print("\n完成!")


if __name__ == "__main__":
    asyncio.run(main())
