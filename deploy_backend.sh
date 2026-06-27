#!/bin/bash
set -e
cd /opt/crush-zhanggui/backend
echo "=== Backup current app ==="
if [ -d "app" ]; then
  mv app "app.bak.$(date +%s)"
fi
echo "=== Extract new app ==="
mkdir -p app
cd app
unzip -q /tmp/backend_app.zip
echo "=== Verify key files ==="
ls api/v1/tasks.py 2>&1
ls repositories/task.py 2>&1
ls models/task.py 2>&1
echo "=== main.py tasks_router check ==="
grep -n "tasks_router" main.py || echo "NOT FOUND"
echo "=== Rebuild backend container ==="
cd /opt/crush-zhanggui
docker compose -f docker-compose.yml up -d --build backend
echo "=== Wait for healthy ==="
for i in $(seq 1 30); do
  status=$(docker inspect --format='{{.State.Health.Status}}' crush-zhanggui-api 2>/dev/null || echo "starting")
  echo "Attempt $i: $status"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 3
done
echo "=== Test /health ==="
curl -s http://127.0.0.1:8001/health
echo
echo "=== Test /docs exists ==="
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/docs
echo
echo "=== Test /api/v1/tasks (should not 404) ==="
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/api/v1/tasks
echo
