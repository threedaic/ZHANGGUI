#!/bin/bash
LOGIN=$(curl -s -X POST http://127.0.0.1:8001/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null)

echo "===== 任务列表完整响应 ====="
curl -s "http://127.0.0.1:8001/api/v1/tasks?page=1&page_size=5" -H "Authorization: Bearer $TOKEN"
echo
echo
echo "===== 后端日志最近 15 行 ====="
docker logs crush-zhanggui-api --tail 15 2>&1
