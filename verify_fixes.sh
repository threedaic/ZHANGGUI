#!/bin/bash
echo "===== 1. 健康检查 ====="
curl -s http://127.0.0.1:8001/health
echo

echo "===== 2. 查询账号 ====="
docker exec crush-zhanggui-db psql -U crush_app -d crush_zhanggui -t -c "SELECT username, role FROM sys_users WHERE role IN ('admin','boss','system_admin') LIMIT 10;"

echo "===== 3. 重置 admin 密码为 admin123 ====="
docker exec crush-zhanggui-api python -c "
from app.utils.security import hash_password
from app.database import AsyncSessionLocal
from sqlalchemy import text
import asyncio
async def reset():
    async with AsyncSessionLocal() as s:
        h = hash_password('admin123')
        await s.execute(text(\"UPDATE sys_users SET password_hash=:h, must_change_password=false WHERE username='admin'\"), {'h': h})
        await s.execute(text(\"UPDATE sys_users SET password_hash=:h, must_change_password=false WHERE username='boss'\"), {'h': h})
        await s.commit()
        print('密码已重置')
asyncio.run(reset())
"

echo "===== 4. 登录测试 ====="
LOGIN=$(curl -s -X POST http://127.0.0.1:8001/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
echo "登录响应: $LOGIN" | head -c 300
TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null)
echo
echo "TOKEN长度: ${#TOKEN}"

if [ -z "$TOKEN" ]; then
  echo "登录仍失败，终止"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"
BASE="http://127.0.0.1:8001/api/v1"

echo
echo "===== 5. 任务系统：创建任务（验证 commit） ====="
CREATE=$(curl -s -X POST $BASE/tasks/ -H "$AUTH" -H "Content-Type: application/json" -d '{"title":"验证测试_请删除","task_type":"pool","priority":"medium"}')
echo "创建: $CREATE" | head -c 300
TASK_ID=$(echo $CREATE | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('id',''))" 2>/dev/null)
echo
echo "任务ID: $TASK_ID"

echo
echo "===== 6. 任务列表（验证持久化+批量查询） ====="
curl -s "$BASE/tasks/?page=1&page_size=5" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('总数:', d.get('data',{}).get('total',0), '条数:', len(d.get('data',{}).get('items',[])))" 2>/dev/null

echo
echo "===== 7. 我的任务 ====="
curl -s "$BASE/tasks/my?page=1&page_size=5" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('我的任务:', d.get('data',{}).get('total',0))" 2>/dev/null

echo
echo "===== 8. 认领池 ====="
curl -s "$BASE/tasks/pool?page=1&page_size=5" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('认领池:', d.get('data',{}).get('total',0))" 2>/dev/null

echo
echo "===== 9. 模板列表 ====="
curl -s "$BASE/tasks/templates" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('模板数:', len(d.get('data',[])))" 2>/dev/null

echo
echo "===== 10. RLS 白名单：未登录访问受保护接口 ====="
curl -s "$BASE/tasks/my" | python3 -c "import sys,json; d=json.load(sys.stdin); print('未登录访问:', d.get('code'), d.get('message'))" 2>/dev/null

echo
echo "===== 11. 公开接口（ratings）应可访问 ====="
curl -s "$BASE/ratings" -o /dev/null -w "HTTP状态: %{http_code}\n"

echo
echo "===== 12. 验证完成 ====="
