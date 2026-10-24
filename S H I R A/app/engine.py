import json,shutil,logging,logging.handlers,multiprocessing,os,queue,threading,time
from pathlib import Path
from config import data_dir,worker_config,ROOT
from recognition import kill_tree
from windows_job import assign as assign_job,close as close_job

def worker(task,cfg,conn):
 try:
  from recognition import scan
  last=[0.0]
  def notify(msg):
   if msg['type']=='metadata' or time.monotonic()-last[0]>.25:
    conn.send(msg);last[0]=time.monotonic()
  result=scan(task,cfg,notify);conn.send(dict(type='result',result=result))
 except BaseException as exc:
  import traceback
  try:conn.send(dict(type='failure',error=str(exc),fatal=type(exc).__name__ in ('FatalInputError','FileNotFoundError','PermissionError'),trace=traceback.format_exc()))
  except (BrokenPipeError,EOFError,OSError):pass
 finally:conn.close()

class Engine:
 def __init__(self,store,callback=lambda *_:None):
  self.store=store;self.callback=callback;self.stop_event=threading.Event();self.thread=None;self.last_error=None
  logger=logging.getLogger('shira');logger.setLevel(logging.INFO)
  if not logger.handlers:
   folder=data_dir()/'logs';folder.mkdir(exist_ok=True)
   handler=logging.handlers.RotatingFileHandler(folder/'app-v2.log',maxBytes=2*2**20,backupCount=3,encoding='utf-8');handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(handler)
  self.logger=logger
 def emit(self,kind,value):
  if kind in ('log','error'):self.logger.info('%s: %s',kind,value)
  try:self.callback(kind,value)
  except Exception:self.logger.exception('Callback failed')
 def running(self):return bool(self.thread and self.thread.is_alive())
 def start(self,concurrency=1):
  if self.running():return
  self.stop_event.clear();self.last_error=None;self.thread=threading.Thread(target=self.run,args=(max(1,min(4,concurrency)),),daemon=True);self.thread.start()
 def stop(self):self.stop_event.set()
 def run(self,concurrency):
  ctx=multiprocessing.get_context('spawn');active={};low_disk_notified=False
  try:
   while True:
    if self.stop_event.is_set():break
    while len(active)<concurrency:
     if shutil.disk_usage(data_dir()).free<256*2**20:
      if not active:raise RuntimeError('Недостаточно места для БД: освободите минимум 256 МБ. Очередь сохранена.')
      if not low_disk_notified:self.emit('log','Мало места на диске: новые задачи не берутся, текущие будут завершены');low_disk_notified=True
      break
     low_disk_notified=False
     task=self.store.claim()
     if not task:break
     cfg=json.loads(task['cfg']);cfg.update(root=str(ROOT),data_dir=str(data_dir()))
     rx,tx=ctx.Pipe(duplex=False);process=ctx.Process(target=worker,args=(task,cfg,tx),daemon=False)
     try:process.start()
     except Exception as exc:rx.close();tx.close();self.store.failed(task['id'],str(exc));continue
     tx.close();job=None
     try:job=assign_job(process.pid)
     except OSError as exc:self.emit('log','Windows Job Object недоступен; действует резервная остановка дерева: '+str(exc))
     active[task['id']]=dict(task=task,cfg=cfg,p=process,rx=rx,job=job,started=time.monotonic());self.emit('log','Обработка: '+task['path'])
    if not active:break
    for key,item in list(active.items()):
     p=item['p'];rx=item['rx'];result=None;failure=None;fatal=False
     if time.monotonic()-item['started']>item['cfg']['timeout']:failure='Тайм-аут интервала; процесс остановлен'
     else:
      try:
       for _ in range(100):
        if not rx.poll():break
        msg=rx.recv()
        if msg['type']=='metadata':self.store.set_duration(key,msg['duration'])
        elif msg['type']=='progress':self.emit('progress',dict(id=key,**msg))
        elif msg['type']=='result':result=msg['result'];break
        elif msg['type']=='failure':failure=msg['error'];fatal=msg.get('fatal',False);self.logger.error(msg.get('trace',''));break
      except (EOFError,OSError):
       if result is None:failure='Обработчик завершился без результата'
      if result is None and failure is None and not p.is_alive() and not rx.poll():failure='Аварийное завершение обработчика'
     if result is not None or failure is not None:
      if p.is_alive():
       if result is not None:p.join(.5)
       if p.is_alive():kill_tree(p.pid)
      p.join(3);rx.close();close_job(item.get('job'));item['job']=None
      if result is not None and failure is None:
       try:self.store.checkpoint(key,result)
       except Exception as exc:
        self.logger.exception('Checkpoint failed');failure='Ошибка сохранения результата: '+str(exc);result=None
      if failure:
       if fatal:self.store.set_state(key,'error',failure)
       else:self.store.failed(key,failure)
       self.emit('error',item['task']['name']+': '+failure)
      else:
       self.emit('log',item['task']['name']+': '+result['state'])
      active.pop(key,None);self.emit('changed',key)
    self.stop_event.wait(.05)
  except BaseException as exc:
   self.last_error=str(exc);self.logger.exception('Coordinator failed');self.emit('error',str(exc))
  finally:
   for key,item in active.items():
    if item['p'].is_alive():kill_tree(item['p'].pid)
    item['p'].join(3);item['rx'].close();close_job(item.get('job'))
    try:self.store.set_state(key,'cancelled','Остановлено; сохранена последняя контрольная точка')
    except Exception:self.logger.exception('Не удалось записать статус остановки; задача будет восстановлена при запуске')
   self.emit('finished',None)
