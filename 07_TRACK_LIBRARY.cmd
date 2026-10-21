@echo off
setlocal
cd /d "%~dp0"
call "%LocalAppData%\SHIRA_MVP\venv\Scripts\python.exe" tools\launch.py --library
