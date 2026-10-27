@echo off
setlocal
cd /d "%~dp0"
"%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe" "%~dp0tools\doctor.py"
pause
