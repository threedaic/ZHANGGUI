# 以管理员权限运行此脚本：安装 WSL2 组件（不含默认发行版）
$logPath = "C:\Users\hello\Documents\trae_projects\crush-zhanggui\wsl-install.log"
"=== 开始 wsl --install --no-distribution ===" | Out-File -FilePath $logPath -Encoding utf8
wsl --install --no-distribution *>&1 | Out-File -FilePath $logPath -Append -Encoding utf8
"=== 退出码: $LASTEXITCODE ===" | Out-File -FilePath $logPath -Append -Encoding utf8
