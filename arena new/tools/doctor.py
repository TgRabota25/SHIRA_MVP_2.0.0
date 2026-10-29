from pathlib import Path
import argparse,importlib,json,os,platform,re,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from config import VERSION,data_dir,settings,worker_config,DEFAULT_PATTERNS

def check():
 result=dict(version=VERSION,python=sys.version,platform=platform.platform(),checks={},errors=[])
 def run(name,fn):
  try:result['checks'][name]=dict(ok=True,result=fn())
  except Exception as exc:result['checks'][name]=dict(ok=False,error=str(exc));result['errors'].append(name)
 def dependencies():
  versions={}
  for name in ['tkinter','cv2','numpy','PIL','psutil','zxingcpp','openpyxl']:
   module=importlib.import_module(name);versions[name]=getattr(module,'__version__','available')
  return versions
 run('dependencies',dependencies)
 def languages():
  from recognition import tesseract_binary
  cfg=worker_config(settings())
  tessdir=ROOT/'app/tesseract/tessdata'
  proc=subprocess.run([tesseract_binary(cfg),'--tessdata-dir','.','--list-langs'],capture_output=True,timeout=20,cwd=str(tessdir),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  text=(proc.stdout+proc.stderr).decode('utf-8','replace')
  if proc.returncode or not all(lang in text.split() for lang in ['eng','rus']):raise RuntimeError(text)
  return text
 run('tesseract_languages',languages)
 def ocr_test():
  import cv2,numpy as np
  from recognition import ocr
  from PIL import Image
  with Image.open(ROOT/'examples/control_text.png') as image:frame=cv2.cvtColor(np.array(image.convert('RGB')),cv2.COLOR_RGB2BGR)
  cfg=worker_config(settings());cfg['language']='eng';cfg['patterns']=DEFAULT_PATTERNS;text=ocr(frame,cfg,7)
  if '81604409-0321-5' not in re.sub(r'\s+','',text):raise RuntimeError('OCR smoke failed: '+text)
  return dict(synthetic_fixture=True,recognized=text.strip())
 run('ocr_smoke',ocr_test)
 def qr_test():
  import cv2,numpy as np,zxingcpp
  frame=cv2.imdecode(np.fromfile(ROOT/'examples/control_qr.png',dtype=np.uint8),cv2.IMREAD_COLOR)
  codes=zxingcpp.read_barcodes(frame)
  if not any(code.text=='ii12345678901' for code in codes):raise RuntimeError('QR test failed')
  return 'ii12345678901'
 run('qr_smoke',qr_test)
 def db():
  from storage import Store
  with tempfile.TemporaryDirectory() as tmp:return Store(Path(tmp)/'test.db').counts()
 run('sqlite',db)
 def write():
  with tempfile.NamedTemporaryFile(dir=data_dir()) as f:f.write(b'OK');f.flush()
  return 'ok'
 run('data_write',write)
 def shell_clipboard():
  if os.name!='nt':return 'not executed: Windows-only'
  import tkinter as tk
  from platform_ui import icon,copy_files
  root=tk.Tk();root.withdraw();icon(root);root.update()
  try:
   from windows_job import assign,close
   child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],creationflags=subprocess.CREATE_NO_WINDOW)
   try:
    handle=assign(child.pid);close(handle);child.wait(timeout=5)
   finally:
    if child.poll() is None:child.kill();child.wait()
   kind=copy_files(root,[ROOT/'examples/control_qr.png'])
   if kind!='files':raise RuntimeError('CF_HDROP unavailable')
  finally:root.destroy()
  return 'Tk icon, Windows Job Object and CF_HDROP file clipboard passed (clipboard replaced by control file)'
 run('windows_shell_smoke',shell_clipboard)

 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args();report=check();text=json.dumps(report,ensure_ascii=False,indent=2)
 Path(args.output or data_dir()/'diagnostics-v2.json').write_text(text,encoding='utf-8');print(text);sys.exit(1 if report['errors'] else 0)
