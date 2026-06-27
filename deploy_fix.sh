#!/bin/bash
set -e
echo "===== 1. 上传代码包 ====="
cd /opt/crush-zhanggui

echo "===== 2. 备份当前 app 目录 ====="
cp -r backend/app backend/app.bak.$(date +%s) 2>/dev/null || true

echo "===== 3. 解压新代码 ====="
tar xzf /tmp/backend_fix.tar.gz -C backend/

echo "===== 4. 删除已废弃的 wecom_notify.py ====="
rm -f backend/app/services/wecom_notify.py

echo "===== 5. 同步 docker-compose.prod.yml ====="
cp /tmp/docker-compose.prod.yml /opt/crush-zhanggui/docker-compose.prod.yml

echo "===== 6. 确保 .env 有 POSTGRES_PASSWORD ====="
grep -q POSTGRES_PASSWORD /opt/crush-zhanggui/.env || echo "POSTGRES_PASSWORD=UXIe8QzwOLNjE3SWSImGhXbv6z_aCZhu" >> /opt/crush-zhanggui/.env

echo "===== 7. 重建后端镜像 ====="
docker compose -f docker-compose.yml build backend

echo "===== 8. 重启后端容器 ====="
docker compose -f docker-compose.yml up -d backend

echo "===== 9. 等待启动 ====="
sleep 8

echo "===== 10. 健康检查 ====="
curl -s http://127.0.0.1:8001/health || echo "健康检查失败"

echo
echo "===== 11. 容器状态 ====="
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10

echo
echo "===== 12. 最近日志 ====="
docker logs crush-zhanggui-api --tail 30 2>&1
