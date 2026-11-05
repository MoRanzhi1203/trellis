# Trellis Windows 环境初始化
# 用法：powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$conda = $null
foreach ($candidate in @('conda', 'E:\anaconda3\Scripts\conda.exe', 'C:\ProgramData\anaconda3\Scripts\conda.exe')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $conda = $cmd.Source; break }
}
if (-not $conda) { throw '未找到 conda，请先安装 Anaconda 或 Miniconda。' }

Write-Host "使用 conda: $conda"
$envs = & $conda env list
if (-not ($envs -match '^\s*trellis\s')) {
    Write-Host '创建 trellis 环境（Python 3.11）…'
    & $conda create -n trellis python=3.11 pip -y
} else {
    Write-Host 'trellis 环境已存在，跳过创建。'
}

Write-Host '安装后端依赖…'
& $conda run -n trellis python -m pip install -e "$root\backend[dev]"

Write-Host '安装前端依赖…'
Push-Location "$root\frontend"
try {
    if (Test-Path 'package-lock.json') { npm ci } else { npm install }
} finally {
    Pop-Location
}

Write-Host '初始化数据库（Alembic upgrade head）…'
& $conda run -n trellis python -m alembic -c "$root\backend\alembic.ini" upgrade head

if ($env:TRELLIS_SKIP_IMPORT -ne '1') {
    Write-Host '导入旧版词库（幂等）…'
    & $conda run -n trellis python "$root\backend\scripts\import_legacy.py"
}

Write-Host '完成。运行 scripts/start.ps1 启动项目。'
