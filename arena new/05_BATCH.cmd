@echo off
setlocal
cd /d "%~dp0"
"%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe" "%~dp0app\cli.py" %*
exit /b %ERRORLEVEL%
