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
    Write-Host "5. 启动 MCP 服务（供 Codex 连接，不是给人看的界面）"
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
        "5" {
            Write-Host "MCP 是 stdio 协议服务，由 Codex 通过管道调用。" -ForegroundColor Yellow
            Write-Host "手动启动后窗口会一直静默等待输入，这是正常现象，不是卡死。" -ForegroundColor Yellow
            Write-Host "日常使用不需要手动启动；Codex 会按全局配置自己拉起。" -ForegroundColor Yellow
            Write-Host "按 Ctrl+C 可以退出。" -ForegroundColor DarkYellow
            & .\tools\start-mcp-server.ps1 -ProjectRoot $ProjectRoot
        }
        "0" { break }
        default { Write-Host "无效选择" -ForegroundColor Yellow }
    }
}
