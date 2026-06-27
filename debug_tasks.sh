#!/bin/bash
BASE="http://127.0.0.1:8001/api/v1"
LOGIN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"

echo "===== 创建任务完整响应 ====="
curl -sv -X POST $BASE/tasks/ -H "$AUTH" -H "Content-Type: application/json" -d '{"title":"验证测试_请删除","task_type":"pool","priority":"medium"}' 2>&1 | tail -30

echo
echo "===== 任务列表完整响应 ====="
curl -s "$BASE/tasks/?page=1&page_size=5" -H "$AUTH"
echo

echo
echo "===== ratings 完整响应 ====="
curl -sv "$BASE/ratings" 2>&1 | tail -15

echo
echo "===== 检查后端日志最近 20 行 ====="
docker logs crush-zhanggui-api --tail 20 2>&1
