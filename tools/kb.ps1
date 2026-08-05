param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Args
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot
if ($Python -eq "py -3") { py -3 -m auto_kb.cli @Args } else { & $Python -m auto_kb.cli @Args }
exit $LASTEXITCODE
