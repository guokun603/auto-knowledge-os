param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AliasRoot = "",
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex")
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $ProjectRoot)) {
    throw "找不到中央知识库目录：$ProjectRoot。请确认目录存在，或用 -ProjectRoot 传入真实目录。"
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null

if (!$AliasRoot) {
    # Default alias inside Codex home — no admin privileges needed.
    # The old default (drive-root junction like G:\AI_KB) required elevation.
    $AliasRoot = Join-Path $CodexHome "AI_KB"
}

function Ensure-AliasRoot([string]$Path, [string]$Target) {
    if (Test-Path -LiteralPath $Path) {
        $Item = Get-Item -LiteralPath $Path -Force
        if (-not (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq [IO.FileAttributes]::ReparsePoint)) {
            throw "$Path 已存在但不是目录联接。为避免覆盖用户数据，请手动处理后重试。"
        }
        return $Path
    }
    New-Item -ItemType Junction -Path $Path -Target $Target | Out-Null
    return $Path
}

try {
    $AliasRoot = Ensure-AliasRoot -Path $AliasRoot -Target $ProjectRoot
} catch {
    $PreferredError = $_.Exception.Message
    $FallbackAlias = Join-Path $CodexHome "AI_KB"
    try {
        $AliasRoot = Ensure-AliasRoot -Path $FallbackAlias -Target $ProjectRoot
        Write-Host "盘根目录别名创建失败，已改用 CodexHome 别名：$AliasRoot" -ForegroundColor Yellow
        Write-Host "原始错误：$PreferredError" -ForegroundColor DarkYellow
    } catch {
        Write-Host "无法创建 ASCII 目录联接，暂时直接使用真实目录：$ProjectRoot" -ForegroundColor Yellow
        Write-Host "原始错误：$PreferredError" -ForegroundColor DarkYellow
        Write-Host "兜底错误：$($_.Exception.Message)" -ForegroundColor DarkYellow
        $AliasRoot = $ProjectRoot
    }
}

$AgentsPath = Join-Path $CodexHome "AGENTS.md"
$StartMarker = "<!-- AUTO_KB_GLOBAL_START -->"
$EndMarker = "<!-- AUTO_KB_GLOBAL_END -->"
$AgentsBlock = @"
$StartMarker
# Global Central Knowledge Base Rules

These are the user's personal default rules for Codex on this computer. They apply across folders unless the user explicitly says otherwise. System/developer instructions and the user's latest explicit request still take priority.

## Central Knowledge Base

- ``$AliasRoot`` is an ASCII junction alias that points to ``$ProjectRoot``; automation may use the alias to avoid Windows subprocess encoding problems, while the real data remains under ``$ProjectRoot``.
- The central knowledge base root is ``$ProjectRoot``.
- When a Codex task starts in any folder, first check whether ``$ProjectRoot`` exists.
- If it exists, treat ``$ProjectRoot\knowledge`` as the durable source of truth for user preferences, lessons, runbooks, decisions, and reusable project knowledge.
- Also read and follow ``$ProjectRoot\AGENTS.md`` for the knowledge-closure workflow when the task is substantial.
- If the ``central_auto_kb`` MCP server is available, use it for knowledge search, task creation, preflight, gate checks, and publishing durable conclusions.
- If the MCP server is unavailable, fall back to direct files and scripts under ``$ProjectRoot`` instead of ignoring the knowledge base.

## User Operating Preference

- The user wants full automation, not a downgraded manual version.
- The user does not want to remember commands or repeat setup steps.
- When the user asks for a system, workflow, or automation, proactively audit missing dependencies, cross-computer behavior, startup behavior, data location, recovery, and one-click operation.
- Do not leave durable lessons only in the chat. Any stable conclusion, user preference, recurring pitfall, or reusable process learned during the conversation should be written to the relevant Markdown file under ``$ProjectRoot\knowledge``.
- Do not create a separate knowledge base outside ``$ProjectRoot`` unless the user explicitly requests it.

## Cross-Project Behavior

- If working in another project folder, obey that project's local ``AGENTS.md`` for repo-specific code style and commands, while still using the central knowledge base for the user's personal memory and reusable decisions.
- If ``$ProjectRoot`` is missing, tell the user that the mobile drive is not mounted or the drive letter changed, then continue with the best available local context.
$EndMarker
"@

$ExistingAgents = ""
if (Test-Path -LiteralPath $AgentsPath) {
    $ExistingAgents = Get-Content -LiteralPath $AgentsPath -Raw -Encoding UTF8
}

$MarkerPattern = "(?s)$([regex]::Escape($StartMarker)).*?$([regex]::Escape($EndMarker))"
if ($ExistingAgents -match $MarkerPattern) {
    $MergedAgents = [regex]::Replace($ExistingAgents, $MarkerPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $AgentsBlock }, 1)
} elseif ($ExistingAgents.Trim()) {
    $BackupPath = Join-Path $CodexHome ("AGENTS.md.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Copy-Item -LiteralPath $AgentsPath -Destination $BackupPath -Force
    Write-Host "已备份原全局 AGENTS.md：$BackupPath" -ForegroundColor Yellow
    $MergedAgents = $ExistingAgents.TrimEnd() + "`r`n`r`n" + $AgentsBlock
} else {
    $MergedAgents = $AgentsBlock
}
Set-Content -LiteralPath $AgentsPath -Value $MergedAgents -Encoding UTF8

$ConfigPath = Join-Path $CodexHome "config.toml"
if (Test-Path -LiteralPath $ConfigPath) {
    $Lines = Get-Content -LiteralPath $ConfigPath -Encoding UTF8
} else {
    $Lines = @("[mcp_servers]")
}

$Out = New-Object System.Collections.Generic.List[string]
$Skip = $false
foreach ($Line in $Lines) {
    if ($Line -match '^\[mcp_servers\.central_auto_kb(\.env)?\]$') {
        $Skip = $true
        continue
    }
    if ($Skip -and $Line -match '^\[') {
        $Skip = $false
    }
    if (-not $Skip) { $Out.Add($Line) }
}

$VenvPython = Join-Path $AliasRoot ".venv\Scripts\python.exe"
$VenvWorks = $false
if (Test-Path -LiteralPath $VenvPython) {
    & $VenvPython --version *> $null
    $VenvWorks = ($LASTEXITCODE -eq 0)
}
$McpCommand = if ($VenvWorks) { $VenvPython } else { "python" }

$Block = @(
    '',
    '[mcp_servers.central_auto_kb]',
    "command = '$McpCommand'",
    "args = ['-m', 'auto_kb.mcp_server']",
    'startup_timeout_sec = 120',
    '',
    '[mcp_servers.central_auto_kb.env]',
    "AUTO_KB_ROOT = '$AliasRoot'",
    "PYTHONPATH = '$AliasRoot'",
    "PYTHONIOENCODING = 'utf-8'"
)
$Out.AddRange([string[]]$Block)
Set-Content -LiteralPath $ConfigPath -Value $Out -Encoding UTF8

Write-Host "Codex 全局知识库自动链接已安装。" -ForegroundColor Green
Write-Host "真实数据：$ProjectRoot" -ForegroundColor Green
Write-Host "自动化别名：$AliasRoot" -ForegroundColor Green

