# Trellis 数据库备份
# 用法：powershell -ExecutionPolicy Bypass -File scripts/backup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$conda = $null
foreach ($candidate in @('conda', 'E:\anaconda3\Scripts\conda.exe', 'C:\ProgramData\anaconda3\Scripts\conda.exe')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $conda = $cmd.Source; break }
}
if (-not $conda) { throw '未找到 conda。' }

$script = @'
import sqlite3, sys
from datetime import datetime
from pathlib import Path

root = Path(sys.argv[1])
db = root / "data" / "local" / "trellis.db"
backup_dir = root / "data" / "local" / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)
target = backup_dir / f"trellis-{datetime.now():%Y%m%d-%H%M%S}.db"
if target.exists():
    raise SystemExit(f"backup already exists: {target}")
if not db.exists():
    raise SystemExit(f"database not found: {db}")
src = sqlite3.connect(db)
dst = sqlite3.connect(target)
with dst:
    src.backup(dst)
src.close()
dst.close()
print(target)
'@
$temp = Join-Path $env:TEMP 'trellis-backup.py'
Set-Content -Path $temp -Value $script -Encoding UTF8
& $conda run -n trellis python $temp $root
