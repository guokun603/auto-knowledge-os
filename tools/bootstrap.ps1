param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$UseVenv,
    [switch]$NoAutoInstallPython
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

function Write-Step($Text) {
    Write-Host "`n==> $Text" -ForegroundColor Cyan
}

function Test-Python($Command) {
    try {
        & $Command --version *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    $ProjectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if ((Test-Path -LiteralPath $ProjectPython) -and (Test-Python $ProjectPython)) { return $ProjectPython }

    if (Test-Python "python") { return "python" }

    try {
        py -3 --version *> $null
        if ($LASTEXITCODE -eq 0) { return "py -3" }
    } catch {}

    $Common = @(
        "$env:LocalAppData\Programs\Python\Python313\python.exe",
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe"
    )
    foreach ($Candidate in $Common) {
        if (Test-Path -LiteralPath $Candidate) { return $Candidate }
    }

    return $null
}

function Install-Python {
    if ($NoAutoInstallPython) {
        throw "未找到 Python，且已禁用自动安装。请安装 Python 3.12+ 后重试。"
    }

    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if (!$Winget) {
        throw "未找到 Python，也未找到 winget，无法自动安装。请先安装 Python 3.12+，再运行本脚本。"
    }

    Write-Step "未找到 Python，尝试用 winget 自动安装 Python 3.13"
    winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget 安装 Python 失败。请手动安装 Python 3.12+ 后重试。"
    }

    $Found = Find-Python
    if (!$Found) {
        throw "Python 安装完成，但当前窗口还找不到 python。请重新打开 PowerShell 后再运行本脚本。"
    }
    return $Found
}

function Run-Python($PythonCommand, [string[]]$Arguments) {
    if ($PythonCommand -eq "py -3") {
        & py -3 @Arguments
    } else {
        & $PythonCommand @Arguments
    }
    return $LASTEXITCODE
}

Write-Step "检查项目目录"
if (!(Test-Path -LiteralPath $ProjectRoot)) {
    throw "找不到项目目录：$ProjectRoot。请确认移动硬盘盘符仍然是 G:。"
}
Set-Location -LiteralPath $ProjectRoot

Write-Step "选择 Python"
$Python = Find-Python
if (!$Python) {
    $Python = Install-Python
}

if ($UseVenv) {
    $VenvDir = Join-Path $ProjectRoot ".venv"
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if ((Test-Path -LiteralPath $VenvPython) -and !(Test-Python $VenvPython)) {
        $BrokenPath = Join-Path $ProjectRoot (".venv.broken-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
        Write-Step "发现损坏的项目内虚拟环境，备份后重建 .venv"
        Move-Item -LiteralPath $VenvDir -Destination $BrokenPath
    }
    if (!(Test-Path -LiteralPath $VenvPython)) {
        Write-Step "创建项目内虚拟环境 .venv"
        Run-Python $Python @("-m", "venv", ".venv") | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "创建 .venv 失败。" }
    }
    $Python = $VenvPython
}

Run-Python $Python @("--version") | Out-Null

Write-Step "安装/更新依赖"
Run-Python $Python @("-m", "pip", "install", "-r", "requirements.txt") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "依赖安装失败。" }

Write-Step "初始化知识库"
Run-Python $Python @("-m", "auto_kb.cli", "init") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "知识库初始化失败。" }

Write-Step "检查适配层状态"
Run-Python $Python @("-m", "auto_kb.cli", "status") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "状态检查失败。" }

Write-Step "运行自动化测试"
$env:PYTHONDONTWRITEBYTECODE = "1"
Run-Python $Python @("-m", "unittest", "discover", "-s", "tests", "-v") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "测试失败，请查看上方输出。" }

Write-Step "安装 Codex 全局自动链接"
& (Join-Path $ProjectRoot "tools\install-codex-global-link.ps1") -ProjectRoot $ProjectRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Codex 全局自动链接安装失败。" }

Write-Step "完成"
Write-Host "知识库可用。数据位置：$ProjectRoot" -ForegroundColor Green
Write-Host "Codex 全局自动链接已配置；重新打开 Codex 或新建任务后生效。" -ForegroundColor Green
