#!/bin/bash
echo "=== Rebuild backend container ==="
cd /opt/crush-zhanggui
docker compose -f docker-compose.yml up -d --build backend 2>&1 | tail -30
echo "=== Wait for healthy ==="
for i in $(seq 1 30); do
  status=$(docker inspect --format='{{.State.Health.Status}}' crush-zhanggui-api 2>/dev/null || echo "starting")
  echo "Attempt $i: $status"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 3
done
echo "=== Container status ==="
docker ps --filter name=crush-zhanggui-api --format 'table {{.Names}}\t{{.Status}}'
echo "=== Test /health ==="
curl -s http://127.0.0.1:8001/health
echo
echo "=== Test /api/v1/tasks HTTP code (expect 401 not 404) ==="
curl -s -o /tmp/resp.txt -w "HTTP:%{http_code}\n" http://127.0.0.1:8001/api/v1/tasks
cat /tmp/resp.txt
echo
echo "=== Last 30 backend logs ==="
docker logs crush-zhanggui-api --tail 30 2>&1
