#!/bin/bash
echo "===== 1. 服务器代码版本 ====="
cd /opt/crush-zhanggui 2>/dev/null || { echo "目录不存在"; exit 1; }
git log --oneline -10 2>&1
echo
echo "===== 2. 当前分支和状态 ====="
git branch --show-current 2>&1
git status --short 2>&1 | head -30
echo
echo "===== 3. 后端 Python 文件统计 ====="
find backend/app -name "*.py" -type f | wc -l
echo
echo "===== 4. 后端目录树（一级） ====="
ls backend/app/
echo
echo "===== 5. API 路由文件 ====="
ls backend/app/api/v1/ | head -40
echo
echo "===== 6. 关键文件存在性核查 ====="
for f in backend/app/main.py backend/app/api/v1/tasks.py backend/app/repositories/task.py backend/app/models/task.py backend/app/api/v1/wework_callback.py; do
  if [ -f "$f" ]; then
    echo "[OK] $f ($(wc -l < $f) 行)"
  else
    echo "[MISSING] $f"
  fi
done
echo
echo "===== 7. 数据库迁移文件 ====="
ls backend/alembic/versions/*.py 2>&1 | head -20
echo
echo "===== 8. .env 文件位置（不显示内容） ====="
ls -la .env backend/.env 2>&1 | awk '{print $NF, $5}'
echo
echo "===== 9. Docker 容器状态 ====="
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10
echo
echo "===== 10. 后端容器最近 20 行日志 ====="
docker logs crush-zhanggui-api --tail 20 2>&1
