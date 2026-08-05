param(
    [string]$Task = "current",
    [Parameter(Mandatory=$true)][string]$Goal,
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot
if ($Python -eq "py -3") { py -3 -m auto_kb.cli preflight --task $Task --goal $Goal } else { & $Python -m auto_kb.cli preflight --task $Task --goal $Goal }
exit $LASTEXITCODE
