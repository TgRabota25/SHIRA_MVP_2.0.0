"""Read-only, best-effort import of prior MVP SQLite results; never executes source SQL."""
import hashlib,json,sqlite3,time
from pathlib import Path
from config import worker_config,settings
from storage import identity

def import_legacy(store,path):
 path=Path(path).resolve()
 if path==store.path.resolve():raise ValueError('Выбрана текущая база')
 if path.stat().st_size>2*2**30:raise ValueError('База импорта превышает 2 ГБ')
 source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);source.row_factory=sqlite3.Row
 source.enable_load_extension(False)
 deadline=time.monotonic()+120;source.set_progress_handler(lambda:1 if time.monotonic()>deadline else 0,10000)
 imported=skipped=0
 try:
  tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if 'jobs' not in tables:raise ValueError('Нужна база предыдущего MVP с таблицей jobs. Старая checked_videos.db автоматически не импортируется.')
  columns={r[1] for r in source.execute('PRAGMA table_info(jobs)')}
  if not {'path','state'}.issubset(columns):raise ValueError('Неизвестная схема таблицы jobs')
  for row in source.execute('SELECT * FROM jobs'):
   value=dict(row);p=Path(value['path']);cfg=worker_config(settings());cfg['mode']='short';available=p.is_file()
   if available:
    try:key,new=store.add(p,cfg)
    except (OSError,ValueError):available=False
   if not available:
    fid=hashlib.sha256(('legacy:'+str(p)).encode()).hexdigest();key=hashlib.sha256((fid+'|short').encode()).hexdigest();cfg['source_id']=fid;now=time.time()
    with store.db() as db:
     cur=db.execute('INSERT OR IGNORE INTO tasks(id,path,name,mode,state,cfg,created,updated) VALUES(?,?,?,?,?,?,?,?)',(key,str(p),p.name,'short','review',json.dumps(cfg,ensure_ascii=False),now,now));new=bool(cur.rowcount)
   if not new:skipped+=1;continue
   state=value['state'] if value['state'] in ('done','accepted','review','not_found','error','cancelled') else 'review'
   evidence=value.get('evidence','')
   if evidence and not Path(evidence).is_file():evidence=''
   with store.db() as db:
    db.execute('UPDATE tasks SET state=?,number=?,market=?,detail=?,evidence=? WHERE id=?',(state,str(value.get('number','')),str(value.get('market','')),'Импорт v1. '+('Исходник доступен. ' if available else 'Исходник отсутствует. ')+str(value.get('detail','')),evidence,key))
    db.execute('INSERT INTO audit(task_id,at,action,payload) VALUES(?,?,?,?)',(key,time.time(),'legacy_import',json.dumps(dict(source=str(path),legacy_id=value.get('id')),ensure_ascii=False)))
   imported+=1
 finally:source.close()
 return f'импортировано {imported}, уже есть {skipped}. Исходная база открывалась только для чтения.'
