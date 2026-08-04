param(
    [string]$ProjectRoot = "G:\AI 架构"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONWARNINGS = "ignore"
$PSNativeCommandUseErrorActionPreference = $false
Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot
$Python = Get-ProjectPython -Root $ProjectRoot

function Invoke-Python([string[]]$Arguments) {
    $OldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Python -eq "py -3") {
            & py -3 @Arguments 2>$null
        } else {
            & $Python @Arguments 2>$null
        }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $OldPreference
    }
}

$checks = @()
function Add-Check($Name, $Pass, $Detail) {
    $script:checks += [pscustomobject]@{ name = $Name; pass = [bool]$Pass; detail = $Detail }
}

Add-Check "project_root" (Test-Path -LiteralPath $ProjectRoot) $ProjectRoot
Add-Check "project_python" ($Python -ne $null) $Python
Add-Check "requirements" (Test-Path -LiteralPath (Join-Path $ProjectRoot "requirements.txt")) "requirements.txt"
Add-Check "knowledge_truth_source" (Test-Path -LiteralPath (Join-Path $ProjectRoot "knowledge")) "knowledge/"
Add-Check "state_db" (Test-Path -LiteralPath (Join-Path $ProjectRoot "memory\knowledge.db")) "memory/knowledge.db"
Add-Check "qdrant_local" (Test-Path -LiteralPath (Join-Path $ProjectRoot "vector\qdrant_local")) "vector/qdrant_local"
Add-Check "mcp_server" (Test-Path -LiteralPath (Join-Path $ProjectRoot "mcp-server\server.py")) "mcp-server/server.py"
Add-Check "hooks" ((Test-Path -LiteralPath (Join-Path $ProjectRoot "hooks\stop_check.ps1")) -and (Test-Path -LiteralPath (Join-Path $ProjectRoot "hooks\precompact_save.ps1"))) "hooks/"
Add-Check "one_click_bat" (Test-Path -LiteralPath (Join-Path $ProjectRoot "一键启动知识库.bat")) "一键启动知识库.bat"
Add-Check "git_repo" (Test-Path -LiteralPath (Join-Path $ProjectRoot ".git")) ".git"

Invoke-Python @("-W", "ignore", "-m", "auto_kb.cli", "status") *> $null
Add-Check "adapter_status" ($LASTEXITCODE -eq 0) "auto_kb.cli status"

Invoke-Python @("-W", "ignore", "-m", "auto_kb.cli", "gate", "--task", "current") *> $null
Add-Check "current_gate" ($LASTEXITCODE -eq 0) "gate current"

Invoke-Python @("-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-v") *> $null
Add-Check "test_suite" ($LASTEXITCODE -eq 0) "python -m unittest discover -s tests -v"

$failed = $checks | Where-Object { -not $_.pass }
$result = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    project_root = $ProjectRoot
    checks = $checks
    pass = ($failed.Count -eq 0)
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot ".auto_kb") | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ProjectRoot ".auto_kb\full-auto-audit.json") -Encoding UTF8
$result | ConvertTo-Json -Depth 5
if ($failed.Count -gt 0) { exit 2 }
exit 0



