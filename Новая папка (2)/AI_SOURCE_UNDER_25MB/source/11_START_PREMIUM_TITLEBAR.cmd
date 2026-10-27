@echo off
setlocal
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe"
if not exist "%PY%" (
 echo [ERROR] SHIRA environment not found.
 pause
 exit /b 1
)
if not exist "app\premium_ui.py" (
 echo [ERROR] Install Premium Tactile first.
 pause
 exit /b 1
)
"%PY%" -u "%~dp0tools\launch_premium_titlebar.py"
if errorlevel 1 pause
