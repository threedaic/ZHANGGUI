"""飞鹅标签机打印测试 - 正确的标签格式"""
import asyncio
import sys
sys.path.insert(0, "/app")

async def test():
    import hashlib
    import time
    import httpx
    from app.database import AsyncSessionLocal
    from app.models.sys import Printer
    from sqlalchemy import select, text as sql_text

    async with AsyncSessionLocal() as db:
        await db.execute(sql_text("SET LOCAL app.current_store_id = '00000000-0000-0000-0000-000000000000'"))
        await db.execute(sql_text("SET LOCAL app.current_user_role = 'boss'"))

        result = await db.execute(select(Printer).where(Printer.is_active == True))
        printers = result.scalars().all()

        for p in printers:
            if p.brand != "feie":
                continue

            user = (p.api_user or "").strip()
            ukey = (p.api_secret or "").strip()
            sn = (p.device_sn or "").strip()

            print(f"打印机: {p.name}, SN: {sn}, type: {p.printer_type}")

            async with httpx.AsyncClient(timeout=30) as client:
                # 标签机格式: 必须用 TEXT 标签指定坐标
                # 40mm宽纸: x最大=320, 高30mm: y最大=240
                print("\n=== 标签机正确格式 (40mm) ===")
                stime = str(int(time.time()))
                sig = hashlib.sha1(f"{user}{ukey}{stime}".encode()).hexdigest()

                content = (
                    "<SIZE>40,30</SIZE>"
                    "<DIRECTION>1</DIRECTION>"
                    "<TEXT x='10' y='10' font='12' w='2' h='2'>取酒小票</TEXT>"
                    "<TEXT x='10' y='70' font='12' w='1' h='1'>单号: Q20260626001</TEXT>"
                    "<TEXT x='10' y='100' font='12' w='1' h='1'>客户: 张三</TEXT>"
                    "<TEXT x='10' y='130' font='12' w='1' h='1'>酒品: 茅台飞天53度</TEXT>"
                    "<TEXT x='10' y='160' font='12' w='1' h='1'>数量: 1瓶</TEXT>"
                    "<TEXT x='10' y='190' font='12' w='1' h='1'>存放: A区03柜</TEXT>"
                )

                payload = {
                    "user": user,
                    "stime": stime,
                    "sig": sig,
                    "apiname": "Open_printLabelMsg",
                    "sn": sn,
                    "content": content,
                    "times": 1,
                }
                print(f"content: {content[:100]}...")
                resp = await client.post("http://api.feieyun.cn/Api/Open/", data=payload)
                print(f"返回: {resp.text}")

                await asyncio.sleep(5)

                # 测试2: 简单的标签
                print("\n=== 最简单的标签 ===")
                stime = str(int(time.time()))
                sig = hashlib.sha1(f"{user}{ukey}{stime}".encode()).hexdigest()

                content2 = (
                    "<SIZE>40,30</SIZE>"
                    "<DIRECTION>1</DIRECTION>"
                    "<TEXT x='10' y='10' font='12' w='1' h='1'>Hello</TEXT>"
                )

                payload = {
                    "user": user,
                    "stime": stime,
                    "sig": sig,
                    "apiname": "Open_printLabelMsg",
                    "sn": sn,
                    "content": content2,
                    "times": 1,
                }
                resp = await client.post("http://api.feieyun.cn/Api/Open/", data=payload)
                print(f"返回: {resp.text}")

asyncio.run(test())
