@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "MENU_PS1="
for %%F in ("%~dp0*.ps1") do set "MENU_PS1=%%~fF"
if not defined MENU_PS1 (
  echo menu script not found
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%MENU_PS1%" -ProjectRoot "%~dp0."
pause
