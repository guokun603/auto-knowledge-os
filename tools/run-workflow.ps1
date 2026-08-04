param(
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$Goal,
    [string]$Conclusion = "",
    [string]$ProjectRoot = "G:\AI 架构"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot

function Invoke-Python([string[]]$Arguments) {
    if ($Python -eq "py -3") { & py -3 @Arguments } else { & $Python @Arguments }
    return $LASTEXITCODE
}

if ($Conclusion -and $Conclusion.Trim()) {
    Invoke-Python @("-m", "auto_kb.cli", "workflow", "--title", $Title, "--goal", $Goal, "--conclusion", $Conclusion) | Out-Null
} else {
    Invoke-Python @("-m", "auto_kb.cli", "workflow", "--title", $Title, "--goal", $Goal) | Out-Null
}
exit $LASTEXITCODE

