#!/bin/bash
echo "===== 测试白名单函数 ====="
docker exec crush-zhanggui-api python3 << 'EOF'
from app.middleware.rls import _is_whitelisted, RLS_WHITELIST_EXACT, RLS_WHITELIST_PREFIX
print("EXACT 白名单内容:")
for p in sorted(RLS_WHITELIST_EXACT):
    print(f"  {p}")
print()
print("PREFIX 白名单内容:")
for p in sorted(RLS_WHITELIST_PREFIX):
    print(f"  {p}")
print()
for path in ["/api/v1/ratings", "/api/v1/auth/login", "/api/v1/tasks/my", "/api/v1/wine-storage/h5/abc", "/api/v1/wework/callback/contact"]:
    print(f"_is_whitelisted({path}) = {_is_whitelisted(path)}")
EOF

echo
echo "===== 测试 ratings 路由注册路径 ====="
docker exec crush-zhanggui-api python3 << 'EOF'
from app.api.v1.ratings import router
for r in router.routes:
    print(f"  path={r.path} methods={r.methods}")
EOF

echo
echo "===== 重新测试 ratings 访问（带 -L 跟随重定向） ====="
curl -s -L http://127.0.0.1:8001/api/v1/ratings | head -c 200
echo
echo "===== 不带斜杠的 tasks 创建 ====="
LOGIN=$(curl -s -X POST http://127.0.0.1:8001/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"

echo "创建任务（不带尾部斜杠）:"
curl -s -X POST http://127.0.0.1:8001/api/v1/tasks -H "$AUTH" -H "Content-Type: application/json" -d '{"title":"验证测试_请删除","task_type":"pool","priority":"medium"}'
echo
echo
echo "任务列表:"
curl -s "http://127.0.0.1:8001/api/v1/tasks?page=1&page_size=5" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('总数:', d.get('data',{}).get('total',0), '条数:', len(d.get('data',{}).get('items',[])))" 2>/dev/null
