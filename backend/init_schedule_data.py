"""初始化排班测试数据：添加员工 + 班次配置

SPEC 2.0 迁移：使用新表名 shared_employees / att_shift_configs，UUID 主键。
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://crush:crush_dev_pwd@localhost:5432/crush_zhanggui"


async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 0. 拿到第一家门店的 store_id（UUID）
        store_result = await conn.execute(
            text("SELECT store_id FROM shared_stores ORDER BY created_at LIMIT 1")
        )
        store_row = store_result.fetchone()
        if store_row is None:
            print("错误：shared_stores 表中没有门店，请先启动后端生成种子数据。")
            return
        store_id = store_row[0]
        print(f"使用门店 store_id: {store_id}")

        # 1. 检查现有员工数量
        result = await conn.execute(
            text("SELECT COUNT(*) FROM shared_employees WHERE status='active' AND store_id=:store_id"),
            {"store_id": store_id},
        )
        count = result.fetchone()[0]
        print(f"当前在职员工数: {count}")

        # 2. 添加测试员工（如果不足）
        if count < 5:
            employees = [
                ("SM001", "张店长", "13800000002", "store_manager", True, False, False, "day"),
                ("ST001", "小李", "13800000003", "staff", False, False, False, "day"),
                ("ST002", "小王", "13800000004", "staff", False, False, False, "day"),
                ("ST003", "小陈", "13800000005", "staff", False, False, False, "night"),
                ("ST004", "小刘", "13800000006", "staff", False, False, False, "night"),
                ("ST005", "小赵", "13800000007", "staff", False, False, False, "night"),
                ("ST006", "小周", "13800000008", "staff", False, False, False, "day"),
                ("ST007", "小吴", "13800000009", "staff", False, False, False, "night"),
            ]
            for code, name, phone, role, is1, is2, is3, shift_group in employees:
                # 检查是否已存在
                exists = await conn.execute(
                    text("SELECT employee_id FROM shared_employees WHERE employee_code=:code"),
                    {"code": code},
                )
                if not exists.fetchone():
                    await conn.execute(
                        text(
                            "INSERT INTO shared_employees "
                            "(store_id, employee_code, name, phone, role, base_salary, "
                            "hire_date, status, is_first_manager, is_second_manager, is_third_manager, shift_group) "
                            "VALUES (:store_id, :code, :name, :phone, :role, 5000, CURRENT_DATE, "
                            "'active', :is1, :is2, :is3, :shift_group)"
                        ),
                        {"store_id": store_id, "code": code, "name": name, "phone": phone, "role": role,
                         "is1": is1, "is2": is2, "is3": is3, "shift_group": shift_group},
                    )
                    print(f"  添加员工: {name} ({role})")
                else:
                    print(f"  已存在: {name}")

        # 3. 添加班次配置
        result = await conn.execute(
            text("SELECT COUNT(*) FROM att_shift_configs WHERE store_id=:store_id"),
            {"store_id": store_id},
        )
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
                        "INSERT INTO att_shift_configs "
                        "(store_id, shift_code, shift_name, start_time, end_time, "
                        "is_overnight, color, sort_order, is_active) "
                        "VALUES (:store_id, :code, :name, :start, :end, :overnight, :color, :order, true)"
                    ),
                    {"store_id": store_id, "code": code, "name": name, "start": start, "end": end,
                     "overnight": overnight, "color": color, "order": order},
                )
                print(f"  添加班次: {name} ({code}) {start}-{end}")

        # 4. 验证
        result = await conn.execute(
            text("SELECT name, role FROM shared_employees WHERE status='active' AND store_id=:store_id ORDER BY role, name"),
            {"store_id": store_id},
        )
        print("\n所有在职员工:")
        for row in result.fetchall():
            print(f"  - {row[0]} ({row[1]})")

        result = await conn.execute(
            text("SELECT shift_code, shift_name, start_time, end_time FROM att_shift_configs WHERE store_id=:store_id"),
            {"store_id": store_id},
        )
        print("\n班次配置:")
        for row in result.fetchall():
            print(f"  - {row[1]} ({row[0]}): {row[2]}-{row[3]}")

    await engine.dispose()
    print("\n完成!")


if __name__ == "__main__":
    asyncio.run(main())
