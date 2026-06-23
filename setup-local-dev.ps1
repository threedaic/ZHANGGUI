# 本地开发环境一键启动脚本
# 重启电脑后，双击运行此脚本即可
# 用法: PowerShell -ExecutionPolicy Bypass -File setup-local-dev.ps1

$ErrorActionPreference = "Stop"
Write-Host "=== Crush掌柜 本地开发环境启动 ===" -ForegroundColor Cyan

# 1. 启动Docker Desktop
Write-Host "`n[1/5] 启动Docker Desktop..." -ForegroundColor Yellow
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Start-Process $dockerExe
    Write-Host "  等待Docker引擎启动..."
    $maxWait = 120
    $waited = 0
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 5
        $waited += 5
        $dockerStatus = & docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker引擎已启动 (等待${waited}秒)" -ForegroundColor Green
            break
        }
        Write-Host "  等待中... ${waited}s"
    }
    if ($waited -ge $maxWait) {
        Write-Host "  Docker启动超时，请手动启动Docker Desktop后重新运行此脚本" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  未找到Docker Desktop，请先安装" -ForegroundColor Red
    exit 1
}

# 2. 启动PostgreSQL+Redis+Backend容器
Write-Host "`n[2/5] 启动PostgreSQL+Redis+Backend容器..." -ForegroundColor Yellow
Set-Location "C:\Users\hello\Documents\trae_projects\crush-zhanggui"
docker compose -f docker-compose.dev.yml up -d
Start-Sleep -Seconds 10
Write-Host "  容器状态:" -ForegroundColor Green
docker compose -f docker-compose.dev.yml ps

# 3. 导入数据库备份
Write-Host "`n[3/5] 导入数据库备份..." -ForegroundColor Yellow
$backupFile = "C:\Users\hello\Documents\trae_projects\crush-zhanggui\backend\crush_backup.sql"
if (Test-Path $backupFile) {
    # 检查是否已导入（有表则跳过）
    $tableCount = docker exec crush-dev-pg psql -U crush -d crush_zhanggui -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>&1
    if ([int]$tableCount.Trim() -gt 0) {
        Write-Host "  数据库已有数据($($tableCount.Trim())张表)，跳过导入" -ForegroundColor Green
    } else {
        Write-Host "  导入备份文件..."
        Get-Content $backupFile | docker exec -i crush-dev-pg psql -U crush -d crush_zhanggui 2>&1 | Select-Object -Last 5
        Write-Host "  导入完成" -ForegroundColor Green
    }
} else {
    Write-Host "  备份文件不存在: $backupFile" -ForegroundColor Red
}

# 4. 检查后端容器健康
Write-Host "`n[4/5] 检查后端容器..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$apiStatus = docker inspect --format='{{.State.Health.Status}}' crush-dev-api 2>&1
if ($apiStatus -eq "healthy") {
    Write-Host "  后端容器健康 (crush-dev-api)" -ForegroundColor Green
} else {
    Write-Host "  后端容器状态: $apiStatus，等待启动..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}
$health = try { (Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 5) } catch { $null }
if ($health) {
    Write-Host "  后端健康检查通过" -ForegroundColor Green
} else {
    Write-Host "  后端启动失败，请运行: docker logs crush-dev-api" -ForegroundColor Red
}

# 5. 重启前端
Write-Host "`n[5/5] 重启前端..." -ForegroundColor Yellow
$conns = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}
$env:Path = "C:\Program Files\nodejs;" + $env:Path
Start-Process -FilePath "npx" -ArgumentList "vite","--port","5173" -WorkingDirectory "C:\Users\hello\Documents\trae_projects\crush-zhanggui\frontend" -WindowStyle Minimized
Start-Sleep -Seconds 5
Write-Host "  前端已启动" -ForegroundColor Green

Write-Host "`n=== 启动完成 ===" -ForegroundColor Cyan
Write-Host "前端: http://localhost:5173/" -ForegroundColor White
Write-Host "后端: http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host "数据库: localhost:5432 (crush/crush_dev_pwd)" -ForegroundColor White
Write-Host "Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "所有服务运行在 Docker 容器中，崩溃会自动重启" -ForegroundColor Green
Write-Host "查看后端日志: docker logs -f crush-dev-api" -ForegroundColor Gray
Write-Host "重启后端: docker compose -f docker-compose.dev.yml restart backend" -ForegroundColor Gray
Write-Host ""
Write-Host "按任意键打开浏览器预览..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:5173/"
