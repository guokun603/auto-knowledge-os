param(
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

Write-Host "== 自动化知识库体检 ==" -ForegroundColor Cyan
Invoke-Python @("-m", "auto_kb.cli", "status") | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== 单元测试 ==" -ForegroundColor Cyan
$env:PYTHONDONTWRITEBYTECODE = "1"
Invoke-Python @("-m", "unittest", "discover", "-s", "tests", "-v") | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== 当前任务门禁 ==" -ForegroundColor Cyan
Invoke-Python @("-m", "auto_kb.cli", "gate", "--task", "current") | Out-Null
exit $LASTEXITCODE
