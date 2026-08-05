@echo off
chcp 65001 >nul
for %%I in ("%~dp0..") do set "CENTRAL_KB=%%~fI"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$template = Get-Content -LiteralPath (Join-Path $env:CENTRAL_KB 'portable\AGENTS.central-kb.md') -Raw -Encoding UTF8; $content = $template.Replace('{{CENTRAL_KB_ROOT}}', $env:CENTRAL_KB); Set-Content -LiteralPath (Join-Path (Get-Location) 'AGENTS.md') -Value $content -Encoding UTF8"
if errorlevel 1 (
  echo 安装失败，请确认 PowerShell 可用。
  pause
  exit /b 1
)
echo 已在当前文件夹安装 AGENTS.md，会连接中央知识库：%CENTRAL_KB%
pause
