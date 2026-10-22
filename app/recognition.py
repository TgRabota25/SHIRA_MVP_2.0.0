import hashlib,json,math,os,re,shutil,subprocess,tempfile,time
from pathlib import Path
from config import ROOT,DEFAULT_PATTERNS
class FatalInputError(ValueError):pass

IMAGES={'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.webp'}
TAIL_SAFE=0.15
TAIL_IGNORE=0.3
OCR_DIGITS=str.maketrans('OoQDlI|SBZ','0000111582')
FUZZY_841=re.compile(r'(?<![0-9A-Za-z])([0-9OoQDlI|SBZ]{8})\s*[-–—−.]\s*([0-9OoQDlI|SBZ]{4})\s*[-–—−.]\s*([0-9OoQDlI|SBZ])(?![0-9A-Za-z])')
OCR_SAMPLES=[]

def trace(cfg,message):
 # Подробный журнал сканирования: что и когда проверялось. Сбой записи не должен ронять обработку.
 try:
  folder=Path(cfg['data_dir'])/'logs';folder.mkdir(parents=True,exist_ok=True)
  path=folder/'scan-v2.log'
  if path.exists() and path.stat().st_size>5*2**20:os.replace(path,folder/'scan-v2.log.1')
  with open(path,'a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S ')+message+'\n')
 except Exception:pass

def native_limits():
 for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
 import cv2
 cv2.setNumThreads(1)

def orient(cap):
 # Учитывать метаданные поворота видео (телефонная съёмка).
 import cv2
 try:cap.set(cv2.CAP_PROP_ORIENTATION_AUTO,1)
 except Exception:pass

def read_frame(cap,ts):
 # Последние кадры файла часто не читаются по времени: пробуем чуть раньше и по номеру кадра.
 import cv2
 try:fps=float(cap.get(cv2.CAP_PROP_FPS))
 except Exception:fps=0
 for back in (0,.05,.1,.2,.5,1.0):
  t=max(0.0,float(ts)-back)
  cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read()
  if ok and frame is not None:return True,frame
  if math.isfinite(fps) and fps>0:
   cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,int(t*fps)));ok,frame=cap.read()
   if ok and frame is not None:return True,frame
 return False,None

def rotate_frame(frame,degrees):
 import cv2
 d=int(degrees or 0)%360
 if d==90:return cv2.rotate(frame,cv2.ROTATE_90_CLOCKWISE)
 if d==180:return cv2.rotate(frame,cv2.ROTATE_180)
 if d==270:return cv2.rotate(frame,cv2.ROTATE_90_COUNTERCLOCKWISE)
 return frame

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

def extract(text,cfg,source='text',fuzzy=False):
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
 # Мягкий разбор 8-4-1: типичные ошибки OCR (O/0, l/1, S/5, B/8, Z/2) и точки вместо тире.
 if fuzzy and source=='text':
  for match in FUZZY_841.finditer(text):
   raw=''.join(match.group(1,2,3))
   if sum(c.isdigit() for c in raw)<10:continue
   digits=raw.translate(OCR_DIGITS)
   if not digits.isdigit() or len(digits)!=13:continue
   number=digits[:8]+'-'+digits[8:12]+'-'+digits[12:]
   if not any(existing[0]==number for existing in out):out.append((number,'Шаблон 8-4-1','Этикетка 8-4-1 мягкий'))
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
  text=out.decode('utf-8','replace')[:50000]
  if len(OCR_SAMPLES)<40:OCR_SAMPLES.append(' '.join(text.split())[:200])
  return text

def scaled(frame,width):
 import cv2
 h,w=frame.shape[:2]
 if max(h,w)>width:frame=cv2.resize(frame,(max(1,round(w*width/max(h,w))),max(1,round(h*width/max(h,w)))),interpolation=cv2.INTER_AREA)
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

def roi_images(frame,regions,full=None):
 # frame: кадр, из которого вырезаются блоки (может быть исходным, без уменьшения); full: уменьшенный кадр целиком.
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
 out.append(full if full is not None else frame)
 return out[:3] if len(out)>3 else out

def recognize_frame(frame,cfg,do_ocr=True,orig=None):
 import cv2
 fuzzy=bool(cfg.get('fuzzy_841',True))
 codes,regions=qr_regions(frame);findings=[];raw_codes=[]
 src=frame;rg=regions
 # QR ищем на уменьшенном кадре, а текст этикетки вырезаем из кадра в полном разрешении: мелкий текст при уменьшении теряется.
 if orig is not None and regions and orig.shape[:2]!=frame.shape[:2]:
  sx=orig.shape[1]/frame.shape[1];sy=orig.shape[0]/frame.shape[0]
  src=orig;rg=[(int(a*sx),int(b*sy),int(c*sx),int(d*sy)) for a,b,c,d in regions]
 for code in codes:
  raw=str(code.text)[:2000];raw_codes.append(raw)
  for number,market,template in extract(raw,cfg,source='qr'):findings.append(dict(number=number,market=market,method='QR / штрихкод',raw=raw,template=template,weak=('мягкий' in template)))
 # Даже если QR содержит подходящий номер, проверяем текст этикетки: QR может быть служебным.
 if do_ocr:
  seen=set()
  for index,image in enumerate(roi_images(src,rg,frame)):
   region_found=False
   for rotation in (0,90,180,270):
    rotated=image if rotation==0 else cv2.rotate(image,{90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation])
    gray=cv2.cvtColor(rotated,cv2.COLOR_BGR2GRAY) if len(rotated.shape)==3 else rotated
    gray=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
    text=ocr(gray,cfg,11)
    for number,market,template in extract(text,cfg,fuzzy=fuzzy):
     key=(number,index)
     if key in seen:continue
     seen.add(key);region_found=True
     findings.append(dict(number=number,market=market,method='QR-якорный OCR' if regions and index<len(regions) else 'OCR',raw=text[:2000],template=template,weak=('мягкий' in template)))
    if region_found:break
   if region_found:break
  # Усиленный проход: QR есть, а трек в тексте не найден — увеличиваем блок у QR и бинаризуем.
  if regions and not any('OCR' in f['method'] for f in findings) and cfg.get('qr_strong_ocr',True):
   try:
    crop=roi_images(src,rg,frame)[0]
    big=cv2.resize(crop,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    gray=cv2.cvtColor(big,cv2.COLOR_BGR2GRAY) if len(big.shape)==3 else big
    gray=cv2.GaussianBlur(gray,(3,3),0);_,bw=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    for rotation in (0,90,180,270):
     image=bw if rotation==0 else cv2.rotate(bw,{90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation])
     text=ocr(image,cfg,6);added=False
     for number,market,template in extract(text,cfg,fuzzy=fuzzy):
      if any(f['number']==number for f in findings):continue
      added=True;findings.append(dict(number=number,market=market,method='QR-якорный OCR (усиленный)',raw=text[:2000],template=template,weak=True))
     if added:break
   except (TimeoutError,RuntimeError):pass
 if not findings and raw_codes:findings.append(dict(number='',market='',method='QR без трека',raw='\n'.join(raw_codes)[:2000],template=''))
 return findings

def save_evidence(frame,cfg,key,ts,number):
 import cv2
 folder=Path(cfg['data_dir'])/'evidence-v2'/key;folder.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(folder).free<512*2**20:return ''
 digest=hashlib.sha256(number.encode()).hexdigest()[:10];path=folder/f'{ts:013.3f}-{digest}.jpg'
 ok,data=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,94])
 if not ok:return ''
 temp=path.with_suffix('.tmp');temp.write_bytes(data.tobytes());os.replace(temp,path);return str(path)

def short_result(hits,unknown=False,evidence=''):
 valid=[h for h in hits if h['number']];unique={h['number'] for h in valid}
 if not valid:return dict(state='review' if unknown else 'not_found',number='',market='',evidence=evidence if unknown else '',detail='QR найден, трек по шаблонам не найден' if unknown else 'Трек не найден')
 best=max(unique,key=lambda n:(len({h['ts'] for h in valid if h['number']==n}),sum(h['method']=='QR / штрихкод' for h in valid if h['number']==n),n))
 selected=[h for h in valid if h['number']==best];first=selected[0]
 reliable=(any(h['method']=='QR / штрихкод' for h in selected) or len({h['ts'] for h in selected})>=2) and any(not h.get('weak') for h in selected)
 state='done' if reliable and len(unique)==1 else 'review'
 detail='Согласованный номер' if state=='done' else 'Несколько номеров: проверьте этикетку' if len(unique)>1 else 'Текст подтверждён только одним кадром'
 return dict(state=state,number=best,market=first['market'],evidence=first.get('evidence',''),detail=detail)

def short_window(cfg,count,fps):
 # Окно сканирования короткой сессии в секундах: [start, end]; end=0 означает «до конца видео».
 last=max(0.0,(count-1)/fps-TAIL_SAFE)
 try:ws=max(0.0,float(cfg.get('short_start',0) or 0));we=float(cfg.get('short_end',0) or 0)
 except (ValueError,TypeError):ws=0.0;we=0.0
 we=last if we<=0 else min(last,we)
 if ws>=we:ws=0.0;we=last
 return ws,we

def scan(task,cfg,notify=lambda _:None):
 native_limits()
 import cv2,numpy as np
 from storage import identity
 path=Path(task['path'])
 if not path.is_file():raise FatalInputError('Исходный файл отсутствует или перемещён')
 if identity(path)!=cfg['source_id']:raise FatalInputError('Исходный файл изменился: добавьте его заново')
 start=float(task['cursor']);mode=task['mode'];hits=[];unknown=False;unknown_evidence='';cap=None;gaps=[]
 rot=int(cfg.get('rotation',0) or 0);window=(0.0,0.0)
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
   orient(cap)
   fps=float(cap.get(cv2.CAP_PROP_FPS));count=float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
   if not math.isfinite(fps) or not math.isfinite(count) or fps<=0 or count<=0:raise ValueError('Неизвестная длительность видео: требуется корректный индекс файла')
   duration=count/fps
   if mode=='long':
    end=min(duration,start+cfg['segment']);step=cfg['long_step'];first=math.ceil((start-1e-8)/step)*step
    times=[];t=first
    while t<end-1e-6:times.append(max(0,t));t+=step
   else:
    end=duration;window=short_window(cfg,count,fps);times=np.linspace(window[0],window[1],cfg['frames']).tolist()
   frames=None
  notify(dict(type='metadata',duration=duration,cursor=start))
  if cfg.get('probe_only'):return dict(state='pending',duration=duration,cursor=start,hits=[])
  evidence_cache={};warnings=[];read=0;fb_used=0;qr_frames=0;ocr_done=0
  ocr_indices={int(round(i)) for i in np.linspace(0,max(0,len(times)-1),min(len(times),cfg['ocr_frames']))}
  if mode=='short':trace(cfg,'%s: старт, окно %.1f–%.1f с из %.1f с, кадров %d, OCR-кадров %d'%(path.name,window[0],window[1],duration,len(times),len(ocr_indices)))
  plans=[times];pass_no=0
  while pass_no<len(plans):
   for index,ts in enumerate(plans[pass_no]):
    if frames is not None:frame=frames[0]
    else:
     ok,frame=read_frame(cap,ts)
     if not ok or frame is None:gaps.append((ts,min(duration,ts+cfg.get('long_step',1)),'Не удалось декодировать кадр'));continue
    read+=1;orig=rotate_frame(frame,rot);frame=scaled(orig,cfg['width'])
    do_ocr=((pass_no==0 and index in ocr_indices) if mode=='short' else (int(round(ts/cfg['long_step']))%cfg['long_ocr_every']==0))
    del OCR_SAMPLES[:]
    try:found=recognize_frame(frame,cfg,do_ocr,orig)
    except (TimeoutError,RuntimeError) as exc:
     found=recognize_frame(frame,cfg,False,orig);warnings.append(str(exc));gaps.append((ts,min(duration,ts+cfg.get('long_step',1)),str(exc)))
    if do_ocr:ocr_done+=1
    # Короткая сессия: QR найден, трека в нём нет, а OCR на этом кадре не запускался — дочитываем текст этикетки.
    if mode=='short' and not do_ocr and cfg.get('qr_text_fallback',True) and fb_used<int(cfg.get('qr_text_fallback_max',12)) and found and not any(h['number'] for h in found):
     fb_used+=1;ocr_done+=1;do_ocr=True
     try:found=recognize_frame(frame,cfg,True,orig)
     except (TimeoutError,RuntimeError) as exc:warnings.append(str(exc));gaps.append((ts,min(duration,ts+cfg.get('long_step',1)),str(exc)))
    if found:qr_frames+=1
    if mode=='short':
     qr_text=' | '.join(' '.join(h['raw'].split())[:120] for h in found if not h['number'])
     trace(cfg,'%s: проход %d, t=%.2f с, OCR=%s, найдено=%s%s%s'%(path.name,pass_no+1,ts,'да' if do_ocr else 'нет',[(h['number'] or 'QR без трека',h['method']) for h in found],(', текст QR=['+qr_text+']') if qr_text else '',(', текст OCR=['+' || '.join(OCR_SAMPLES[:3])+']') if OCR_SAMPLES else ''))
    for h in found:
     if not h['number']:
      unknown=True
      if not unknown_evidence:unknown_evidence=save_evidence(frame,cfg,task['id'],ts,'qr-no-track')
      continue
     h.update(ts=round(ts,3),state='review' if 'OCR' in h['method'] or h.get('weak') else 'done')
     if h['number'] not in evidence_cache:evidence_cache[h['number']]=save_evidence(frame,cfg,task['id'],ts,h['number'])
     h['evidence']=evidence_cache[h['number']];hits.append(h)
    notify(dict(type='progress',cursor=ts,duration=duration))
   # Второй, более частый проход: в первом проходе трек не найден — берём кадры между уже проверенными.
   if mode=='short' and pass_no==0 and cfg.get('short_second_pass',True) and frames is None and len(times)>1 and not any(h['number'] for h in hits):
    plans.append([(a+b)/2 for a,b in zip(times,times[1:])])
    trace(cfg,'%s: трек не найден, второй проход по %d промежуточным кадрам'%(path.name,len(plans[1])))
   pass_no+=1
  if not read and times:raise ValueError('Ни один кадр интервала не прочитан')
  if mode=='short':
   result=short_result(hits,unknown,unknown_evidence)
   real_gaps=[g for g in gaps if g[0]<duration-TAIL_IGNORE or g[2]!='Не удалось декодировать кадр']
   if real_gaps:result.update(state='review' if (hits or unknown) else 'error',detail=result['detail']+'; есть пропуски декодирования / OCR')
   trace(cfg,'%s: итог %s, номер=%s, прочитано кадров %d, кадров с QR/находками %d, OCR-вызовов %d, пропусков %d, причина: %s'%(path.name,result['state'],result.get('number') or '-',read,qr_frames,ocr_done,len(gaps),result['detail']))
  else:
   result=dict(state='done' if end>=duration-1e-6 else 'pending',detail='Индексация: '+str(len(hits))+' наблюдений за интервал')
  result.update(hits=hits,cursor=end,duration=duration,gaps=gaps)
  return result
 finally:
  if cap is not None:cap.release()
