param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONWARNINGS = "ignore"

$checks = @()
function Add-Check($Name, $Pass, $Detail) {
    $script:checks += [pscustomobject]@{ name = $Name; pass = [bool]$Pass; detail = [string]$Detail }
}

function Quote-ProcessArg([string]$Arg) {
    if ($Arg -match '[\s"]') {
        return '"' + ($Arg.Replace('"', '\"')) + '"'
    }
    return $Arg
}

Add-Check "project_root" (Test-Path -LiteralPath $ProjectRoot) $ProjectRoot
if (!(Test-Path -LiteralPath $ProjectRoot)) {
    $result = [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        project_root = $ProjectRoot
        checks = $checks
        pass = $false
    }
    $result | ConvertTo-Json -Depth 5
    exit 2
}

Set-Location -LiteralPath $ProjectRoot
. (Join-Path $ProjectRoot "tools\python-runner.ps1") -ProjectRoot $ProjectRoot

$Python = $null
try {
    $Python = Get-ProjectPython -Root $ProjectRoot
    Add-Check "project_python" $true $Python
} catch {
    Add-Check "project_python" $false $_.Exception.Message
}

function Invoke-Python([string[]]$Arguments) {
    if (!$Python) {
        return [pscustomobject]@{ exit_code = 127; output = "No usable Python was found. Run 换电脑初始化.bat." }
    }

    $Exe = $Python
    $ProcessArgs = $Arguments
    if ($Python -eq "py -3") {
        $Exe = "py"
        $ProcessArgs = @("-3") + $Arguments
    }

    $Psi = [System.Diagnostics.ProcessStartInfo]::new()
    $Psi.FileName = $Exe
    $Psi.Arguments = (($ProcessArgs | ForEach-Object { Quote-ProcessArg $_ }) -join " ")
    $Psi.WorkingDirectory = $ProjectRoot
    $Psi.UseShellExecute = $false
    $Psi.RedirectStandardOutput = $true
    $Psi.RedirectStandardError = $true
    $Psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $Psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    try {
        $Proc = [System.Diagnostics.Process]::Start($Psi)
        $Stdout = $Proc.StandardOutput.ReadToEnd()
        $Stderr = $Proc.StandardError.ReadToEnd()
        $Proc.WaitForExit()
        $Output = (($Stdout, $Stderr) | Where-Object { $_ -and $_.Trim() }) -join "`n"
        return [pscustomobject]@{ exit_code = $Proc.ExitCode; output = $Output.Trim() }
    } catch {
        return [pscustomobject]@{ exit_code = 126; output = $_.Exception.Message }
    }
}

Add-Check "requirements" (Test-Path -LiteralPath (Join-Path $ProjectRoot "requirements.txt")) "requirements.txt"
Add-Check "knowledge_truth_source" (Test-Path -LiteralPath (Join-Path $ProjectRoot "knowledge")) "knowledge/"
Add-Check "mcp_server" (Test-Path -LiteralPath (Join-Path $ProjectRoot "mcp-server\server.py")) "mcp-server/server.py"
Add-Check "hooks" ((Test-Path -LiteralPath (Join-Path $ProjectRoot "hooks\stop_check.ps1")) -and (Test-Path -LiteralPath (Join-Path $ProjectRoot "hooks\precompact_save.ps1"))) "hooks/"
Add-Check "one_click_bat" (Test-Path -LiteralPath (Join-Path $ProjectRoot "一键启动知识库.bat")) "一键启动知识库.bat"
Add-Check "git_repo" (Test-Path -LiteralPath (Join-Path $ProjectRoot ".git")) ".git"
Add-Check "vector_dir" (Test-Path -LiteralPath (Join-Path $ProjectRoot "vector")) "vector/ exists; qdrant_local is optional unless AUTO_KB_ENABLE_QDRANT=1"

$init = Invoke-Python @("-W", "ignore", "-m", "auto_kb.cli", "init")
Add-Check "init" ($init.exit_code -eq 0) $init.output
Add-Check "state_db" (Test-Path -LiteralPath (Join-Path $ProjectRoot "memory\knowledge.db")) "memory/knowledge.db after init"

$status = Invoke-Python @("-W", "ignore", "-m", "auto_kb.cli", "status")
Add-Check "adapter_status" ($status.exit_code -eq 0) $status.output

$currentTask = $null
if ($status.exit_code -eq 0 -and $status.output) {
    try {
        $statusJson = $status.output | ConvertFrom-Json
        $currentTask = $statusJson.current_task
    } catch {}
}

if ($currentTask) {
    $gate = Invoke-Python @("-W", "ignore", "-m", "auto_kb.cli", "gate", "--task", "current")
    Add-Check "current_gate" ($gate.exit_code -eq 0) $gate.output
} else {
    Add-Check "current_gate" $true "No current task; gate check skipped for fresh checkout/runtime idle state."
}

$tests = Invoke-Python @("-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-v")
Add-Check "test_suite" ($tests.exit_code -eq 0) $tests.output

$failed = $checks | Where-Object { -not $_.pass }
$result = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    project_root = $ProjectRoot
    checks = $checks
    pass = ($failed.Count -eq 0)
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot ".auto_kb") | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ProjectRoot ".auto_kb\full-auto-audit.json") -Encoding UTF8
$result | ConvertTo-Json -Depth 6
if ($failed.Count -gt 0) { exit 2 }
exit 0
