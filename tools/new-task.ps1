param(
    [Parameter(Mandatory=$true)][string]$Title,
    [string]$Goal = "",
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot
if ($Python -eq "py -3") {
    if ($Goal) { py -3 -m auto_kb.cli new-task $Title --goal $Goal } else { py -3 -m auto_kb.cli new-task $Title }
} else {
    if ($Goal) { & $Python -m auto_kb.cli new-task $Title --goal $Goal } else { & $Python -m auto_kb.cli new-task $Title }
}
exit $LASTEXITCODE
