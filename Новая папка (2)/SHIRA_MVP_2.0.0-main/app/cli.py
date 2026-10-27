import argparse,json,multiprocessing,os,sys,time
from pathlib import Path
from config import settings,worker_config,PROFILES,atomic_json,data_dir
from storage import Store,AppLock,EXTENSIONS
from engine import Engine

def main():
 parser=argparse.ArgumentParser(description='SHIRA: короткая обработка и индекс длинных видео')
 parser.add_argument('paths',nargs='*');parser.add_argument('--mode',choices=['short','long'],default='short');parser.add_argument('--profile',choices=list(PROFILES));parser.add_argument('--step',type=float);parser.add_argument('--ocr-every',type=int);parser.add_argument('--recursive',action='store_true');parser.add_argument('--retry-errors',action='store_true');parser.add_argument('--export');parser.add_argument('--search');args=parser.parse_args()
 lock=AppLock()
 try:
  lock.acquire();store=Store();store.recover();cfg=settings();cfg['mode']=args.mode
  if args.profile:cfg['profile']=args.profile
  if args.step is not None:
   if not .1<=args.step<=60:raise ValueError('--step: 0.1..60 секунд')
   cfg['long_step']=args.step
  if args.ocr_every is not None:
   if not 1<=args.ocr_every<=100:raise ValueError('--ocr-every: 1..100')
   cfg['long_ocr_every']=args.ocr_every
  added=0;errors=0
  for name in args.paths:
   path=Path(name)
   candidates=path.rglob('*') if path.is_dir() and args.recursive else path.iterdir() if path.is_dir() else [path]
   for p in candidates:
    if p.is_symlink() or not p.is_file() or p.suffix.lower() not in EXTENSIONS:continue
    try:_,new=store.add(p,worker_config(cfg));added+=int(new)
    except Exception as exc:errors+=1;print(str(exc),file=sys.stderr)
  print('Добавлено:',added)
  if args.retry_errors:
   with store.db() as db:ids=[r[0] for r in db.execute("SELECT id FROM tasks WHERE state IN ('error','cancelled')")]
   store.retry(ids)
  if args.search:
   rows,total=store.hits(search=args.search)
   print(json.dumps(dict(total=total,hits=rows),ensure_ascii=False,indent=2));return 0
  engine=Engine(store,lambda kind,value:print(value,flush=True) if kind in ('log','error') else None);engine.start(PROFILES[cfg['profile']]['workers'])
  try:
   while engine.running():time.sleep(.1)
  except KeyboardInterrupt:
   engine.stop();engine.thread.join(20);return 130
  if args.export:store.export(args.export)
  print(json.dumps(store.counts(),ensure_ascii=False));return 2 if errors or engine.last_error or store.counts().get('error') else 0
 finally:lock.close()
if __name__=='__main__':multiprocessing.freeze_support();sys.exit(main())
