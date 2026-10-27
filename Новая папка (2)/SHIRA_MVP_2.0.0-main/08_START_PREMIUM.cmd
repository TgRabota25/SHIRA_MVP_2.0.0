@echo off
setlocal
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe"
if not exist "%PY%" (
 echo [ERROR] Run 01_INSTALL.cmd first.
 pause
 exit /b 1
)
if not exist "app\main.py" (
 echo [ERROR] Extract into the SHIRA project root.
 pause
 exit /b 1
)
"%PY%" -u "%~dp0tools\launch_premium.py" %*
if errorlevel 1 pause
