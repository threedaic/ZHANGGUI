# Crush 掌柜 - 前端启动脚本
# 用法: 在 frontend 目录下执行 .\start-dev.ps1
# 功能: 清理旧进程 + 启动 vite（固定 5173 端口）

Write-Host "=== Crush 掌柜前端启动 ===" -ForegroundColor Cyan

# 1. 清理所有占用 5173 的进程
Write-Host "[1/3] 清理 5173 端口..." -ForegroundColor Yellow
$conns = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($conn in $conns) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  杀掉 PID $($proc.Id) ($($proc.ProcessName))"
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "  端口空闲"
}

# 2. 清理所有 vite 相关 node 进程（避免僵尸进程）
Write-Host "[2/3] 清理僵尸 vite 进程..." -ForegroundColor Yellow
$nodeProcs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "vite" -or $_.CommandLine -match "npx"
}
foreach ($p in $nodeProcs) {
    Write-Host "  杀掉 PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

# 3. 启动 vite
Write-Host "[3/3] 启动 vite..." -ForegroundColor Yellow
$env:Path = "C:\Program Files\nodejs;" + $env:Path
npx.cmd vite
