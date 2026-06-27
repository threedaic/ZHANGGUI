#!/bin/bash
# OA 任务系统 API 全量测试
# 测试目标：验证任务系统的核心功能、边缘功能、异常处理
set -u

BASE="http://127.0.0.1:8001"
PASS=0
FAIL=0
SKIP=0
RESULTS_FILE="/tmp/test_results.txt"
> $RESULTS_FILE

# 颜色输出（简化版，不带emoji）
log_pass() { echo "[PASS] $1"; PASS=$((PASS+1)); echo "[PASS] $1" >> $RESULTS_FILE; }
log_fail() { echo "[FAIL] $1 -> $2"; FAIL=$((FAIL+1)); echo "[FAIL] $1 -> $2" >> $RESULTS_FILE; }
log_skip() { echo "[SKIP] $1 -> $2"; SKIP=$((SKIP+1)); echo "[SKIP] $1 -> $2" >> $RESULTS_FILE; }
log_info() { echo "       $1"; }

echo "=========================================="
echo "  OA 任务系统 API 全量测试"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo

# ========== 0. 健康检查 ==========
echo "--- 0. 健康检查 ---"
resp=$(curl -s $BASE/health)
if echo "$resp" | grep -q '"healthy"'; then
  log_pass "0.1 /health 接口"
else
  log_fail "0.1 /health 接口" "$resp"
  echo "健康检查失败，终止测试"
  exit 1
fi
echo

# ========== 1. 登录 ==========
echo "--- 1. 登录 ---"
# 使用 admin 账号
login_resp=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}')
token=$(echo "$login_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token',''))" 2>/dev/null)

if [ -n "$token" ] && [ "$token" != "" ]; then
  log_pass "1.1 admin 登录获取 token"
else
  log_fail "1.1 admin 登录" "$login_resp"
  echo "登录失败，终止测试"
  exit 1
fi

AUTH="Authorization: Bearer $token"
log_info "Token: ${token:0:30}..."
echo

# ========== 2. 任务列表查询（核心：GET /tasks） ==========
echo "--- 2. 任务列表 ---"

# 2.1 基本列表
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks")
code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
if [ "$code" = "200" ]; then
  log_pass "2.1 任务列表 200"
else
  log_fail "2.1 任务列表" "HTTP $code: $body"
fi

# 2.2 带过滤参数
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks?status=pending&priority=high&page=1&page_size=10")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "2.2 任务列表（带过滤）"
else
  log_fail "2.2 任务列表（带过滤）" "HTTP $code"
fi

# 2.3 分页参数边界
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks?page=1&page_size=100")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "2.3 分页参数（最大page_size）"
else
  log_fail "2.3 分页参数" "HTTP $code"
fi

# 2.4 异常：page=0 应被拒绝（ge=1）
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks?page=0")
code=$(echo "$resp" | tail -1)
if [ "$code" = "422" ]; then
  log_pass "2.4 异常 page=0 拒绝（422）"
else
  log_fail "2.4 异常 page=0" "期望422 实际$code"
fi

# 2.5 异常：page_size > 100 应被拒绝
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks?page_size=200")
code=$(echo "$resp" | tail -1)
if [ "$code" = "422" ]; then
  log_pass "2.5 异常 page_size=200 拒绝（422）"
else
  log_fail "2.5 异常 page_size=200" "期望422 实际$code"
fi

# 2.6 未登录访问应 401
resp=$(curl -s -w "\n%{http_code}" "$BASE/api/v1/tasks")
code=$(echo "$resp" | tail -1)
if [ "$code" = "401" ]; then
  log_pass "2.6 未登录访问 401"
else
  log_fail "2.6 未登录访问" "期望401 实际$code"
fi
echo

# ========== 3. 我的任务 ==========
echo "--- 3. 我的任务 GET /tasks/my ---"
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/my")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "3.1 我的任务"
else
  log_fail "3.1 我的任务" "HTTP $code"
fi

resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/my?status=pending")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "3.2 我的任务（带status）"
else
  log_fail "3.2 我的任务" "HTTP $code"
fi
echo

# ========== 4. 认领池 ==========
echo "--- 4. 认领池 GET /tasks/pool ---"
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/pool")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "4.1 认领池列表"
else
  log_fail "4.1 认领池列表" "HTTP $code"
fi
echo

# ========== 5. 创建任务 ==========
echo "--- 5. 创建任务 POST /tasks ---"

# 5.1 正常指派任务
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"API测试-指派任务","description":"测试用","task_type":"direct","priority":"high","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4"}')
code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
if [ "$code" = "200" ]; then
  DIRECT_TASK_ID=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
  log_pass "5.1 创建指派任务 (id=${DIRECT_TASK_ID:0:8})"
else
  log_fail "5.1 创建指派任务" "HTTP $code: $body"
  DIRECT_TASK_ID=""
fi

# 5.2 正常认领池任务
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"API测试-认领池任务","description":"待认领","task_type":"pool","priority":"medium"}')
code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
if [ "$code" = "200" ]; then
  POOL_TASK_ID=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
  log_pass "5.2 创建认领池任务 (id=${POOL_TASK_ID:0:8})"
else
  log_fail "5.2 创建认领池任务" "HTTP $code: $body"
  POOL_TASK_ID=""
fi

# 5.3 异常：标题为空
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"","task_type":"direct","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4"}')
code=$(echo "$resp" | tail -1)
if [ "$code" = "400" ] || [ "$code" = "422" ]; then
  log_pass "5.3 异常 标题为空（$code）"
else
  log_fail "5.3 异常 标题为空" "期望400/422 实际$code"
fi

# 5.4 异常：标题过长（>200）
LONG_TITLE=$(python3 -c "print('x'*201)")
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d "{\"title\":\"$LONG_TITLE\",\"task_type\":\"direct\",\"assignee_id\":\"1e616c5d-00eb-4072-82fa-af3ca571fbe4\"}")
code=$(echo "$resp" | tail -1)
if [ "$code" = "400" ] || [ "$code" = "422" ]; then
  log_pass "5.4 异常 标题过长201字（$code）"
else
  log_fail "5.4 异常 标题过长" "期望400/422 实际$code"
fi

# 5.5 异常：指派任务未指定 assignee_id
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"测试无执行人","task_type":"direct"}')
code=$(echo "$resp" | tail -1)
if [ "$code" = "400" ] || [ "$code" = "422" ]; then
  log_pass "5.5 异常 指派无assignee_id（$code）"
else
  log_fail "5.5 异常 指派无assignee_id" "期望400/422 实际$code"
fi

# 5.6 异常：无效 task_type
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"无效类型","task_type":"invalid","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4"}')
code=$(echo "$resp" | tail -1)
if [ "$code" = "400" ] || [ "$code" = "422" ]; then
  log_pass "5.6 异常 无效task_type（$code）"
else
  log_fail "5.6 异常 无效task_type" "期望400/422 实际$code"
fi
echo

# ========== 6. 任务详情 ==========
echo "--- 6. 任务详情 ---"
if [ -n "$DIRECT_TASK_ID" ]; then
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/$DIRECT_TASK_ID")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "6.1 任务详情"
  else
    log_fail "6.1 任务详情" "HTTP $code"
  fi
fi

# 6.2 异常：不存在的任务
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/00000000-0000-0000-0000-000000000000")
code=$(echo "$resp" | tail -1)
if [ "$code" = "404" ]; then
  log_pass "6.2 异常 任务不存在 404"
else
  log_fail "6.2 异常 任务不存在" "期望404 实际$code"
fi

# 6.3 异常：无效UUID
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/not-a-uuid")
code=$(echo "$resp" | tail -1)
if [ "$code" = "404" ] || [ "$code" = "422" ] || [ "$code" = "400" ]; then
  log_pass "6.3 异常 无效UUID（$code）"
else
  log_fail "6.3 异常 无效UUID" "期望400/404/422 实际$code"
fi
echo

# ========== 7. 状态更新 ==========
echo "--- 7. 状态更新 ---"
if [ -n "$DIRECT_TASK_ID" ]; then
  # 7.1 pending -> in_progress
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/$DIRECT_TASK_ID/status" \
    -d '{"status":"in_progress"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "7.1 pending -> in_progress"
  else
    log_fail "7.1 状态更新 in_progress" "HTTP $code"
  fi

  # 7.2 in_progress -> completed
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/$DIRECT_TASK_ID/status" \
    -d '{"status":"completed"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "7.2 in_progress -> completed"
  else
    log_fail "7.2 状态更新 completed" "HTTP $code"
  fi

  # 7.3 异常：已完成任务不能再改
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/$DIRECT_TASK_ID/status" \
    -d '{"status":"in_progress"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "409" ]; then
    log_pass "7.3 异常 已完成不可改 409"
  else
    log_fail "7.3 异常 已完成不可改" "期望409 实际$code"
  fi
fi

# 7.4 异常：无效状态值
if [ -n "$POOL_TASK_ID" ]; then
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/$POOL_TASK_ID/status" \
    -d '{"status":"invalid_status"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "400" ] || [ "$code" = "422" ]; then
    log_pass "7.4 异常 无效状态值（$code）"
  else
    log_fail "7.4 异常 无效状态值" "期望400/422 实际$code"
  fi
fi
echo

# ========== 8. 认领 ==========
echo "--- 8. 认领任务 ---"
if [ -n "$POOL_TASK_ID" ]; then
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X POST "$BASE/api/v1/tasks/$POOL_TASK_ID/claim")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "8.1 认领池任务"
  else
    log_fail "8.1 认领池任务" "HTTP $code"
  fi

  # 8.2 异常：重复认领
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X POST "$BASE/api/v1/tasks/$POOL_TASK_ID/claim")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "409" ]; then
    log_pass "8.2 异常 重复认领 409"
  else
    log_fail "8.2 异常 重复认领" "期望409 实际$code"
  fi
fi

# 8.3 异常：认领非pool类型
if [ -n "$DIRECT_TASK_ID" ]; then
  # 重新创建一个direct任务测试
  resp=$(curl -s -H "$AUTH" -H "Content-Type: application/json" \
    -X POST "$BASE/api/v1/tasks" \
    -d '{"title":"测试认领非pool","task_type":"direct","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4"}')
  tid=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
  if [ -n "$tid" ]; then
    resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -X POST "$BASE/api/v1/tasks/$tid/claim")
    code=$(echo "$resp" | tail -1)
    if [ "$code" = "409" ]; then
      log_pass "8.3 异常 认领direct任务 409"
    else
      log_fail "8.3 异常 认领direct任务" "期望409 实际$code"
    fi
  fi
fi
echo

# ========== 9. 编辑任务 ==========
echo "--- 9. 编辑任务 PATCH /tasks/{id} ---"
if [ -n "$DIRECT_TASK_ID" ]; then
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/$DIRECT_TASK_ID" \
    -d '{"title":"API测试-修改后标题","priority":"low"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "9.1 编辑任务"
  else
    log_fail "9.1 编辑任务" "HTTP $code"
  fi
fi
echo

# ========== 10. 附件 ==========
echo "--- 10. 附件管理 ---"
# 创建测试图片
TEST_IMG="/tmp/test.jpg"
python3 -c "
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img.save('$TEST_IMG')
" 2>/dev/null || printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9#441' > $TEST_IMG

# 创建一个新任务做附件测试
resp=$(curl -s -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks" \
  -d '{"title":"附件测试任务","task_type":"direct","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4"}')
ATT_TASK_ID=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)

if [ -n "$ATT_TASK_ID" ] && [ -f "$TEST_IMG" ]; then
  # 10.1 上传附件
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X POST "$BASE/api/v1/tasks/$ATT_TASK_ID/attachments" \
    -F "file=@$TEST_IMG" -F "stage=progress")
  code=$(echo "$resp" | tail -1)
  body=$(echo "$resp" | sed '$d')
  if [ "$code" = "200" ]; then
    ATT_ID=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
    log_pass "10.1 上传附件 (att_id=${ATT_ID:0:8})"
  else
    log_fail "10.1 上传附件" "HTTP $code: $body"
    ATT_ID=""
  fi

  # 10.2 获取附件列表
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/$ATT_TASK_ID/attachments")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "10.2 获取附件列表"
  else
    log_fail "10.2 获取附件列表" "HTTP $code"
  fi

  # 10.3 删除附件
  if [ -n "$ATT_ID" ]; then
    resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
      -X DELETE "$BASE/api/v1/tasks/$ATT_TASK_ID/attachments/$ATT_ID")
    code=$(echo "$resp" | tail -1)
    if [ "$code" = "200" ]; then
      log_pass "10.3 删除附件"
    else
      log_fail "10.3 删除附件" "HTTP $code"
    fi
  fi

  # 10.4 异常：上传非图片
  echo "fake text" > /tmp/test.txt
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X POST "$BASE/api/v1/tasks/$ATT_TASK_ID/attachments" \
    -F "file=@/tmp/test.txt" -F "stage=progress")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "400" ] || [ "$code" = "422" ]; then
    log_pass "10.4 异常 上传非图片（$code）"
  else
    log_fail "10.4 异常 上传非图片" "期望400/422 实际$code"
  fi
fi
echo

# ========== 11. 周期模板 ==========
echo "--- 11. 周期模板 ---"

# 11.1 创建模板
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks/templates" \
  -d '{"title":"每日清洁检查","description":"每日例行","priority":"medium","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4","due_time":"10:00","recurrence_type":"daily","recurrence_rule":{}}')
code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
if [ "$code" = "200" ]; then
  TPL_ID=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
  log_pass "11.1 创建模板 (id=${TPL_ID:0:8})"
else
  log_fail "11.1 创建模板" "HTTP $code: $body"
  TPL_ID=""
fi

# 11.2 模板列表
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" "$BASE/api/v1/tasks/templates")
code=$(echo "$resp" | tail -1)
if [ "$code" = "200" ]; then
  log_pass "11.2 模板列表"
else
  log_fail "11.2 模板列表" "HTTP $code"
fi

# 11.3 编辑模板
if [ -n "$TPL_ID" ]; then
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
    -X PATCH "$BASE/api/v1/tasks/templates/$TPL_ID" \
    -d '{"title":"每日清洁检查-修改","priority":"high"}')
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "11.3 编辑模板"
  else
    log_fail "11.3 编辑模板" "HTTP $code"
  fi

  # 11.4 切换启用状态
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X PATCH "$BASE/api/v1/tasks/templates/$TPL_ID/toggle")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "11.4 启用/停用模板"
  else
    log_fail "11.4 启用/停用模板" "HTTP $code"
  fi

  # 11.5 删除模板
  resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" \
    -X DELETE "$BASE/api/v1/tasks/templates/$TPL_ID")
  code=$(echo "$resp" | tail -1)
  if [ "$code" = "200" ]; then
    log_pass "11.5 删除模板"
  else
    log_fail "11.5 删除模板" "HTTP $code"
  fi
fi

# 11.6 异常：无效 recurrence_type
resp=$(curl -s -w "\n%{http_code}" -H "$AUTH" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/tasks/templates" \
  -d '{"title":"测试","assignee_id":"1e616c5d-00eb-4072-82fa-af3ca571fbe4","recurrence_type":"hourly"}')
code=$(echo "$resp" | tail -1)
if [ "$code" = "400" ] || [ "$code" = "422" ]; then
  log_pass "11.6 异常 无效recurrence_type（$code）"
else
  log_fail "11.6 异常 无效recurrence_type" "期望400/422 实际$code"
fi
echo

# ========== 12. 权限测试 ==========
echo "--- 12. 权限测试（用 staff 账号） ---"
# 注意：当前admin是system_admin，应该有权限
# 测试无权限用户能否创建任务（这需要staff账号，这里跳过）
log_skip "12.1 staff账号创建任务权限" "需要staff账号密码"
echo

# ========== 清理测试数据 ==========
echo "--- 13. 清理测试数据 ---"
for tid in "$DIRECT_TASK_ID" "$POOL_TASK_ID" "$ATT_TASK_ID"; do
  if [ -n "$tid" ]; then
    curl -s -H "$AUTH" -H "Content-Type: application/json" \
      -X PATCH "$BASE/api/v1/tasks/$tid/status" \
      -d '{"status":"cancelled"}' > /dev/null
    log_info "已取消任务 ${tid:0:8}"
  fi
done
echo

# ========== 总结 ==========
echo "=========================================="
echo "  测试总结"
echo "=========================================="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo "  TOTAL: $((PASS+FAIL+SKIP))"
echo "=========================================="
echo
echo "详细结果已保存到: $RESULTS_FILE"
