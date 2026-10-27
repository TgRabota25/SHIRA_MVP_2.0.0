import csv,json,os,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from config import settings,worker_config,DEFAULT_PATTERNS,PROFILES,stamp,atomic_json
from storage import Store,AppLock,identity
from recognition import extract,short_result,scan,recognize_frame
from engine import Engine

class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.folder=Path(self.tmp.name);self.old=os.environ.get('SHIRA_DATA_DIR');os.environ['SHIRA_DATA_DIR']=str(self.folder/'data');self.store=Store(self.folder/'test.db');self.cfg=worker_config(settings());self.cfg.update(language='eng',profile='weak',**PROFILES['weak'])
 def tearDown(self):
  if self.old is None:os.environ.pop('SHIRA_DATA_DIR',None)
  else:os.environ['SHIRA_DATA_DIR']=self.old
  self.tmp.cleanup()
 def add(self,name='control_qr.png',mode='short'):
  cfg=dict(self.cfg,mode=mode);key,_=self.store.add(ROOT/'examples'/name,cfg);return key
 def wait(self,engine,limit=90):
  until=time.monotonic()+limit
  while engine.running() and time.monotonic()<until:time.sleep(.05)
  if engine.running():engine.stop();engine.thread.join(15);self.fail('Engine timeout')

class StoreTests(Base):
 def test_duplicate(self):
  a=self.add();self.assertEqual(a,self.add());self.assertEqual(sum(self.store.counts().values()),1)
 def test_separate_sessions(self):self.assertNotEqual(self.add(mode='short'),self.add(mode='long'))
 def test_same_basename_separate(self):
  a=self.add();p=self.folder/'control_qr.png';p.write_bytes((ROOT/'examples/control_qr.png').read_bytes()+b'\0');b,_=self.store.add(p,self.cfg);self.assertNotEqual(a,b)
 def test_empty_rejected(self):
  p=self.folder/'empty.mp4';p.touch()
  with self.assertRaises(ValueError):self.store.add(p,self.cfg)
 def test_bad_extension(self):
  p=self.folder/'x.exe';p.write_bytes(b'a')
  with self.assertRaises(ValueError):self.store.add(p,self.cfg)
 def test_claim_once(self):self.add();self.assertIsNotNone(self.store.claim());self.assertIsNone(self.store.claim())
 def test_recovery(self):
  key=self.add();self.store.claim();self.store.recover();self.assertEqual(self.store.get(key)['state'],'pending')
 def test_cursor_monotonic(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='pending',cursor=5,duration=10))
  with self.assertRaises(ValueError):self.store.checkpoint(key,dict(state='pending',cursor=2))
 def test_atomic_rollback(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='pending',cursor=5))
  with self.assertRaises(ValueError):self.store.checkpoint(key,dict(state='pending',cursor=2,hits=[dict(number='test',ts=1,method='OCR')]))
  self.assertEqual(self.store.hits(key)[1],0)
 def test_idempotent_hit(self):
  key=self.add(mode='long');result=dict(state='pending',cursor=2,hits=[dict(number='x',ts=1,method='OCR')]);self.store.checkpoint(key,result);self.store.checkpoint(key,result);self.assertEqual(self.store.hits(key)[1],1)
 def test_gap_marks_partial(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',cursor=6,duration=6,gaps=[(1,2,'decode')]))
  self.assertEqual(self.store.get(key)['state'],'partial')
 def test_empty_long_not_found(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',cursor=6,duration=6));self.assertEqual(self.store.get(key)['state'],'not_found')
 def test_failure_retried(self):
  key=self.add();self.store.failed(key,'bad');self.assertEqual(self.store.get(key)['state'],'pending');self.store.failed(key,'bad');self.assertEqual(self.store.get(key)['state'],'error')
 def test_long_failed_segment_visible_gap(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='pending',cursor=0,duration=150));self.store.failed(key,'timeout');self.store.failed(key,'timeout');self.assertEqual(len(self.store.gaps(key)),1);self.assertGreater(self.store.get(key)['cursor'],0)
 def test_resume_keeps_index(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='cancelled',cursor=2,duration=8,hits=[dict(number='x',ts=1,method='OCR')]));self.store.retry([key]);self.assertEqual(self.store.get(key)['cursor'],2);self.assertEqual(self.store.hits(key)[1],1)
 def test_reset_clears_index(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',cursor=8,duration=8,hits=[dict(number='x',ts=1,method='OCR')]));self.store.retry([key],True);self.assertEqual(self.store.get(key)['cursor'],0);self.assertEqual(self.store.hits(key)[1],0);self.assertTrue(self.store.history(key))
 def test_bulk_retry(self):
  a=self.add();b=self.add('control_text.png');self.store.set_state(a,'error');self.store.set_state(b,'cancelled');self.store.retry([a,b]);self.assertEqual(self.store.counts(),{'pending':2})
 def test_sort(self):
  self.add('control_text.png');self.add('control_qr.png');rows,_=self.store.page(sort='name',descending=False);self.assertEqual([r['name'] for r in rows],sorted(r['name'] for r in rows))
 def test_sort_injection_whitelisted(self):self.add();self.assertEqual(self.store.page(sort='name;DROP TABLE tasks')[1],1)
 def test_sort_hit_count(self):self.add();self.assertEqual(len(self.store.page(sort='hit_count')[0]),1)
 def test_search_hits(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',hits=[dict(number='81604409-0321-5',ts=4,method='OCR')]))
  self.assertEqual(self.store.page(search='81604409')[1],1)
 def test_literal_search(self):self.add();self.assertEqual(self.store.page(search='%')[1],0)
 def test_pagination(self):self.add();self.assertEqual(self.store.page(page=1,limit=1)[0],[])
 def test_confirm_audit(self):
  key=self.add();self.store.confirm(key,'81604409-0321-5','Custom');self.assertEqual(self.store.get(key)['state'],'accepted');self.assertTrue(self.store.history(key))
 def test_running_not_editable(self):
  key=self.add();self.store.claim()
  with self.assertRaises(ValueError):self.store.confirm(key,'x','')
 def test_confirm_hit(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',hits=[dict(number='x',ts=1,method='OCR')]))
  hit=self.store.hits(key)[0][0];self.store.confirm(key,'y','',hit['id']);self.assertEqual(self.store.hits(key)[0][0]['number'],'y')
 def test_legacy_import_read_only(self):
  from legacy_import import import_legacy
  source=self.folder/'v1.db';db=sqlite3.connect(source);db.execute('CREATE TABLE jobs(id TEXT,path TEXT,state TEXT,number TEXT,market TEXT,evidence TEXT,detail TEXT)');db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',('old',str(ROOT/'examples/control_qr.png'),'accepted','ii12345678901','Ozon','',''));db.commit();db.close();before=source.read_bytes()
  result=import_legacy(self.store,source);self.assertIn('импортировано 1',result);self.assertEqual(source.read_bytes(),before);self.assertEqual(self.store.page()[0][0]['state'],'accepted')
 def test_summary_times(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',hits=[dict(number='x',ts=t,method='OCR') for t in [1,2,3]]));r=self.store.summary(key)[0];self.assertEqual((r['first_seen'],r['last_seen'],r['samples']),(1,3,3))
 def test_hit_sort(self):
  key=self.add(mode='long');self.store.checkpoint(key,dict(state='done',hits=[dict(number=n,ts=t,method='OCR') for n,t in [('z',1),('a',2)]]));self.assertEqual(self.store.hits(key,sort='number')[0][0]['number'],'a')
 def test_csv_formula(self):
  key=self.add();self.store.confirm(key,'=SUM(1)','');dest=self.folder/'x.csv';self.store.export(dest)
  with dest.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
  self.assertEqual(rows[1][4],"'=SUM(1)")
 def test_xlsx(self):
  from openpyxl import load_workbook
  self.add();dest=self.folder/'x.xlsx';self.store.export(dest);book=load_workbook(dest,read_only=True);self.assertEqual(len(list(book.active.values)),2);book.close()
 def test_short_export_uses_manual_number(self):
  key=self.add();self.store.checkpoint(key,dict(state='done',number='old',hits=[dict(number='old',ts=1,method='QR / штрихкод')]))
  self.store.confirm(key,'corrected','M');dest=self.folder/'manual.csv';self.store.export(dest)
  with dest.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
  self.assertEqual(len(rows),2);self.assertEqual(rows[1][4],'corrected')
 def test_backup(self):
  self.add();dest=self.folder/'backup.db';self.store.backup(dest);self.assertEqual(sum(Store(dest).counts().values()),1)
 def test_backup_same(self):
  with self.assertRaises(ValueError):self.store.backup(self.store.path)
 def test_single_instance(self):
  lock=AppLock().acquire()
  try:
   child=subprocess.run([sys.executable,'-c',"import sys;sys.path.insert(0,sys.argv[1]);from storage import AppLock;AppLock().acquire()",str(ROOT/'app')],capture_output=True,timeout=10);self.assertNotEqual(child.returncode,0)
  finally:lock.close()

class RecognitionTests(Base):
 def test_requested_template(self):self.assertIn('81604409-0321-5',[x[0] for x in extract('трек 81604409-0321-5',self.cfg)])
 def test_ozon_new(self):self.assertIn('ii50065384261',[x[0] for x in extract('ii50065384261',self.cfg)])
 def test_legacy_space_pattern(self):self.assertIn('1234567890-1234-1',[x[0] for x in extract('123456 7890-1234-1',self.cfg)])
 def test_legacy_yandex_soft(self):self.assertIn('1234567890-12',[x[0] for x in extract('1234567890-12',self.cfg)])
 def test_weak_qr_requires_review(self):self.assertEqual(short_result([dict(number='x',market='',ts=1,method='QR / штрихкод',weak=True)])['state'],'review')
 def test_qr_order_not_global_phone(self):self.assertEqual(extract('79991234567',self.cfg,source='qr')[0][0],'79991234567')
 def test_old_ozon(self):self.assertIn('1234567890-1234-1',[x[0] for x in extract('1234567890-1234-1',self.cfg)])
 def test_yandex(self):self.assertIn('12345678901-12',[x[0] for x in extract('12345678901-12',self.cfg)])
 def test_arbitrary_phone_rejected(self):self.assertEqual(extract('79991234567',self.cfg),[])
 def test_custom(self):
  cfg=dict(self.cfg,patterns=[dict(name='Custom',market='M',regex=r'ABC-\d{5}')]);self.assertEqual(extract('ABC-12345',cfg)[0][0],'ABC-12345')
 def test_invalid_regex(self):
  with self.assertRaises(ValueError):extract('x',dict(self.cfg,patterns=[dict(regex='[')]))
 def test_single_ocr_review(self):self.assertEqual(short_result([dict(number='x',market='',ts=1,method='OCR')])['state'],'review')
 def test_two_frames_done(self):self.assertEqual(short_result([dict(number='x',market='',ts=t,method='OCR') for t in [1,2]])['state'],'done')
 def test_two_rotations_same_frame_not_consensus(self):self.assertEqual(short_result([dict(number='x',market='',ts=1,method='OCR')]*2)['state'],'review')
 def test_conflict_review(self):self.assertEqual(short_result([dict(number=x,market='',ts=1,method='QR / штрихкод') for x in ['a','b']])['state'],'review')
 def test_unknown_qr_review(self):self.assertEqual(short_result([],True)['state'],'review')
 def test_changed_source(self):
  p=self.folder/'x.png';p.write_bytes((ROOT/'examples/control_qr.png').read_bytes());key,_=self.store.add(p,self.cfg);p.write_bytes(b'bad')
  with self.assertRaises(ValueError):scan(self.store.get(key),json.loads(self.store.get(key)['cfg']))
 def test_timestamp_8_hours(self):self.assertEqual(stamp(8*3600+1.5),'08:00:01.500')
 def test_auto(self):
  from config import auto_profile
  key,info=auto_profile();self.assertIn(key,PROFILES);self.assertIn('available_ram_gb',info)
 def test_classify_mode_boundary(self):
  from config import classify_mode
  self.assertEqual(classify_mode(3599),'short')
  self.assertEqual(classify_mode(3599.999),'short')
  self.assertEqual(classify_mode(3600),'long')
  self.assertEqual(classify_mode(3600.0),'long')
  self.assertEqual(classify_mode(3601),'long')
  self.assertEqual(classify_mode(None),None)
  self.assertEqual(classify_mode('bad'),None)
  self.assertEqual(classify_mode(-1),None)
 def test_atomic_settings(self):
  p=self.folder/'x.json';atomic_json(p,dict(test='тест'));self.assertEqual(json.loads(p.read_text('utf-8'))['test'],'тест')

class IntegrationTests(Base):
 def run_scan(self,name,mode='short',**overrides):
  key=self.add(name,mode);task=self.store.get(key);cfg=json.loads(task['cfg']);cfg.update(overrides);return key,scan(task,cfg)
 def test_real_qr(self):
  _,r=self.run_scan('control_qr.png');self.assertEqual(r['number'],'ii12345678901');self.assertEqual(r['state'],'done')
 def test_real_ocr(self):
  _,r=self.run_scan('control_text.png');self.assertEqual(r['number'],'81604409-0321-5');self.assertEqual(r['state'],'review')
 def test_service_qr_near_text(self):
  _,r=self.run_scan('control_qr_near_text.png');self.assertEqual(r['number'],'81604409-0321-5');self.assertTrue(any(h['method']=='QR-якорный OCR' for h in r['hits']))
 def test_rotated_service_label(self):
  _,r=self.run_scan('control_rotated_label.png');self.assertEqual(r['number'],'81604409-0321-5')
 def test_long_chunk_resume_real_video(self):
  key=self.add('control_multi_label.avi','long');task=self.store.get(key);cfg=json.loads(task['cfg']);cfg.update(segment=2,long_step=1,long_ocr_every=100)
  r=scan(task,cfg);self.store.checkpoint(key,r);self.assertEqual(r['cursor'],2)
  task=self.store.get(key);r=scan(task,cfg);self.store.checkpoint(key,r);self.assertEqual(r['cursor'],4)
  task=self.store.get(key);r=scan(task,cfg);self.store.checkpoint(key,r)
  numbers={h['number'] for h in self.store.hits(key)[0]};self.assertIn('ii12345678901',numbers);self.assertIn('ii99999999999',numbers)
 def test_spawn_engine(self):
  key=self.add('control_qr.png');engine=Engine(self.store);engine.start();self.wait(engine);self.assertEqual(self.store.get(key)['state'],'done')
 def test_corrupt_file_does_not_stop_queue(self):
  p=self.folder/'bad.mp4';p.write_bytes(b'bad');bad,_=self.store.add(p,self.cfg);good=self.add('control_qr.png');engine=Engine(self.store);engine.start();self.wait(engine);self.assertEqual(self.store.get(bad)['state'],'error');self.assertEqual(self.store.get(good)['state'],'done')
 def test_stop_resume(self):
  key=self.add('control_multi_label.avi','long');engine=Engine(self.store);engine.start();time.sleep(.2);engine.stop();self.wait(engine);self.assertNotEqual(self.store.get(key)['state'],'running')
 def test_timestamp_beyond_8_hours_real_container(self):
  from unittest.mock import patch
  key=self.add('control_9h_sparse.avi','long');self.store.checkpoint(key,dict(state='pending',cursor=28800,duration=32400));task=self.store.get(key);cfg=json.loads(task['cfg']);cfg.update(segment=60,long_step=30,long_ocr_every=1)
  with patch('recognition.recognize_frame',return_value=[]):result=scan(task,cfg)
  self.assertGreaterEqual(result['duration'],32400);self.assertEqual(result['cursor'],28860);self.assertFalse(result['gaps'])
 def test_changed_long_source_is_error_not_many_skips(self):
  p=self.folder/'change.avi';p.write_bytes((ROOT/'examples/control_multi_label.avi').read_bytes());cfg=dict(self.cfg,mode='long');key,_=self.store.add(p,cfg);self.store.checkpoint(key,dict(state='pending',cursor=2,duration=6));p.write_bytes(b'changed');engine=Engine(self.store);engine.start();self.wait(engine);self.assertEqual(self.store.get(key)['state'],'error');self.assertEqual(self.store.gaps(key),[])
 def test_deadline(self):
  cfg=dict(self.cfg,timeout=.001);key,_=self.store.add(ROOT/'examples/control_text.png',cfg);engine=Engine(self.store);engine.start();self.wait(engine);self.assertEqual(self.store.get(key)['state'],'error')
if __name__=='__main__':unittest.main(verbosity=2)
