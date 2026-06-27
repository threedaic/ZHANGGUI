"""验证 system_admin 登录总部后能否跨店访问北京店数据"""
import asyncio
import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.store import Store
from app.utils.security import create_access_token


async def main():
    async with AsyncSessionLocal() as session:
        # 用 system_admin 角色 + 总部 store_id 模拟登录后状态
        result = await session.execute(select(Store).where(Store.store_code == "HQ-001").limit(1))
        hq_store = result.scalar_one_or_none()
        result = await session.execute(select(User).where(User.role == "system_admin").limit(1))
        user = result.scalar_one_or_none()
        token = create_access_token({
            "user_id": str(user.id),
            "role": user.role,
            "store_id": str(hq_store.id),
            "employee_id": str(user.employee_id) if user.employee_id else None,
        })
        print(f"USER: {user.username} ROLE: {user.role} STORE: {hq_store.name} ({hq_store.id})")

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=10) as client:
        # 1. 总部 store_id 直接调用 → 业务层 WHERE store_id='总部'，应该返回 0 条
        r = await client.get("/api/v1/tasks/employees", headers={"Authorization": f"Bearer {token}"})
        print(f"[HQ context] STATUS={r.status_code}  COUNT={len(r.json().get('data', []))}")

        # 2. 切换到北京三里屯店后再调用
        r2 = await client.post(
            "/api/v1/auth/switch-store",
            json={"store_id": "0b3aefc9-dd57-4490-a628-b23914e01585"},
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"[switch-store] STATUS={r2.status_code}")
        if r2.status_code == 200:
            new_token = r2.json().get("data", {}).get("access_token")
            if new_token:
                r3 = await client.get(
                    "/api/v1/tasks/employees",
                    headers={"Authorization": f"Bearer {new_token}"},
                )
                print(f"[BJ context] STATUS={r3.status_code}  COUNT={len(r3.json().get('data', []))}")


if __name__ == "__main__":
    asyncio.run(main())
