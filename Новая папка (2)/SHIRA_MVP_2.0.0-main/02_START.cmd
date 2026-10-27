@echo off
setlocal
cd /d "%~dp0"
if not exist "%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\pythonw.exe" (echo Run 01_INSTALL.cmd first.&pause&exit /b 1)
start "" "%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\pythonw.exe" "%~dp0tools\launch.py"
