@echo off
setlocal
cd /d "%~dp0"
"%LOCALAPPDATA%\SHIRA_MVP\venv\Scripts\python.exe" -m unittest discover -s tests -v
pause
