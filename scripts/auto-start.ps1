# Crush掌柜 后端自动启动脚本（开机自启用）
# 此脚本由 Windows 计划任务在用户登录时自动执行，静默运行，无弹窗。
# 日志输出到 backend/auto-start.log 方便排查问题。

$ErrorActionPreference = "Continue"
$LogFile = "C:\Users\hello\Documents\trae_projects\crush-zhanggui\backend\auto-start.log"
$ProjectRoot = "C:\Users\hello\Documents\trae_projects\crush-zhanggui"
$BackendDir = "$ProjectRoot\backend"
$FrontendDir = "$ProjectRoot\frontend"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

Log "========== Auto start triggered =========="

# --- 1. 启动 Docker Desktop（容器会随 Docker 引擎自动恢复）---
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    $dockerProc = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
    if (-not $dockerProc) {
        Log "Starting Docker Desktop..."
        Start-Process $dockerExe
    } else {
        Log "Docker Desktop already running."
    }

    # 等待 Docker 引擎就绪（最多 120 秒）
    $waited = 0
    while ($waited -lt 120) {
        Start-Sleep -Seconds 5
        $waited += 5
        $dockerInfo = & docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log "Docker engine ready (${waited}s)."
            break
        }
    }
    if ($waited -ge 120) {
        Log "ERROR: Docker engine did not start within 120s."
    }
} else {
    Log "WARN: Docker Desktop not found at expected path."
}

# --- 2. 确保 dev 容器在运行 ---
Log "Ensuring dev containers are up..."
Push-Location $ProjectRoot
& docker compose -f docker-compose.dev.yml up -d 2>&1 | Out-File -FilePath $LogFile -Append -Encoding utf8
Pop-Location
Start-Sleep -Seconds 3

# --- 3. 启动后端 uvicorn（如果 8001 端口未占用）---
$backendConn = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($backendConn) {
    Log "Backend already running on port 8001 (PID $($backendConn.OwningProcess))."
} else {
    Log "Starting backend uvicorn..."
    Start-Process -FilePath "C:\Program Files\Python312\python.exe" `
        -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8001" `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden
    Start-Sleep -Seconds 6

    # 健康检查
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 5
        Log "Backend healthy: $($health | ConvertTo-Json -Compress)"
    } catch {
        Log "ERROR: Backend health check failed: $($_.Exception.Message)"
    }
}

# --- 4. 启动前端 vite（如果 5173 端口未占用）---
$frontendConn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontendConn) {
    Log "Frontend already running on port 5173 (PID $($frontendConn.OwningProcess))."
} else {
    Log "Starting frontend vite..."
    $env:Path = "C:\Program Files\nodejs;" + $env:Path
    Start-Process -FilePath "C:\Program Files\nodejs\node.exe" `
        -ArgumentList "node_modules\vite\bin\vite.js","--host","0.0.0.0","--port","5173" `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Log "Frontend started."
}

Log "========== Auto start done =========="
