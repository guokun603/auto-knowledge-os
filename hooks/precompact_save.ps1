param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot
New-Item -ItemType Directory -Force -Path ".auto_kb" | Out-Null
if ($Python -eq "py -3") { py -3 -m auto_kb.cli status | Out-File -FilePath ".auto_kb\precompact-status.json" -Encoding utf8 } else { & $Python -m auto_kb.cli status | Out-File -FilePath ".auto_kb\precompact-status.json" -Encoding utf8 }
exit 0
