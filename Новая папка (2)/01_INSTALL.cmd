@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
if %ERRORLEVEL% neq 0 (
    echo Установка завершена с ошибкой (см. %LOCALAPPDATA%\SHIRA_MVP\installation-v2.log).
    pause
    exit /b 1
)
echo Установка завершена успешно (SUCCESS).
pause
exit /b 0
