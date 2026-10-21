import hashlib,json,math,os,re,shutil,subprocess,tempfile,time
from pathlib import Path
from config import ROOT,DEFAULT_PATTERNS
class FatalInputError(ValueError):pass

IMAGES={'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.webp'}

def native_limits():
 for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
 import cv2
 cv2.setNumThreads(1)

def patterns(cfg):
 out=[]
 configured=cfg.get('patterns',DEFAULT_PATTERNS)
 if not isinstance(configured,list) or not 1<=len(configured)<=30:raise ValueError('Нужны 1–30 шаблонов')
 for p in configured:
  if not isinstance(p,dict):continue
  source=p.get('regex','')
  if len(source)>300:raise ValueError('Шаблон длиннее 300 символов')
  try:out.append((re.compile(source),p.get('market','Шаблон'),p.get('name','Шаблон'),p.get('source','text'))) 
  except re.error as e:raise ValueError('Некорректный шаблон: '+str(e))
 if not out:raise ValueError('Нет шаблонов распознавания')
 return out

def extract(text,cfg,source='text'):
 text=str(text)[:50000];out=[]
 for regex,market,name,required_source in patterns(cfg):
  if required_source=='qr' and source!='qr':continue
  for match in regex.finditer(text):
   number=re.sub(r'\s+','',match.group(0)).replace('—','-').replace('–','-')
   if number.lower().startswith('ii'):number='ii'+number[2:]
   # Яндекс с суффиксом внутри более длинного Ozon-номера не отдельный кандидат.
   if name.startswith('Яндекс груз') and ((match.start()>0 and text[match.start()-1]=='-') or (match.end()<len(text) and text[match.end()]=='-')):continue
   if name=='Ozon пробелы мягкий':
    digits=re.sub(r'\D','',number);number=digits[:10]+'-'+digits[10:14]+'-'+digits[14:]
   value=(number,market,name)
   if not any(existing[0]==number for existing in out):out.append(value)
 return out

def tesseract_binary(cfg):
 override=os.environ.get('SHIRA_TESSERACT')
 if override:return override
 if os.name=='nt':return str(Path(cfg['root'])/'app/tesseract/tesseract.exe')
 found=shutil.which('tesseract')
 if not found:raise RuntimeError('Tesseract не установлен')
 return found

def kill_tree(pid):
 import psutil
 try:process=psutil.Process(pid);children=process.children(recursive=True)
 except psutil.Error:return
 for child in reversed(children):
  try:child.kill()
  except psutil.Error:pass
 try:process.kill()
 except psutil.Error:pass


def ocr(image,cfg,psm=11):
 import cv2
 binary=tesseract_binary(cfg)
 with tempfile.TemporaryDirectory(prefix='shira-ocr-') as tmp:
  src=Path(tmp)/'input.png';ok,buf=cv2.imencode('.png',image)
  if not ok:raise ValueError('Не удалось подготовить изображение для OCR')
  src.write_bytes(buf.tobytes())
  tessdir=Path(cfg['root'])/'app/tesseract/tessdata'
  cmd=[binary,str(src),'stdout','--tessdata-dir','.','-l',cfg.get('language','rus+eng'),'--psm',str(psm)]
  proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(tessdir),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  try:out,err=proc.communicate(timeout=cfg.get('ocr_timeout',15))
  except subprocess.TimeoutExpired:kill_tree(proc.pid);proc.communicate();raise TimeoutError('Превышен срок выполнения OCR')
  if proc.returncode:raise RuntimeError('Tesseract: '+err.decode('utf-8','replace')[:500])
  return out.decode('utf-8','replace')[:50000]

def scaled(frame,width):
 import cv2
 h,w=frame.shape[:2]
 if max(h,w)>width:frame=cv2.resize(frame,(max(1,round(w*width/max(h,w))),max(1,round(h*width/max(h,w)))))
 return frame

def qr_regions(frame):
 import cv2,zxingcpp
 decoded=zxingcpp.read_barcodes(frame,try_rotate=True,try_downscale=True)
 regions=[]
 for code in decoded:
  p=code.position;points=[p.top_left,p.top_right,p.bottom_left,p.bottom_right]
  xs=[int(q.x) for q in points];ys=[int(q.y) for q in points]
  regions.append((min(xs),min(ys),max(xs),max(ys)))
 if not regions:
  try:
   ok,points=cv2.QRCodeDetector().detectMulti(frame)
   if ok:
    for polygon in points:
     xs=polygon[:,0];ys=polygon[:,1];regions.append((int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())))
  except cv2.error:pass
 return decoded,regions

def roi_images(frame,regions):
 import cv2
 h,w=frame.shape[:2];out=[]
 for x1,y1,x2,y2 in regions[:4]:
  size=max(x2-x1,y2-y1,20)
  # Весь блок вокруг QR: текст может быть с любой стороны.
  xa=max(0,x1-3*size);xb=min(w,x2+5*size);ya=max(0,y1-3*size);yb=min(h,y2+5*size)
  crop=frame[ya:yb,xa:xb]
  if crop.size:
   if max(crop.shape[:2])<900:
    crop=cv2.resize(crop,None,fx=min(3,900/max(crop.shape[:2])),fy=min(3,900/max(crop.shape[:2])),interpolation=cv2.INTER_CUBIC)
   out.append(crop)
 out.append(frame)
 return out[:3] if len(out)>3 else out

def recognize_frame(frame,cfg,do_ocr=True):
 import cv2
 codes,regions=qr_regions(frame);findings=[];raw_codes=[]
 for code in codes:
  raw=str(code.text)[:2000];raw_codes.append(raw)
  for number,market,template in extract(raw,cfg,source='qr'):findings.append(dict(number=number,market=market,method='QR / штрихкод',raw=raw,template=template,weak=('мягкий' in template)))
 # Даже если QR содержит подходящий номер, проверяем текст этикетки: QR может быть служебным.
 if do_ocr:
  seen=set()
  for index,image in enumerate(roi_images(frame,regions)):
   region_found=False
   for rotation in (0,90,180,270):
    rotated=image if rotation==0 else cv2.rotate(image,{90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation])
    gray=cv2.cvtColor(rotated,cv2.COLOR_BGR2GRAY) if len(rotated.shape)==3 else rotated
    gray=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
    text=ocr(gray,cfg,11)
    for number,market,template in extract(text,cfg):
     key=(number,index)
     if key in seen:continue
     seen.add(key);region_found=True
     findings.append(dict(number=number,market=market,method='QR-якорный OCR' if regions and index<len(regions) else 'OCR',raw=text[:2000],template=template,weak=('мягкий' in template)))
    if region_found:break
   if region_found:break
 if not findings and raw_codes:findings.append(dict(number='',market='',method='QR без трека',raw='\n'.join(raw_codes)[:2000],template=''))
 return findings

def save_evidence(frame,cfg,key,ts,number):
 import cv2
 folder=Path(cfg['data_dir'])/'evidence-v2'/key;folder.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(folder).free<512*2**20:return ''
 digest=hashlib.sha256(number.encode()).hexdigest()[:10];path=folder/f'{ts:013.3f}-{digest}.jpg'
 ok,data=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,82])
 if not ok:return ''
 temp=path.with_suffix('.tmp');temp.write_bytes(data.tobytes());os.replace(temp,path);return str(path)

def short_result(hits,unknown=False):
 valid=[h for h in hits if h['number']];unique={h['number'] for h in valid}
 if not valid:return dict(state='review' if unknown else 'not_found',number='',market='',detail='QR найден, трек по шаблонам не найден' if unknown else 'Трек не найден')
 best=max(unique,key=lambda n:(len({h['ts'] for h in valid if h['number']==n}),sum(h['method']=='QR / штрихкод' for h in valid if h['number']==n),n))
 selected=[h for h in valid if h['number']==best];first=selected[0]
 reliable=(any(h['method']=='QR / штрихкод' for h in selected) or len({h['ts'] for h in selected})>=2) and any(not h.get('weak') for h in selected)
 state='done' if reliable and len(unique)==1 else 'review'
 detail='Согласованный номер' if state=='done' else 'Несколько номеров: проверьте этикетку' if len(unique)>1 else 'Текст подтверждён только одним кадром'
 return dict(state=state,number=best,market=first['market'],evidence=first.get('evidence',''),detail=detail)

def scan(task,cfg,notify=lambda _:None):
 native_limits()
 import cv2,numpy as np
 from storage import identity
 path=Path(task['path'])
 if not path.is_file():raise FatalInputError('Исходный файл отсутствует или перемещён')
 if identity(path)!=cfg['source_id']:raise FatalInputError('Исходный файл изменился: добавьте его заново')
 start=float(task['cursor']);mode=task['mode'];hits=[];unknown=False;cap=None;gaps=[]
 try:
  if path.suffix.lower() in IMAGES:
   from PIL import Image,ImageOps
   Image.MAX_IMAGE_PIXELS=40_000_000
   with Image.open(path) as im:
    if im.width*im.height>40_000_000:raise ValueError('Изображение превышает 40 МП')
    frame=cv2.cvtColor(np.array(ImageOps.exif_transpose(im).convert('RGB')),cv2.COLOR_RGB2BGR)
   duration=0;times=[0.0];end=0;frames=[frame]
  else:
   cap=cv2.VideoCapture(str(path))
   if not cap.isOpened():raise ValueError('Не удалось открыть видео или кодек')
   fps=float(cap.get(cv2.CAP_PROP_FPS));count=float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
   if not math.isfinite(fps) or not math.isfinite(count) or fps<=0 or count<=0:raise ValueError('Неизвестная длительность видео: требуется корректный индекс файла')
   duration=count/fps
   if mode=='long':
    end=min(duration,start+cfg['segment']);step=cfg['long_step'];first=math.ceil((start-1e-8)/step)*step
    times=[];t=first
    while t<end-1e-6:times.append(max(0,t));t+=step
   else:
    end=duration;times=np.linspace(0,max(0,(count-1)/fps),cfg['frames']).tolist()
   frames=None
  notify(dict(type='metadata',duration=duration,cursor=start))
  if cfg.get('probe_only'):return dict(state='pending',duration=duration,cursor=start,hits=[])
  evidence_cache={};warnings=[];read=0
  ocr_indices={int(round(i)) for i in np.linspace(0,max(0,len(times)-1),min(len(times),cfg['ocr_frames']))}
  for index,ts in enumerate(times):
   if frames is not None:frame=frames[0]
   else:
    cap.set(cv2.CAP_PROP_POS_MSEC,float(ts*1000));ok,frame=cap.read()
    if not ok or frame is None:gaps.append((ts,min(duration,ts+cfg.get('long_step',1)),'Не удалось декодировать кадр'));continue
   read+=1;frame=scaled(frame,cfg['width'])
   do_ocr=(index in ocr_indices) if mode=='short' else (int(round(ts/cfg['long_step']))%cfg['long_ocr_every']==0)
   try:found=recognize_frame(frame,cfg,do_ocr)
   except (TimeoutError,RuntimeError) as exc:
    found=recognize_frame(frame,cfg,False);warnings.append(str(exc));gaps.append((ts,min(duration,ts+cfg.get('long_step',1)),str(exc)))
   for h in found:
    if not h['number']:unknown=True;continue
    h.update(ts=round(ts,3),state='review' if 'OCR' in h['method'] or h.get('weak') else 'done')
    if h['number'] not in evidence_cache:evidence_cache[h['number']]=save_evidence(frame,cfg,task['id'],ts,h['number'])
    h['evidence']=evidence_cache[h['number']];hits.append(h)
   notify(dict(type='progress',cursor=ts,duration=duration))
  if not read and times:raise ValueError('Ни один кадр интервала не прочитан')
  if mode=='short':
   result=short_result(hits,unknown)
   if gaps:result.update(state='review' if hits else 'error',detail=result['detail']+'; есть пропуски декодирования / OCR')
  else:
   result=dict(state='done' if end>=duration-1e-6 else 'pending',detail='Индексация: '+str(len(hits))+' наблюдений за интервал')
  result.update(hits=hits,cursor=end,duration=duration,gaps=gaps)
  return result
 finally:
  if cap is not None:cap.release()
