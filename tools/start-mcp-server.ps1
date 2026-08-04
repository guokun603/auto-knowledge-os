param(
    [string]$ProjectRoot = "G:\AI 架构"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:AUTO_KB_ROOT = $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot
if ($Python -eq "py -3") { py -3 -m auto_kb.mcp_server } else { & $Python -m auto_kb.mcp_server }
