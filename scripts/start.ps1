# Trellis 本地启动
# 用法：powershell -ExecutionPolicy Bypass -File scripts/start.ps1
#       powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Port 8124

param([int]$Port = 8123)

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

foreach ($candidatePort in @($Port, 5173)) {
    $inUse = Get-NetTCPConnection -LocalPort $candidatePort -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        throw "端口 $candidatePort 已被占用（PID $($inUse.OwningProcess)）。换一个端口：scripts/start.ps1 -Port 8124"
    }
}

Write-Host "启动后端 127.0.0.1:$Port …"
$backend = Start-Process -FilePath $conda `
    -ArgumentList 'run', '-n', 'trellis', 'python', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Port", '--reload' `
    -WorkingDirectory "$root\backend" -PassThru

Write-Host '启动前端 http://127.0.0.1:5173 …'
$frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
    -WorkingDirectory "$root\frontend" -PassThru

Write-Host ''
Write-Host "完整应用: http://127.0.0.1:$Port"
Write-Host "前端开发: http://127.0.0.1:5173"
Write-Host "接口文档: http://127.0.0.1:$Port/docs"
Write-Host "停止：Stop-Process -Id $($backend.Id),$($frontend.Id)"
