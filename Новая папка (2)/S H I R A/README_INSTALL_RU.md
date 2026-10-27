# S H I R A — подготовка установщика

Основа: активные исходники SHIRA_MVP_2.0.0-main из коммита 15b89d6 (123).
Альтернативные patched/Base64-файлы и прежние CMD не включены.

1. Windows x64, Python 3.12 x64 с Python Launcher; Inno Setup 6 с x64compatible.
2. Запустите 01_INSTALL.cmd. Для пакетов Python нужен интернет.
3. Проверьте приложение через 02_START.cmd на копиях видео.
4. Запустите 03_BUILD_EXE.cmd.
5. Проверьте dist/SHIRA/SHIRA.exe: OCR, предпросмотр кадра, экспорт и удаление тестовой копии.
6. Откройте SHIRA.iss в Inno Setup Compiler и нажмите Compile.
7. Результат: installer_output/SHIRA_Setup_2.0.0_x64.exe.

Tesseract, DLL и tessdata должны находиться в app/tesseract. Нужны rus.traineddata и eng.traineddata.
Если ресурсов нет, сборка остановится; автоматическое скачивание сторонних EXE не выполняется.
app/icon.png — источник нормализованных PNG и многослойного ICO при сборке.
Извлечение кадров внутри EXE получает отдельный режим --frame-preview.
Пользовательские данные: SHIRA_DATA_DIR либо LOCALAPPDATA/SHIRA_MVP; прежняя логика сохранена.
Не удаляйте _internal рядом с SHIRA.exe. База и видео не включаются в установщик.
Деинсталлятор не очищает пользовательские базы, бэкапы и видео.
Готовность к компиляции не означает проверку работы на Windows: GUI, OCR, сборку и установку нужно протестировать.
Цифровая подпись не настроена. Источник и SHA256 файлов: SOURCE_MANIFEST.json.
