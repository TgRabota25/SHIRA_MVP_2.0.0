@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto fail
".venv\Scripts\python.exe" tools\build_exe.py
if errorlevel 1 goto fail
echo [OK]
pause
exit /b 0
:fail
echo [ERROR] See the error above.
pause
exit /b 1
