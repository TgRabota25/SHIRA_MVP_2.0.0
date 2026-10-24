from pathlib import Path
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
