#!/bin/bash
BASE="http://127.0.0.1:8001/api/v1"
LOGIN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"

echo "===== 1. 任务列表（验证持久化） ====="
curl -s "$BASE/tasks?page=1&page_size=10" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
items = d.get('data',{}).get('items',[])
total = d.get('data',{}).get('total',0)
print(f'总数: {total}, 当前页条数: {len(items)}')
for i in items[:5]:
    print(f'  - {i.get(\"title\")} [{i.get(\"status_label\")}] 附件数:{i.get(\"attachments_count\")}')
"

echo
echo "===== 2. 认领池（应有刚创建的 pool 任务） ====="
curl -s "$BASE/tasks/pool?page=1&page_size=10" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
items = d.get('data',{}).get('items',[])
print(f'认领池总数: {d.get(\"data\",{}).get(\"total\",0)}')
for i in items[:3]:
    print(f'  - {i.get(\"title\")} [{i.get(\"status_label\")}]')
"

echo
echo "===== 3. 我的任务 ====="
curl -s "$BASE/tasks/my?page=1&page_size=5" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'我的任务: {d.get(\"data\",{}).get(\"total\",0)}')
"

echo
echo "===== 4. 模板列表 ====="
curl -s "$BASE/tasks/templates" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'模板数: {len(d.get(\"data\",[]))}')
"

echo
echo "===== 5. 员工列表 ====="
curl -s "$BASE/tasks/employees" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
emps = d.get('data',[])
print(f'员工数: {len(emps)}')
for e in emps[:3]:
    print(f'  - {e.get(\"name\")} ({e.get(\"role_label\")})')
"

echo
echo "===== 6. 清理测试任务 ====="
# 找到测试任务并取消
TEST_ID=$(curl -s "$BASE/tasks?page=1&page_size=50" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for i in d.get('data',{}).get('items',[]):
    if '验证测试' in i.get('title',''):
        print(i.get('id'))
        break
" 2>/dev/null)
if [ -n "$TEST_ID" ]; then
  curl -s -X PATCH "$BASE/tasks/$TEST_ID/status" -H "$AUTH" -H "Content-Type: application/json" -d '{"status":"cancelled"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('清理结果:', d.get('message'))" 2>/dev/null
else
  echo "未找到测试任务"
fi

echo
echo "===== 7. 验证店长不能访问 payroll monthly（权限收紧） ====="
# 用 admin 登录（system_admin），尝试访问 payroll/monthly 应该被拒（不在 boss/accountant）
curl -s "$BASE/payroll/monthly?period=2026-06" -H "$AUTH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'admin 访问 payroll/monthly: code={d.get(\"code\")} msg={d.get(\"message\")}')
" 2>/dev/null

echo
echo "===== 验证完成 ====="
