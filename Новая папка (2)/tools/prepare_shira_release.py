"""Copy a pinned project snapshot; prepare Windows EXE and Inno Setup sources."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='15b89d62099c7bdcc3ad1fb59cec25a1fc30130d'
PREFIX='SHIRA_MVP_2.0.0-main/'
DEST=ROOT/'S H I R A'

def write(path,text):
    p=DEST/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(text.encode('utf-8'))
def replace(path,old,new):
    p=DEST/path;text=p.read_text('utf-8-sig')
    if text.count(old)!=1:raise RuntimeError('Unexpected source: '+path)
    p.write_text(text.replace(old,new,1),encoding='utf-8')
def main():
    if DEST.exists():raise RuntimeError('S H I R A already exists; refusing overwrite')
    names=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',SOURCE,'--',PREFIX],cwd=ROOT).decode().split('\0')
    for name in names:
        if not name:continue
        rel=name[len(PREFIX):];p=Path(rel)
        if '..' in p.parts or '__pycache__' in p.parts:continue
        if '.before-' in p.name or p.suffix in ('.log','.pyc','.db','.sqlite3'):continue
        keep=p.parts[0] in ('docs','licenses','tests') or rel in ('requirements.txt','requirements-windows-lock.txt','README_RU.md','tools/frame_preview.py','tools/doctor.py')
        if p.parts[0]=='app':
            keep=('tesseract' in p.parts or p.name in ('icon.ico','icon.png') or (p.suffix=='.py' and p.name not in ('main_patched.py','studio_ui_patched.py','ui_patch.py') and (not p.name.startswith('premium_') or p.name=='premium_windows.py')))
        if not keep:continue
        data=subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
        if data.startswith(b'version https://git-lfs.github.com/spec/v1'):raise RuntimeError('Unresolved LFS resource: '+name)
        target=DEST/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    replace('app/config.py','ROOT=Path(__file__).resolve().parents[1]',"ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))")
    replace('app/engine.py','from config import data_dir,worker_config','from config import data_dir,worker_config,ROOT')
    replace('app/engine.py','cfg.update(root=str(Path(__file__).resolve().parents[1]),data_dir=str(data_dir()))','cfg.update(root=str(ROOT),data_dir=str(data_dir()))')
    replace('app/main.py',"command=[sys.executable,str(ROOT/'tools/frame_preview.py'),str(video),str(ts),out]","command=([sys.executable,'--frame-preview',str(video),str(ts),out] if getattr(sys,'frozen',False) else [sys.executable,str(ROOT/'launcher.py'),'--frame-preview',str(video),str(ts),out])")
    p=DEST/'app/studio_ui.py';text=p.read_text('utf-8-sig')
    text=text.replace('        w=event.widget\n        if w not in seen:',"        w=event.widget\n        if not hasattr(w,'winfo_exists'):return\n        if w not in seen:")
    p.write_text(text,encoding='utf-8')
    write('launcher.py',LAUNCHER)
    write('tools/build_exe.py',BUILD)
    write('SHIRA.iss',ISS)
    write('requirements-build.txt','PyInstaller>=6.11,<7\n')
    commands={
      '01_INSTALL.cmd':'py -3.12 -c "import struct; assert struct.calcsize(\'P\') == 8"\nif errorlevel 1 goto fail\nif not exist ".venv\\Scripts\\python.exe" py -3.12 -m venv .venv\nif errorlevel 1 goto fail\n".venv\\Scripts\\python.exe" -m pip install -r requirements.txt -r requirements-build.txt',
      '02_START.cmd':'if not exist ".venv\\Scripts\\python.exe" goto fail\n".venv\\Scripts\\python.exe" launcher.py',
      '03_BUILD_EXE.cmd':'if not exist ".venv\\Scripts\\python.exe" goto fail\n".venv\\Scripts\\python.exe" tools\\build_exe.py'}
    for name,body in commands.items():
        text='@echo off\nsetlocal\ncd /d "%~dp0"\n'+body+'\nif errorlevel 1 goto fail\necho [OK]\npause\nexit /b 0\n:fail\necho [ERROR] See the error above.\npause\nexit /b 1\n'
        write(name,text.replace('\n','\r\n'))
    write('README_INSTALL_RU.md',README)
    write('.gitignore','.venv/\nbuild/\ndist/\nbuild_assets/\ninstaller_output/\n__pycache__/\n*.spec\n*.log\n')
    for p in DEST.rglob('*.py'):ast.parse(p.read_text('utf-8-sig'),filename=str(p))
    files={p.relative_to(DEST).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.rglob('*') if p.is_file()}
    write('SOURCE_MANIFEST.json',json.dumps(dict(source_commit=SOURCE,files=files),ensure_ascii=False,indent=2))
    print('Prepared',len(files),'files; Windows runtime tests still required')

LAUNCHER='''from pathlib import Path
import logging,multiprocessing,runpy,sys,traceback
BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
sys.path.insert(0,str(BASE/'app'))
def run():
    if len(sys.argv)>1 and sys.argv[1]=='--frame-preview':
        sys.argv=[str(BASE/'tools/frame_preview.py')]+sys.argv[2:]
        runpy.run_path(str(BASE/'tools/frame_preview.py'),run_name='__main__');return
    from config import data_dir
    folder=data_dir()/'logs';folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=str(folder/'desktop-startup.log'),level=logging.INFO,encoding='utf-8',force=True)
    import main as app
    if '--standard' not in sys.argv:
        import studio_ui,premium_windows
        studio_ui.install(app);premium_windows.install(app)
    import archive_delete
    archive_delete.install(app);app.main()
if __name__=='__main__':
    multiprocessing.freeze_support()
    try:run()
    except Exception:
        text=traceback.format_exc();logging.exception('Startup failed')
        try:
            from config import data_dir
            (data_dir()/'startup-error.txt').write_text(text,encoding='utf-8')
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw();messagebox.showerror('SHIRA',text,parent=root);root.destroy()
        except Exception:print(text,file=sys.stderr)
        sys.exit(1)
'''
BUILD='''from pathlib import Path
import ast,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    if os.name!='nt':raise RuntimeError('Build on Windows x64')
    for p in (ROOT/'app').glob('*.py'):ast.parse(p.read_text('utf-8-sig'),filename=str(p))
    for rel in ['app/tesseract/tesseract.exe','app/tesseract/tessdata/rus.traineddata','app/tesseract/tessdata/eng.traineddata']:
        if not (ROOT/rel).is_file():raise RuntimeError('Missing OCR resource: '+rel)
    from PIL import Image
    assets=ROOT/'build_assets';assets.mkdir(exist_ok=True)
    with Image.open(ROOT/'app/icon.png') as source:
        im=source.convert('RGBA');im.save(assets/'icon.png',format='PNG')
        im.save(assets/'icon.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','SHIRA','--paths',str(ROOT/'app'),'--icon',str(assets/'icon.ico'),'--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build'),'--specpath',str(ROOT)]
    for src,dst in [(assets/'icon.png','app'),(assets/'icon.ico','app'),(ROOT/'app/tesseract','app/tesseract'),(ROOT/'tools/frame_preview.py','tools'),(ROOT/'README_RU.md','.')]:args+=['--add-data',str(src)+';'+dst]
    if (ROOT/'licenses').is_dir():args+=['--add-data',str(ROOT/'licenses')+';licenses']
    for package in ['cv2','numpy','PIL','zxingcpp','psutil','openpyxl']:args+=['--collect-all',package]
    for module in ['main','config','storage','engine','recognition','platform_ui','imageview','legacy_import','windows_job','studio_ui','premium_windows','archive_delete']:args+=['--hidden-import',module]
    args.append(str(ROOT/'launcher.py'));subprocess.run(args,cwd=ROOT,check=True)
    if not (ROOT/'dist/SHIRA/SHIRA.exe').is_file():raise RuntimeError('EXE not created')
    print('Test dist/SHIRA/SHIRA.exe before compiling SHIRA.iss')
if __name__=='__main__':main()
'''
ISS='''#define MyAppName "SHIRA"
#define MyAppVersion "2.0.0"
#if !FileExists(SourcePath + "\\dist\\SHIRA\\SHIRA.exe")
  #error First run 03_BUILD_EXE.cmd and test the EXE
#endif
[Setup]
AppId={{9C212F98-B44C-40E6-BE11-E748B30A9659}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SHIRA
DefaultDirName={localappdata}\\Programs\\SHIRA
DefaultGroupName=SHIRA
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=SHIRA_Setup_2.0.0_x64
SetupIconFile=build_assets\\icon.ico
UninstallDisplayIcon={app}\\SHIRA.exe
CloseApplications=yes
DisableProgramGroupPage=yes
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "dist\\SHIRA\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\\SHIRA"; Filename: "{app}\\SHIRA.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\\SHIRA"; Filename: "{app}\\SHIRA.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\\SHIRA.exe"; Description: "Запустить SHIRA"; Flags: nowait postinstall skipifsilent
'''
README='''# S H I R A — подготовка установщика

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
'''
if __name__=='__main__':main()
