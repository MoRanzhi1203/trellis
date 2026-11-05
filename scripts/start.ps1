# Trellis 本地启动
# 默认由后端同源提供已构建前端（单一端口，避免端口冲突）。
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts/start.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Port 8124
#   powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Dev   （另启 Vite 5173）

param([int]$Port = 8123, [switch]$Dev)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$conda = $null
foreach ($candidate in @('conda', 'E:\anaconda3\Scripts\conda.exe', 'C:\ProgramData\anaconda3\Scripts\conda.exe')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $conda = $cmd.Source; break }
}
if (-not $conda) { throw '未找到 conda。' }

$envs = & $conda env list
if (-not ($envs -match '^\s*trellis\s')) { throw 'trellis 环境不存在，请先运行 scripts/setup.ps1。' }

if (-not (Test-Path "$root\frontend\dist\index.html")) {
    Write-Host '未找到前端构建产物，先执行 npm run build …'
    Push-Location "$root\frontend"
    try { npm run build } finally { Pop-Location }
}

$ports = @($Port)
if ($Dev) { $ports += 5173 }
foreach ($candidatePort in $ports) {
    $inUse = Get-NetTCPConnection -LocalPort $candidatePort -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        throw "端口 $candidatePort 已被占用（PID $($inUse.OwningProcess)）。换一个端口：scripts/start.ps1 -Port 8124"
    }
}

Write-Host "启动后端 127.0.0.1:$Port …"
$backend = Start-Process -FilePath $conda `
    -ArgumentList 'run', '-n', 'trellis', 'python', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Port", '--reload' `
    -WorkingDirectory "$root\backend" -PassThru

if ($Dev) {
    Write-Host '启动前端开发服务器 http://localhost:5173 …'
    $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
        -WorkingDirectory "$root\frontend" -PassThru
}

Write-Host ''
Write-Host "完整应用: http://127.0.0.1:$Port"
Write-Host "接口文档: http://127.0.0.1:$Port/docs"
if ($Dev) { Write-Host '前端开发: http://localhost:5173' }
Write-Host "停止：Stop-Process -Id $($backend.Id)"
