#!/bin/bash
# /opt/crush-zhanggui/scripts/backup.sh
# Crush掌柜 数据库自动备份脚本
# - 本地保留 7 天
# - 腾讯云 COS 保留 90 天（异地容灾）

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=crush_zhanggui
DB_USER=crush
DB_CONTAINER=crush-zhanggui-db
BACKUP_DIR=/opt/crush-zhanggui/backups
COS_BUCKET=crush-db-backups

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 开始备份 $DB_NAME ..."

# 全量备份（gzip 压缩）
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz" | cut -f1)
    echo "[OK] 本地备份完成: ${DB_NAME}_${DATE}.sql.gz ($SIZE)"

    # 上传至腾讯云 COS（异地存储）
    if command -v coscmd &> /dev/null; then
        coscmd upload "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz" "$COS_BUCKET/" 2>&1 && \
            echo "[OK] COS 上传完成" || \
            echo "[WARN] COS 上传失败，本地备份仍保留"

        # COS 保留 90 天
        coscmd delete -r "$COS_BUCKET/" --prefix "${DB_NAME}_" --days 90 2>/dev/null || true
    else
        echo "[INFO] coscmd 未安装，跳过 COS 上传。安装: pip install coscmd"
    fi
else
    echo "[FAIL] 备份失败！"
    exit 1
fi

# 本地保留 7 天
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +7 -delete 2>/dev/null || true
echo "[OK] 本地保留 7 天，更早的已清理"

# 记录磁盘使用
echo "磁盘使用: $(df -h /opt | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
