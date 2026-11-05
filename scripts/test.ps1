# Trellis 测试
# 用法：powershell -ExecutionPolicy Bypass -File scripts/test.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$conda = $null
foreach ($candidate in @('conda', 'E:\anaconda3\Scripts\conda.exe', 'C:\ProgramData\anaconda3\Scripts\conda.exe')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $conda = $cmd.Source; break }
}
if (-not $conda) { throw '未找到 conda。' }

Push-Location "$root\backend"
try {
    & $conda run -n trellis python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw '后端测试失败。' }
} finally {
    Pop-Location
}

Push-Location "$root\frontend"
try {
    npm test -- --run 2>$null
} finally {
    Pop-Location
}

Write-Host '测试完成。'
