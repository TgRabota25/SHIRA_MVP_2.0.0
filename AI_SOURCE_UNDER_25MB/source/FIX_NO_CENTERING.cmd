@echo off
setlocal
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe"
if not exist "%PY%" (
 echo [ERROR] SHIRA environment not found.
 pause
 exit /b 1
)
"%PY%" "%~dp0tools\fix_no_centering.py"
pause
