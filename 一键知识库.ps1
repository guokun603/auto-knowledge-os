param(
    [string]$ProjectRoot = $PSScriptRoot
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Set-Location -LiteralPath $ProjectRoot

while ($true) {
    Write-Host ""
    Write-Host "自动化知识库菜单" -ForegroundColor Cyan
    Write-Host "1. 换电脑/首次安装自检"
    Write-Host "2. 体检：状态 + 测试 + 当前门禁"
    Write-Host "3. 一键跑完整任务闭环"
    Write-Host "4. 搜索知识库"
    Write-Host "5. 启动 MCP/JSON-RPC 服务"
    Write-Host "0. 退出"
    $choice = Read-Host "请选择"

    switch ($choice) {
        "1" { & .\tools\bootstrap.ps1 -ProjectRoot $ProjectRoot }
        "2" { & .\tools\health-check.ps1 -ProjectRoot $ProjectRoot }
        "3" {
            $title = Read-Host "任务标题"
            $goal = Read-Host "任务目标"
            $conclusion = Read-Host "稳定结论（没有可直接回车）"
            & .\tools\run-workflow.ps1 -ProjectRoot $ProjectRoot -Title $title -Goal $goal -Conclusion $conclusion
        }
        "4" {
            $query = Read-Host "搜索关键词"
            & .\tools\kb.ps1 -ProjectRoot $ProjectRoot search $query
        }
        "5" { & .\tools\start-mcp-server.ps1 -ProjectRoot $ProjectRoot }
        "0" { break }
        default { Write-Host "无效选择" -ForegroundColor Yellow }
    }
}
