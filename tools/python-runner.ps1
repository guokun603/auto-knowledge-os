param(
    [string]$ProjectRoot = "G:\AI 架构"
)

function Test-ProjectPython {
    param([string]$Command)
    try {
        & $Command --version *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-ProjectPython {
    param([string]$Root)

    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if ((Test-Path -LiteralPath $VenvPython) -and (Test-ProjectPython $VenvPython)) { return $VenvPython }

    try {
        python --version *> $null
        if ($LASTEXITCODE -eq 0) { return "python" }
    } catch {}

    try {
        py -3 --version *> $null
        if ($LASTEXITCODE -eq 0) { return "py -3" }
    } catch {}

    throw "未找到可用 Python。请先运行：换电脑初始化.bat"
}
