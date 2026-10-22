import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='2.0.0'
APPID='SHIRA.LabelIndex.MVP.2'
PROFILES={
 'weak':dict(label='Слабый ПК',workers=1,frames=8,ocr_frames=3,width=1280,segment=30,timeout=240,ocr_timeout=12),
 'balanced':dict(label='Обычный ПК',workers=2,frames=16,ocr_frames=5,width=1600,segment=60,timeout=600,ocr_timeout=15),
 'powerful':dict(label='Мощный CPU',workers=4,frames=24,ocr_frames=8,width=1920,segment=60,timeout=900,ocr_timeout=20)}
DEFAULT_PATTERNS=[
 {'name':'Ozon ii','market':'Ozon','regex':r'(?<![A-Za-z0-9])[iI]{2}\s*\d{11}(?!\d)'},
 {'name':'Ozon старый','market':'Ozon','regex':r'(?<!\d)\d{6}\s*\d{4}\s*[-–—]\s*\d{4}\s*[-–—]\s*\d{1,3}(?!\d)'},
 {'name':'Этикетка 8-4-1','market':'Шаблон 8-4-1','regex':r'(?<!\d)\d{8}\s*[-–—]\s*\d{4}\s*[-–—]\s*\d(?!\d)'},
 {'name':'Яндекс груз','market':'Yandex Market','regex':r'(?<!\d)\d{11}\s*[-–—]\s*\d{1,3}(?!\d)'},
 {'name':'Ozon ii мягкий','market':'Ozon','regex':r'(?<![A-Za-z0-9])[iI]{2}\s*\d{10,12}(?!\d)'},
 {'name':'Ozon пробелы мягкий','market':'Ozon','regex':r'(?<!\d)\d{6}\s+\d{4}\s+\d{4}\s+\d{1,3}(?!\d)'},
 {'name':'Яндекс груз мягкий','market':'Yandex Market','regex':r'(?<!\d)\d{10,12}\s*[-–—]\s*\d{1,3}(?!\d)'},
 {'name':'Яндекс заказ QR мягкий','market':'Yandex Market','source':'qr','regex':r'^\d{11}$'}]
def data_dir():
 p=Path(os.environ.get('SHIRA_DATA_DIR') or (Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'SHIRA_MVP'))
 p.mkdir(parents=True,exist_ok=True);return p

def atomic_json(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.tmp-',suffix='.json',dir=path.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)

def auto_profile():
 import psutil
 ram=psutil.virtual_memory().available/2**30;cores=psutil.cpu_count(logical=False) or 1
 key='powerful' if ram>=12 and cores>=8 else 'balanced' if ram>=5 and cores>=4 else 'weak'
 return key,dict(available_ram_gb=round(ram,1),physical_cores=cores)

def settings():
 value=dict(profile='balanced',mode='short',long_step=1.0,long_ocr_every=3,language='rus+eng',recursive=True,patterns=DEFAULT_PATTERNS,
  short_frames=0,short_ocr_frames=0,short_qr_ocr=True,short_qr_ocr_max=12,short_enhanced=True)
 try:
  loaded=json.loads((data_dir()/'settings-v2.json').read_text('utf-8'))
  if isinstance(loaded,dict):value.update(loaded)
 except (ValueError,OSError):pass
 if value.get('profile') not in PROFILES:value['profile']='weak'
 if value.get('mode') not in ('short','long'):value['mode']='short'
 try:value['long_step']=min(60,max(.1,float(value['long_step'])))
 except (ValueError,TypeError):value['long_step']=1.0
 try:value['long_ocr_every']=min(100,max(1,int(value['long_ocr_every'])))
 except (ValueError,TypeError):value['long_ocr_every']=3
 if value.get('language') not in ('rus','eng','rus+eng'):value['language']='rus+eng'
 for key,low,high in (('short_frames',4,120),('short_ocr_frames',1,120)):
  try:n=int(value.get(key,0))
  except (ValueError,TypeError):n=0
  value[key]=0 if n<=0 else min(high,max(low,n))
 try:value['short_qr_ocr_max']=min(60,max(0,int(value.get('short_qr_ocr_max',12))))
 except (ValueError,TypeError):value['short_qr_ocr_max']=12
 value['short_qr_ocr']=bool(value.get('short_qr_ocr',True));value['short_enhanced']=bool(value.get('short_enhanced',True))
 return value

def worker_config(value):
 result=dict(PROFILES[value['profile']]);result.update(value)
 # 0 = взять значение из профиля ПК.
 if value.get('short_frames'):result['frames']=int(value['short_frames'])
 if value.get('short_ocr_frames'):result['ocr_frames']=int(value['short_ocr_frames'])
 result.update(root=str(ROOT),data_dir=str(data_dir()))
 return result

def stamp(seconds):
 seconds=max(0,float(seconds));h=int(seconds//3600);m=int(seconds//60)%60;s=seconds%60
 return f'{h:02d}:{m:02d}:{s:06.3f}'
