@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import struct; assert struct.calcsize('P') == 8"
if errorlevel 1 goto fail
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto fail
echo [OK]
pause
exit /b 0
:fail
echo [ERROR] See the error above.
pause
exit /b 1
