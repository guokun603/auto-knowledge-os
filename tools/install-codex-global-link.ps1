param(
    [string]$ProjectRoot = "G:\AI 架构",
    [string]$AliasRoot = "G:\AI_KB",
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex")
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $ProjectRoot)) {
    throw "找不到中央知识库目录：$ProjectRoot。请确认移动硬盘盘符是 G:。"
}

if (Test-Path -LiteralPath $AliasRoot) {
    $Item = Get-Item -LiteralPath $AliasRoot -Force
    if (-not (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq [IO.FileAttributes]::ReparsePoint)) {
        throw "$AliasRoot 已存在但不是目录联接。为避免覆盖用户数据，请手动处理后重试。"
    }
} else {
    New-Item -ItemType Junction -Path $AliasRoot -Target $ProjectRoot | Out-Null
}

New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null

$AgentsPath = Join-Path $CodexHome "AGENTS.md"
if (Test-Path -LiteralPath $AgentsPath) {
    $ExistingAgents = Get-Content -LiteralPath $AgentsPath -Raw
    if ($ExistingAgents -and $ExistingAgents -notmatch "Global Central Knowledge Base Rules") {
        $BackupPath = Join-Path $CodexHome ("AGENTS.md.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
        Copy-Item -LiteralPath $AgentsPath -Destination $BackupPath -Force
        Write-Host "已备份原全局 AGENTS.md：$BackupPath" -ForegroundColor Yellow
    }
}
$Agents = @"
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
"@
Set-Content -LiteralPath $AgentsPath -Value $Agents -Encoding UTF8

$ConfigPath = Join-Path $CodexHome "config.toml"
if (Test-Path -LiteralPath $ConfigPath) {
    $Lines = Get-Content -LiteralPath $ConfigPath
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
$McpCommand = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { "python" }

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


