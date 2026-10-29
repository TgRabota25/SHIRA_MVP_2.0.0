import json,logging,multiprocessing,os,queue,re,subprocess,sys,tempfile,threading,time,traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from config import ROOT,VERSION,PROFILES,settings,worker_config,auto_profile,atomic_json,data_dir,stamp
from theme import apply_theme, DEFAULT_THEME, THEME_LABELS, stat_card, status_badge, make_card, make_section, divider, apply_palette_to_widget
from storage import Store,AppLock,EXTENSIONS,LABELS
from engine import Engine
from platform_ui import app_identity,icon,open_path,copy_files
from imageview import brand_icon,Rotations,render_image
from photo_ui import PhotoWindow

def make_scrollable(parent,padding=15,bg=None):
 frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
 canvas=tk.Canvas(frame,highlightthickness=0);scroll=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview)
 if bg:canvas.configure(bg=bg)
 canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
 inner=ttk.Frame(canvas,padding=padding);window=canvas.create_window((0,0),window=inner,anchor='nw')
 inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
 canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
 def wheel(event):
  if isinstance(event.widget,tk.Text):return
  delta=getattr(event,'delta',0)
  if delta:canvas.yview_scroll(-1 if delta>0 else 1,'units')
  elif getattr(event,'num',0)==4:canvas.yview_scroll(-1,'units')
  elif getattr(event,'num',0)==5:canvas.yview_scroll(1,'units')
  return 'break'
 parent.bind('<MouseWheel>',wheel,add='+');parent.bind('<Button-4>',wheel,add='+');parent.bind('<Button-5>',wheel,add='+')
 return canvas,inner

class Application:
 def __init__(self,root,store):
  self.root=root;self.store=store;self.cfg=settings();self.events=queue.Queue(maxsize=500);self.engine=Engine(store,self.post);self.rot=Rotations()
  self.page=0;self.total=0;self.sort='created';self.desc=True;self.rows={};self.busy=0;self.closed=False;self.last_refresh=0;self.photo_window=None
  root.title('SHIRA '+VERSION+' — этикетки и видеоархив');root.geometry('1400x900');root.minsize(1150,720);icon(root)
  root.protocol('WM_DELETE_WINDOW',self.close);root.report_callback_exception=self.callback_error
  style=ttk.Style();style.theme_use('clam')
  self.theme_mode=self.cfg.get('theme',DEFAULT_THEME)
  self.theme=apply_theme(root,self.theme_mode)
  self.nav_active=tk.StringVar(value='queue')
  self.build();self.store.recover();self.refresh();self.bind_copy(root);root.bind('<Button-1>',self.clear_selection_if_empty,add='+');root.after(120,self.poll);root.after(80,lambda:center_window(root))
 def clear_selection_if_empty(self,event):
  if event.widget is self.tree:return
  if self.tree.selection():self.tree.selection_remove(*self.tree.selection())
 def callback_error(self,kind,value,tb):
  self.engine.logger.error('GUI callback',exc_info=(kind,value,tb));messagebox.showerror('SHIRA',str(value),parent=self.root)
 def post(self,kind,value):
  try:self.events.put_nowait((kind,value))
  except queue.Full:
   if kind in ('background_done','finished','error'):
    try:self.events.get_nowait();self.events.put_nowait((kind,value))
    except (queue.Empty,queue.Full):pass
 def rot_file(self):return data_dir()/'rotations-v2.json'
 def get_rotation(self,path):
  try:return int(json.loads(self.rot_file().read_text('utf-8')).get(str(path),0))%360
  except Exception:return 0
 def set_rotation(self,path,degrees):
  try:data=json.loads(self.rot_file().read_text('utf-8'))
  except Exception:data={}
  data[str(path)]=int(degrees)%360;atomic_json(self.rot_file(),data)
 def background(self,fn,label):
  self.busy+=1;self.status.set(label)
  def work():
   try:result=fn();self.post('notice',label+': '+str(result or 'готово'))
   except Exception as exc:self.post('error',label+': '+str(exc))
   finally:self.post('background_done',None)
  threading.Thread(target=work,daemon=True).start()
 def build(self):
  pal=self.theme['palette'];F=self.theme['fonts'];S=self.theme['space']
  # ---------- Корневой контейнер ----------
  root=tk.Frame(self.root,bg=pal['canvas']);root.pack(fill='both',expand=True)
  # ---------- Боковая навигация ----------
  sidebar=tk.Frame(root,bg=pal['surface'],width=220);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
  tk.Frame(sidebar,bg=pal['border'],height=1).pack(side='right',fill='y')
  brand=tk.Frame(sidebar,bg=pal['surface'],height=72);brand.pack(fill='x')
  try:
   from PIL import ImageTk
   self.brand_img=ImageTk.PhotoImage(brand_icon(ROOT/'app/icon.png',32))
   tk.Label(brand,image=self.brand_img,bg=pal['surface']).pack(side='left',padx=(16,8),pady=18)
  except Exception:self.brand_img=None
  tk.Label(brand,text='SHIRA',bg=pal['surface'],fg=pal['ink'],font=F['heading']).pack(side='left',pady=18)
  tk.Label(brand,text='v'+VERSION,bg=pal['surface'],fg=pal['muted'],font=F['caption']).pack(side='left',pady=18)
  nav_items=[('queue','Очередь','📋'),('index','Индекс этикеток','🔖'),('photo','Группировка фото','🖼️'),('settings','Настройки','⚙️')]
  self.nav_buttons={}
  for key,label,icon_txt in nav_items:
   btn=tk.Button(sidebar,text=f'  {icon_txt}  {label}',bg=pal['surface'],fg=pal['muted'],font=F['ui'],
                 bd=0,highlightthickness=0,activebackground=pal['accent_soft'],activeforeground=pal['accent_text'],
                 cursor='hand2',anchor='w',padx=16,pady=12,
                 command=lambda k=key:self._nav_switch(k))
   btn.pack(fill='x')
   self.nav_buttons[key]=btn
  self._nav_switch('queue')
  tk.Frame(sidebar,bg=pal['border_soft'],height=1).pack(fill='x',pady=S['4'])
  theme_btn=tk.Button(sidebar,text='Тема: '+THEME_LABELS[self.theme_mode],bg=pal['surface'],fg=pal['muted'],
                      font=F['small'],bd=0,highlightthickness=0,cursor='hand2',anchor='w',padx=16,pady=10,
                      command=self._toggle_theme);theme_btn.pack(fill='x')
  self.theme_btn=theme_btn
  # ---------- Основное содержимое ----------
  content=tk.Frame(root,bg=pal['canvas']);content.pack(side='left',fill='both',expand=True)
  # --- Шапка ---
  header=tk.Frame(content,bg=pal['canvas']);header.pack(fill='x',padx=S['6'],pady=(S['6'],S['4']))
  tk.Label(header,text='Очередь задач',bg=pal['canvas'],fg=pal['ink'],font=F['heading']).pack(side='left')
  tk.Button(header,text='Инструкция',bg=pal['surface'],fg=pal['muted'],font=F['small'],bd=0,
            highlightthickness=0,cursor='hand2',padx=10,pady=6,
            command=lambda:self.safe_open(ROOT/'README_RU.md')).pack(side='right')
  # --- Карточки статистики ---
  stats=tk.Frame(content,bg=pal['canvas']);stats.pack(fill='x',padx=S['6'],pady=(0,S['4']))
  for i in range(4):stats.columnconfigure(i,weight=1)
  self.stat_cards={}
  for idx,(key,label,accent) in enumerate([('total','Всего файлов','accent'),('pending','В очереди','info'),('done','Готово','success'),('errors','Ошибки','error')]):
   card=stat_card(stats,'0',label,pal,accent);card.grid(row=0,column=idx,padx=S['2'],sticky='ew')
   self.stat_cards[key]=card
  # --- Панель управления ---
  bar=tk.Frame(content,bg=pal['canvas']);bar.pack(fill='x',padx=S['6'],pady=(0,S['4']))
  left=tk.Frame(bar,bg=pal['canvas']);left.pack(side='left')
  tk.Button(left,text='Добавить файлы',bg=pal['surface'],fg=pal['ink'],font=F['ui'],bd=1,
            highlightbackground=pal['border'],highlightthickness=1,cursor='hand2',padx=14,pady=8,
            command=self.add_files).pack(side='left',padx=(0,S['2']))
  tk.Button(left,text='Добавить папку',bg=pal['surface'],fg=pal['ink'],font=F['ui'],bd=1,
            highlightbackground=pal['border'],highlightthickness=1,cursor='hand2',padx=14,pady=8,
            command=self.add_folder).pack(side='left',padx=(0,S['4']))
  tk.Button(left,text='Обработать очередь',bg=pal['accent_btn'],fg='#ffffff',font=F['ui_medium'],bd=0,
            highlightthickness=0,cursor='hand2',padx=18,pady=10,command=self.start).pack(side='left',padx=(0,S['2']))
  tk.Button(left,text='Стоп',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=14,pady=10,command=self.stop).pack(side='left')
  right=tk.Frame(bar,bg=pal['canvas']);right.pack(side='right')
  tk.Label(right,text='Режим:',bg=pal['canvas'],fg=pal['muted'],font=F['small']).pack(side='left',padx=(0,S['2']))
  self.mode=tk.StringVar(value={'short':'Короткая','long':'Длительная','photo':'Фото'}[self.cfg['mode']])
  cb=ttk.Combobox(left,textvariable=self.mode,values=['Короткая','Длительная','Фото'],state='readonly',width=12,font=F['ui'])
  cb.pack(side='left',padx=(0,S['4']));cb.bind('<<ComboboxSelected>>',lambda e:self.active_cfg())
  tk.Label(right,text='Профиль:',bg=pal['canvas'],fg=pal['muted'],font=F['small']).pack(side='left',padx=(S['4'],S['2']))
  self.profile=tk.StringVar(value=self.cfg['profile'])
  cb2=ttk.Combobox(left,textvariable=self.profile,values=list(PROFILES),state='readonly',width=10,font=F['ui'])
  cb2.pack(side='left');cb2.bind('<<ComboboxSelected>>',lambda e:self.active_cfg())
  tk.Button(left,text='Авто',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=12,pady=8,command=self.auto).pack(side='left',padx=(S['4'],0))
  # --- Фильтры ---
  filters=tk.Frame(content,bg=pal['canvas']);filters.pack(fill='x',padx=S['6'],pady=(0,S['4']))
  search_wrap=tk.Frame(filters,bg=pal['surface'],highlightbackground=pal['border'],highlightthickness=1,bd=0)
  search_wrap.pack(side='left',fill='x',expand=True,padx=(0,S['4']))
  tk.Label(search_wrap,text='🔍',bg=pal['surface'],fg=pal['muted']).pack(side='left',padx=(S['3'],0),pady=S['2'])
  self.search=tk.StringVar();entry=tk.Entry(search_wrap,textvariable=self.search,bg=pal['surface'],fg=pal['ink'],
    bd=0,highlightthickness=0,font=F['ui']);entry.pack(side='left',fill='x',expand=True,padx=(0,S['3']),pady=S['2'])
  entry.bind('<Return>',lambda e:self.find())
  tk.Button(filters,text='Найти',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=14,pady=8,command=self.find).pack(side='left',padx=(0,S['2']))
  self.state=tk.StringVar(value='Все статусы');self.filter_mode=tk.StringVar(value='Все сессии')
  statebox=ttk.Combobox(filters,textvariable=self.state,values=['Все статусы']+list(LABELS.values()),state='readonly',width=16,font=F['ui'])
  statebox.pack(side='left',padx=(0,S['2']));statebox.bind('<<ComboboxSelected>>',lambda e:self.find())
  mb=ttk.Combobox(filters,textvariable=self.filter_mode,values=['Все сессии','Короткая','Длительная'],state='readonly',width=14,font=F['ui'])
  mb.pack(side='left',padx=(0,S['2']));mb.bind('<<ComboboxSelected>>',lambda e:self.find())
  tk.Button(filters,text='Сброс',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=12,pady=8,command=self.clear_filter).pack(side='left')
  # --- Таблица задач ---
  table_wrap=make_card(content);table_wrap.pack(fill='both',expand=True,padx=S['6'],pady=(0,S['4']))
  table_inner=tk.Frame(table_wrap,bg=pal['surface']);table_inner.pack(fill='both',expand=True,padx=S['3'],pady=S['3'])
  cols=('name','mode','state','number','market','cursor','duration','hit_count','path')
  self.tree=ttk.Treeview(table_inner,columns=cols,show='headings',selectmode='extended')
  labels=['Файл','Сессия','Статус','Номер','Маркетплейс','Пройдено','Длительность','Этикеток','Путь к файлу']
  widths=[230,90,110,190,110,100,90,70,340]
  for col,label,width in zip(cols,labels,widths):
   self.tree.heading(col,text=label,command=lambda c=col:self.sort_by(c))
   self.tree.column(col,width=width,minwidth=65,stretch=col in ('name','path'))
  vs=ttk.Scrollbar(table_inner,orient='vertical',command=self.tree.yview);hs=ttk.Scrollbar(table_inner,orient='horizontal',command=self.tree.xview)
  self.tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
  self.tree.grid(row=0,column=0,sticky='nsew');vs.grid(row=0,column=1,sticky='ns');hs.grid(row=1,column=0,sticky='ew')
  table_inner.rowconfigure(0,weight=1);table_inner.columnconfigure(0,weight=1)
  for tag in STATE_THEME:self.tree.tag_configure(tag,background=STATE_THEME[tag][2])
  self.tree.bind('<Double-1>',self.double_click);self.tree.bind('<Control-c>',lambda e:self.copy_rows());self.tree.bind('<Control-C>',lambda e:self.copy_rows())
  self.tree.bind('<Control-a>',self.select_all);self.tree.bind('<Control-A>',self.select_all);self.tree.bind('<Button-3>',self.context)
  self.tree.bind('<<TreeviewSelect>>',lambda e:self.selection_changed())
  # --- Нижняя панель ---
  bottom=tk.Frame(content,bg=pal['canvas']);bottom.pack(fill='x',padx=S['6'],pady=(0,S['6']))
  nav=tk.Frame(bottom,bg=pal['canvas']);nav.pack(side='left')
  tk.Button(nav,text='←',bg=pal['surface'],fg=pal['ink'],font=F['ui'],bd=1,highlightbackground=pal['border'],
            highlightthickness=1,cursor='hand2',padx=10,pady=6,command=lambda:self.change_page(-1)).pack(side='left')
  self.page_label=tk.StringVar();tk.Label(nav,textvariable=self.page_label,bg=pal['canvas'],fg=pal['muted'],font=F['ui']).pack(side='left',padx=S['3'])
  tk.Button(nav,text='→',bg=pal['surface'],fg=pal['ink'],font=F['ui'],bd=1,highlightbackground=pal['border'],
            highlightthickness=1,cursor='hand2',padx=10,pady=6,command=lambda:self.change_page(1)).pack(side='left',padx=(S['3'],0))
  tk.Button(nav,text='Выделить страницу',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=10,pady=6,command=self.select_all).pack(side='left',padx=(S['4'],0))
  self.selected_label=tk.StringVar();tk.Label(nav,textvariable=self.selected_label,bg=pal['canvas'],fg=pal['muted'],font=F['ui']).pack(side='left',padx=(S['6'],0))
  # Путь к файлу
  pathbar=tk.Frame(bottom,bg=pal['canvas']);pathbar.pack(side='right')
  self.path_value=tk.StringVar();pathentry=tk.Entry(pathbar,textvariable=self.path_value,state='readonly',bg=pal['surface'],fg=pal['ink'],
    font=F['mono'],bd=1,highlightbackground=pal['border'],highlightthickness=1)
  pathentry.pack(side='left',padx=(0,S['3']))
  tk.Button(pathbar,text='К файлу',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=10,pady=6,command=self.reveal).pack(side='left',padx=(0,S['2']))
  tk.Button(pathbar,text='Копировать путь',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=10,pady=6,command=self.copy_paths).pack(side='left',padx=(0,S['2']))
  tk.Button(pathbar,text='Копировать файл',bg=pal['neutral_bg'],fg=pal['neutral_text'],font=F['ui'],bd=0,
            highlightthickness=0,cursor='hand2',padx=10,pady=6,command=self.copy_selected_files).pack(side='left')
  # Статус и лог
  self.status=tk.StringVar(value='Готово');tk.Label(content,textvariable=self.status,bg=pal['canvas'],fg=pal['muted'],font=F['small']).pack(fill='x',padx=S['6'],pady=(0,S['2']))
  self.log=tk.Text(content,height=5,wrap='word',state='disabled',bg=pal['surface'],fg=pal['ink'],insertbackground=pal['ink'],
                   bd=1,highlightbackground=pal['border'],highlightthickness=1);self.log.pack(fill='x',padx=S['6'],pady=(0,S['6']))
 def _nav_switch(self,key):
  self.nav_active.set(key)
  for k,btn in self.nav_buttons.items():
   if k==key:
    btn.configure(bg=self.theme['palette']['accent_soft'],fg=self.theme['palette']['accent_text'])
   else:
    btn.configure(bg=self.theme['palette']['surface'],fg=self.theme['palette']['muted'])
 def _toggle_theme(self):
  order=['light','dark','auto'];cur=self.theme_mode;nxt=order[(order.index(cur)+1)%len(order)]
  self.theme_mode=nxt;self.theme=apply_theme(self.root,nxt)
  pal=self.theme['palette'];self.theme_btn.configure(text='Тема: '+THEME_LABELS[nxt])
  self.refresh()
 def active_cfg(self):
  self.cfg['profile']=self.profile.get();self.cfg['mode']={'Короткая':'short','Длительная':'long','Фото':'photo'}[self.mode.get()];atomic_json(data_dir()/'settings-v2.json',self.cfg);return worker_config(self.cfg)
 def auto(self):
  profile,stats=auto_profile();self.profile.set(profile);self.active_cfg();self.status.set(f"Авто: {PROFILES[profile]['label']}; доступно RAM {stats['available_ram_gb']} ГБ, физических ядер {stats['physical_cores']}. Для новых заданий.")
 def add_files(self):
  paths=filedialog.askopenfilenames(parent=self.root,title='Выберите видео / изображения',filetypes=[('Видео и фото',' '.join('*'+e for e in sorted(EXTENSIONS))),('Все файлы','*.*')])
  if paths:
   if self.active_cfg()['mode']=='photo':self.open_photo_window(paths)
   else:self.import_paths(paths)
 def add_folder(self):
  folder=filedialog.askdirectory(parent=self.root)
  if folder:
   if self.active_cfg()['mode']=='photo':self.open_photo_window([folder])
   else:self.import_paths([folder])
 def open_photo_window(self,paths=None):
  if getattr(self,'photo_window',None) and self.photo_window.win.winfo_exists():
   self.photo_window.win.focus_set();return
  self.photo_window=PhotoWindow(self.root,theme=self.theme)
  if paths:
   self.photo_window.files=[Path(p) for p in paths if Path(p).suffix.lower() in EXTENSIONS]
   self.photo_window.count()
 def import_paths(self,values):
  cfg=self.active_cfg();recursive=self.cfg.get('recursive',True)
  def work():
   count=errors=0
   for value in values:
    p=Path(value)
    if p.is_dir():
     def candidates():
      for folder,dirs,files in os.walk(p,followlinks=False):
       dirs[:]=[d for d in dirs if not (Path(folder)/d).is_symlink()]
       for name in files:yield Path(folder)/name
       if not recursive:dirs.clear()
     iterable=candidates()
    else:iterable=[p]
    for file in iterable:
     if file.is_symlink() or not file.is_file() or file.suffix.lower() not in EXTENSIONS:continue
     try:_,new=self.store.add(file,cfg);count+=int(new)
     except Exception as exc:errors+=1;self.post('log',str(file)+': '+str(exc))
   return f'добавлено {count}, ошибок {errors}; профиль и шаг сохранены для каждого задания'
  self.background(work,'Добавление файлов')
 def start(self):
  if self.busy:messagebox.showinfo('SHIRA','Дождитесь завершения добавления / экспорта / резервного копирования',parent=self.root);return
  cfg=self.active_cfg()
  if cfg['mode']=='photo':return self.open_photo_window()
  self.engine.start(PROFILES[cfg['profile']]['workers']);self.status.set('Обработка очереди. Стоп сохраняет последнюю контрольную точку.')
 def stop(self):self.engine.stop();self.status.set('Остановка обработчиков…')
 def selected(self):return [key for key in self.tree.selection() if key in self.rows]
 def retry(self,reset=False):
  keys=self.selected()
  if not keys:return
  if self.engine.running():messagebox.showinfo('SHIRA','Сначала остановите обработку',parent=self.root);return
  if reset and not messagebox.askyesno('Переиндексация','Удалить текущие попадания выбранных заданий и начать сначала? Бэкап рекомендуется.',parent=self.root):return
  self.store.retry(keys,reset=reset);self.refresh();self.status.set(f'Возвращено в очередь: {len(keys)}. Нажмите «Обработать очередь».')
 def retry_gaps_ui(self):
  keys=self.selected()
  if not keys:messagebox.showinfo('SHIRA','Выделите задания, у которых нужно повторить пропуски',parent=self.root);return
  if self.engine.running():messagebox.showinfo('SHIRA','Сначала остановите обработку',parent=self.root);return
  try:self.store.retry_gaps(keys)
  except Exception as exc:messagebox.showerror('Повтор пропусков',str(exc),parent=self.root);return
  self.refresh();self.status.set(f'Пропуски вернены в очередь: {len(keys)}. Нажмите «Обработать очередь».')
 def find(self):self.page=0;self.refresh()
 def clear_filter(self):self.search.set('');self.state.set('Все статусы');self.filter_mode.set('Все сессии');self.find()
 def sort_by(self,col):
  if col==self.sort:self.desc=not self.desc
  else:self.sort=col;self.desc=False
  self.page=0;self.refresh()
 def change_page(self,delta):
  value=self.page+delta
  if value<0 or value*200>=self.total:return
  self.page=value;self.refresh()
 def refresh(self):
  keep=set(self.selected()) if hasattr(self,'tree') else set();state=next((k for k,v in LABELS.items() if v==self.state.get()),'');mode={'Короткая':'short','Длительная':'long'}.get(self.filter_mode.get(),'')
  rows,total=self.store.page(search=self.search.get(),state=state,mode=mode,sort=self.sort,descending=self.desc,page=self.page)
  if not rows and self.page and total:self.page=max(0,(total-1)//200);return self.refresh()
  self.total=total;self.rows={r['id']:r for r in rows};self.tree.delete(*self.tree.get_children())
  counts={'total':0,'pending':0,'done':0,'errors':0}
  for r in rows:
   counts['total']+=1;st=r['state']
   if st in ('pending','running','review','partial','accepted'):counts['pending']+=1
   if st in ('done',):counts['done']+=1
   if st in ('error',):counts['errors']+=1
   self.tree.insert('',tk.END,iid=r['id'],values=(r['name'],'Короткая' if r['mode']=='short' else 'Длительная',LABELS.get(r['state'],r['state']),r['number'] or ('См. индекс' if r['mode']=='long' else ''),r['market'],stamp(r['cursor']),stamp(r['duration']),r['hit_count'],r['path']),tags=(st,))
  for key in keep&self.rows.keys():self.tree.selection_add(key)
  self.page_label.set(f'Страница {self.page+1} / {max(1,(total+199)//200)} · файлов {total}');self.selection_changed();self.last_refresh=time.monotonic()
  pal=self.theme['palette']
  for key,label in [('total','Всего файлов'),('pending','В очереди'),('done','Готово'),('errors','Ошибки')]:
   card=self.stat_cards[key];card.winfo_children()[0].configure(text=str(counts[key]))
 def selection_changed(self):
  selected=self.selected();self.selected_label.set(f'Выбрано: {len(selected)}');self.path_value.set(self.rows[selected[0]]['path'] if selected else '')
 def select_all(self,event=None):self.tree.selection_set(self.tree.get_children());return 'break'
 def clipboard(self,text):self.root.clipboard_clear();self.root.clipboard_append(str(text));self.root.update_idletasks();self.status.set('Скопировано в буфер обмена');return 'break'
 def copy_rows(self):
  text='\n'.join('\t'.join(str(v) for v in self.tree.item(key,'values')) for key in self.selected());return self.clipboard(text)
 def copy_paths(self):return self.clipboard('\n'.join(self.rows[k]['path'] for k in self.selected()))
 def copy_numbers(self):return self.clipboard('\n'.join(self.rows[k]['number'] for k in self.selected() if self.rows[k]['number']))
 def copy_selected_files(self):
  try:kind=copy_files(self.root,[self.rows[k]['path'] for k in self.selected()]);self.status.set('Файлы скопированы. Вставьте Ctrl+V в письмо или папку.' if kind=='files' else 'Пути скопированы; системное копирование файлов реализовано для Windows.')
  except Exception as exc:messagebox.showerror('Копирование',str(exc),parent=self.root)
 def safe_open(self,path,select=False):
  try:open_path(path,select)
  except Exception as exc:messagebox.showerror('Файл',str(exc),parent=self.root)
 def reveal(self):
  keys=self.selected()
  if keys:self.safe_open(self.rows[keys[0]]['path'],True)
 def context(self,event):
  row=self.tree.identify_row(event.y)
  if row and row not in self.selected():self.tree.selection_set(row)
  menu=tk.Menu(self.root,tearoff=False)
  for label,fn in [('Проверить',self.review),('Копировать строки',self.copy_rows),('Копировать номера',self.copy_numbers),('Копировать пути',self.copy_paths),('Копировать файлы для письма',self.copy_selected_files),('Показать в папке',self.reveal),('Повторить выбранные',self.retry),('Повторить пропуски',self.retry_gaps_ui)]:menu.add_command(label=label,command=fn)
  menu.tk_popup(event.x_root,event.y_root)
 def double_click(self,event):
  if self.tree.identify_region(event.x,event.y) not in ('cell','tree'):return
  if self.tree.identify_column(event.x)=='#9':self.reveal()
  else:self.review()
 def bind_copy(self,window):
  def menu(event):
   widget=event.widget
   if isinstance(widget,(tk.Entry,ttk.Entry,tk.Text)):
    popup=tk.Menu(window,tearoff=False)
    for name,action in [('Копировать','<<Copy>>'),('Вставить','<<Paste>>'),('Вырезать','<<Cut>>')]:popup.add_command(label=name,command=lambda a=action,w=widget:w.event_generate(a))
    popup.add_command(label='Выделить всё',command=lambda:self.select_text(widget));popup.tk_popup(event.x_root,event.y_root)
  window.bind('<Button-3>',menu,add='+')
  # Физические клавиши C/V/X/A работают и в русской раскладке Windows.
  def key(event):
   w=event.widget
   if isinstance(w,ttk.Treeview):
    if event.keycode==67:return self.clipboard('\n'.join('\t'.join(str(x) for x in w.item(k,'values')) for k in w.selection()))
    if event.keycode==65:w.selection_set(w.get_children());return 'break'
   if not isinstance(w,(tk.Entry,ttk.Entry,tk.Text)):return
   action={67:'<<Copy>>',86:'<<Paste>>',88:'<<Cut>>'}.get(event.keycode)
   if action:w.event_generate(action);return 'break'
   if event.keycode==65:self.select_text(w);return 'break'
  if os.name=='nt':window.bind('<Control-KeyPress>',key,add='+')
 def select_text(self,widget):
  if isinstance(widget,tk.Text):widget.tag_add('sel','1.0','end-1c')
  else:widget.selection_range(0,'end');widget.icursor('end')
 def export(self):
  destination=filedialog.asksaveasfilename(parent=self.root,defaultextension='.xlsx',filetypes=[('Excel','*.xlsx'),('CSV','*.csv')])
  if destination:self.background(lambda:self.store.export(destination),'Экспорт')
 def backup(self):
  destination=filedialog.asksaveasfilename(parent=self.root,defaultextension='.sqlite3',filetypes=[('SQLite backup','*.sqlite3')])
  if destination:self.background(lambda:self.store.backup(destination),'Резервная копия')
 def poll(self):
  if self.closed:return
  changed=False
  for _ in range(70):
   try:kind,value=self.events.get_nowait()
   except queue.Empty:break
   if kind in ('log','error','notice'):
    self.log.configure(state='normal');self.log.insert('end',str(value)+'\n');lines=int(self.log.index('end-1c').split('.')[0])
    if lines>350:self.log.delete('1.0',f'{lines-300}.0')
    self.log.see('end');self.log.configure(state='disabled');self.status.set(str(value))
   elif kind=='background_done':self.busy=max(0,self.busy-1);changed=True
   elif kind=='changed':changed=True
   elif kind=='finished':changed=True;self.status.set('Обработка завершена / остановлена. Статусы пропусков сохранены.')
   elif kind=='progress':
    if value['id'] in self.rows:self.tree.set(value['id'],'cursor',stamp(value['cursor']));self.tree.set(value['id'],'duration',stamp(value['duration']))
    self.status.set('Обработка '+stamp(value['cursor'])+' / '+stamp(value['duration'])+' (контрольная точка сохраняется по окончании интервала)')
  if (changed and time.monotonic()-self.last_refresh>1) or time.monotonic()-self.last_refresh>5:self.refresh()
  self.root.after(150,self.poll)
 def scan_report(self):
  path=data_dir()/'logs'/'scan-v2.log'
  if not path.is_file():messagebox.showinfo('Отчёт сканирования','Отчёта пока нет: он создаётся после первой обработки короткой сессии.',parent=self.root);return
  self.safe_open(path)
 def preferences(self):
  win=tk.Toplevel(self.root);icon(win);win.title('Настройки новых заданий');win.geometry('980x900');win.minsize(860,560);win.resizable(True,True);self.bind_copy(win);center_window(win)
  canvas,frame=make_scrollable(win,bg=self.theme['palette']['surface_alt'])
  ttk.Label(frame,text='Изменения применяются к новым заданиям. Уже добавленные используют сохранённые настройки.').pack(anchor='w')
  ttk.Label(frame,text='Тема оформления:').pack(anchor='w',pady=(10,0));theme_var=tk.StringVar(value=self.cfg.get('theme',DEFAULT_THEME));ttk.Combobox(frame,textvariable=theme_var,values=['light','dark','auto'],state='readonly',width=12).pack(anchor='w')
  ttk.Label(frame,text='Шаг поиска QR в длинном видео, секунд (0.1–60):').pack(anchor='w',pady=(10,0));step=tk.StringVar(value=str(self.cfg['long_step']));ttk.Entry(frame,textvariable=step).pack(fill='x')
  ttk.Label(frame,text='OCR на каждом N-м выбранном кадре (1 — весь шаг, медленнее):').pack(anchor='w');every=tk.StringVar(value=str(self.cfg['long_ocr_every']));ttk.Entry(frame,textvariable=every).pack(fill='x')
  ttk.Label(frame,text='Языки OCR:').pack(anchor='w');lang=tk.StringVar(value=self.cfg['language']);ttk.Combobox(frame,textvariable=lang,values=['rus+eng','eng','rus'],state='readonly').pack(fill='x')
  recursive=tk.BooleanVar(value=self.cfg.get('recursive',True));ttk.Checkbutton(frame,text='Добавлять вложенные папки',variable=recursive).pack(anchor='w')
  box=ttk.LabelFrame(frame,text='Короткая сессия (0 = брать из профиля ПК)',padding=8);box.pack(fill='x',pady=(10,0))
  sf=tk.StringVar(value=str(self.cfg.get('short_frames',0)));so=tk.StringVar(value=str(self.cfg.get('short_ocr_frames',0)));fm=tk.StringVar(value=str(self.cfg.get('qr_text_fallback_max',12)))
  ws=tk.StringVar(value=str(self.cfg.get('short_start',0.0)));we=tk.StringVar(value=str(self.cfg.get('short_end',0.0)))
  fb=tk.BooleanVar(value=self.cfg.get('qr_text_fallback',True));st=tk.BooleanVar(value=self.cfg.get('qr_strong_ocr',True));fz=tk.BooleanVar(value=self.cfg.get('fuzzy_841',True));sp=tk.BooleanVar(value=self.cfg.get('short_second_pass',True))
  ttk.Label(box,text='Кадров на видео для поиска QR (0 или 4–120):').grid(row=0,column=0,sticky='w');ttk.Entry(box,textvariable=sf,width=8).grid(row=0,column=1,padx=6,pady=2)
  ttk.Label(box,text='Кадров с OCR текста этикетки (0 или 1–120):').grid(row=1,column=0,sticky='w');ttk.Entry(box,textvariable=so,width=8).grid(row=1,column=1,padx=6,pady=2)
  ttk.Label(box,text='Сканировать с секунды (0 = с начала видео):').grid(row=2,column=0,sticky='w');ttk.Entry(box,textvariable=ws,width=8).grid(row=2,column=1,padx=6,pady=2)
  ttk.Label(box,text='Сканировать до секунды (0 = до конца видео):').grid(row=3,column=0,sticky='w');ttk.Entry(box,textvariable=we,width=8).grid(row=3,column=1,padx=6,pady=2)
  ttk.Label(box,text='Кадры равномерно распределяются внутри этого промежутка; хвост видео (~0.15 с) всегда отбрасывается.',foreground=self.theme['palette']['muted']).grid(row=4,column=0,columnspan=2,sticky='w')
  ttk.Checkbutton(box,text='Если трек не найден — второй проход по промежуточным кадрам (медленнее, надёжнее)',variable=sp).grid(row=5,column=0,columnspan=2,sticky='w')
  ttk.Checkbutton(box,text='Если QR найден, а трека в нём нет — дочитывать текст этикетки (OCR)',variable=fb).grid(row=6,column=0,columnspan=2,sticky='w')
  ttk.Label(box,text='Максимум таких дополнительных кадров с OCR на видео (0–60):').grid(row=7,column=0,sticky='w');ttk.Entry(box,textvariable=fm,width=8).grid(row=7,column=1,padx=6,pady=2)
  ttk.Checkbutton(box,text='Усиленный OCR вокруг QR (медленнее, лучше читает мелкий текст)',variable=st).grid(row=8,column=0,columnspan=2,sticky='w')
  ttk.Checkbutton(box,text='Распознавать номера 10-4-1 с типичными ошибками OCR (О/0, l/1; такие номера идут на проверку)',variable=fz).grid(row=9,column=0,columnspan=2,sticky='w')
  ttk.Button(box,text='Открыть отчёт сканирования (scan-v2.log)',command=self.scan_report).grid(row=10,column=0,columnspan=2,sticky='w',pady=(6,0))
  ttk.Label(frame,text='Шаблоны JSON (regex, name, market).').pack(anchor='w',pady=(10,0))
  text=tk.Text(frame,height=12,wrap='word',bg=self.theme['palette']['surface'],fg=self.theme['palette']['ink'],insertbackground=self.theme['palette']['ink']);text.pack(fill='both',expand=True);text.insert('1.0',json.dumps(self.cfg['patterns'],ensure_ascii=False,indent=2))
  def save():
   try:
    s=float(step.get());n=int(every.get());p=json.loads(text.get('1.0','end'))
    sfv=int(sf.get() or 0);sov=int(so.get() or 0);fmv=int(fm.get() or 0)
    wsv=float((ws.get() or '0').replace(',','.'));wev=float((we.get() or '0').replace(',','.'))
    if not .1<=s<=60 or not 1<=n<=100:raise ValueError('Проверьте диапазоны шага и N')
    if sfv and not 4<=sfv<=120:raise ValueError('Кадров для QR: 0 или 4–120')
    if sov and not 1<=sov<=120:raise ValueError('Кадров с OCR: 0 или 1–120')
    if not 0<=fmv<=60:raise ValueError('Дополнительных кадров с OCR: 0–60')
    if wsv!=wsv or wev!=wev or wsv<0 or wev<0:raise ValueError('Окно сканирования: секунды не могут быть отрицательными')
    if wev and wev<=wsv:raise ValueError('Окно сканирования: «до» должно быть больше «с» (или 0 — до конца)')
    if not isinstance(p,list) or not 1<=len(p)<=30:raise ValueError('Нужен список из 1–30 шаблонов')
    for item in p:
     if not isinstance(item,dict) or not isinstance(item.get('regex'),str) or len(item['regex'])>300:raise ValueError('Некорректный шаблон')
     re.compile(item['regex'])
    self.cfg.update(long_step=s,long_ocr_every=n,patterns=p,language=lang.get(),recursive=recursive.get(),short_frames=sfv,short_ocr_frames=sov,short_start=wsv,short_end=wev,short_second_pass=sp.get(),qr_text_fallback=fb.get(),qr_text_fallback_max=fmv,qr_strong_ocr=st.get(),fuzzy_841=fz.get(),theme=theme_var.get());self.theme_mode=theme_var.get();self.theme=apply_theme(self.root,self.theme_mode);self.log.configure(bg=self.theme['palette']['surface'],fg=self.theme['palette']['ink']);self.refresh();self.active_cfg();win.destroy()
   except Exception as exc:messagebox.showerror('Настройки',str(exc),parent=win)
  ttk.Button(frame,text='Сохранить',command=save).pack(pady=8)
  def legacy():
   path=filedialog.askopenfilename(parent=win,title='База предыдущего MVP jobs.sqlite3',filetypes=[('SQLite','*.sqlite3 *.db'),('Все','*.*')])
   if path:
    from legacy_import import import_legacy
    self.background(lambda:import_legacy(self.store,path),'Импорт результатов v1')
  ttk.Button(frame,text='Импортировать результаты предыдущего MVP',command=legacy).pack(pady=4)
 def fetch_frame(self,win,video,ts,done):
  # Извлекает кадр из исходного видео в отдельном процессе; done(path|None, сообщение).
  fd,out=tempfile.mkstemp(suffix='.jpg',prefix='shira-frame-');os.close(fd)
  command=[sys.executable,str(ROOT/'tools/frame_preview.py'),str(video),str(ts),out]
  proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0);deadline=time.monotonic()+25
  def drop():Path(out).unlink(missing_ok=True)
  def poll():
   if not win.winfo_exists():
    if proc.poll() is None:
     from recognition import kill_tree
     kill_tree(proc.pid)
    drop();return
   if proc.poll() is None:
    if time.monotonic()>deadline:
     from recognition import kill_tree
     kill_tree(proc.pid);drop();done(None,'Тайм-аут извлечения кадра');return
    win.after(150,poll);return
   if proc.returncode==0 and Path(out).is_file() and Path(out).stat().st_size>0:done(out,'')
   else:drop();done(None,'Не удалось прочитать кадр. Возможно, исходник перемещён или кодек не поддержан.')
  win.after(150,poll)
 def review(self):
  keys=self.selected()
  if not keys:return
  key=keys[0];row=self.store.get(key)
  if row['mode']=='long':self.index(key);return
  win=tk.Toplevel(self.root);icon(win);win.title('Проверка: '+row['name']);win.geometry('1180x920');win.minsize(960,700);win.resizable(True,True);self.bind_copy(win);center_window(win)
  pal=self.theme['palette']
  frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
  path=tk.StringVar(value=row['path']);ttk.Entry(frame,textvariable=path,state='readonly').pack(fill='x')
  buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=5)
  ttk.Button(buttons,text='К файлу',command=lambda:self.safe_open(row['path'],True)).pack(side='left');ttk.Button(buttons,text='Копировать путь',command=lambda:self.clipboard(row['path'])).pack(side='left',padx=4)
  def cf():
   try:copy_files(self.root,[row['path']]);self.status.set('Файл скопирован для вставки')
   except Exception as exc:messagebox.showerror('Файл',str(exc),parent=win)
  ttk.Button(buttons,text='Копировать файл для письма',command=cf).pack(side='left');ttk.Button(buttons,text='Открыть видео',command=lambda:self.safe_open(row['path'])).pack(side='left',padx=4)
  info=ttk.Entry(frame,state='normal');info.insert(0,LABELS[row['state']]+' · '+row['detail']);info.configure(state='readonly');info.pack(fill='x')
  shown={'path':row['evidence'] or '','temp':None}
  image_label=ttk.Label(frame,text='Кадр не сохранён');image_label.pack(fill='both',expand=True,pady=8)
  def show():
   if shown['path']:self.load_image(image_label,shown['path'],(1050,560),self.rot.get(key))
  def turn(delta):
   self.rot.add(key,delta);show()
  tools=ttk.Frame(frame);tools.pack(fill='x')
  for label,delta in [('↺ 90°',-90),('↻ 90°',90),('180°',180)]:ttk.Button(tools,text=label,command=lambda d=delta:turn(d)).pack(side='left',padx=2)
  ttk.Button(tools,text='Кадр крупно',command=lambda:FullImage(self,win,shown['path'],key)).pack(side='left',padx=8)
  hits,total=self.store.hits(key);text=tk.Text(frame,height=5,wrap='word',bg=pal['surface'],fg=pal['ink'],insertbackground=pal['ink']);text.pack(fill='x',pady=(8,0))
  for hit in hits:text.insert('end',f"{hit['number']} · {hit['market']} · {stamp(hit['ts'])} · {hit['method']}\n")
  text.configure(state='disabled')
  if shown['path'] and Path(shown['path']).is_file():show()
  else:
   shown['path']='';gaps=self.store.gaps(key);ts=hits[0]['ts'] if hits else (gaps[0]['start'] if gaps else 0)
   image_label.configure(text='Извлекаю кадр из видео…')
   def done(frame_path,message):
    if frame_path:shown['path']=frame_path;shown['temp']=frame_path;show()
    else:image_label.configure(text=message)
   self.fetch_frame(win,row['path'],ts,done)
  win.bind('<Destroy>',lambda e:Path(shown['temp']).unlink(missing_ok=True) if e.widget is win and shown['temp'] else None)
  edit=ttk.Frame(frame);edit.pack(fill='x',pady=6);ttk.Label(edit,text='Номер:').pack(side='left');number=tk.StringVar(value=row['number']);ttk.Entry(edit,textvariable=number,width=40).pack(side='left',padx=4);market=tk.StringVar(value=row['market']);ttk.Entry(edit,textvariable=market,width=22).pack(side='left')
  def confirm():
   try:self.store.confirm(key,number.get(),market.get());self.refresh();win.destroy()
   except Exception as exc:messagebox.showerror('Проверка',str(exc),parent=win)
  foot=ttk.Frame(frame);foot.pack(fill='x');ttk.Button(foot,text='Подтвердить номер',command=confirm).pack(side='left');ttk.Button(foot,text='История',command=lambda:self.history(key)).pack(side='left',padx=4);ttk.Button(foot,text='Индекс / все кадры',command=lambda:self.index(key)).pack(side='left');ttk.Button(foot,text='Закрыть',command=win.destroy).pack(side='right')
 def load_image(self,label,path,size,angle=0):
  if not path or not Path(path).is_file():return
  try:
   from PIL import ImageTk
   im=render_image(path,angle,size)
   label._photo=ImageTk.PhotoImage(im);label.configure(image=label._photo,text='')
  except Exception as exc:label.configure(text='Ошибка кадра: '+str(exc))
 def history(self,key):
  pal=self.theme['palette']
  win=tk.Toplevel(self.root);icon(win);win.title('История и пропуски');win.geometry('980x700');win.minsize(760,520);win.resizable(True,True);self.bind_copy(win);center_window(win)
  text=tk.Text(win,wrap='word',bg=pal['surface'],fg=pal['ink'],insertbackground=pal['ink']);text.pack(fill='both',expand=True)
  text.insert('end',json.dumps(dict(gaps=self.store.gaps(key),audit=self.store.history(key)),ensure_ascii=False,indent=2));text.configure(state='disabled')
 def index(self,key=None):
  IndexWindow(self,key)
 def close(self):
  if self.busy:messagebox.showinfo('SHIRA','Дождитесь завершения добавления / экспорта / резервного копирования',parent=self.root);return
  if self.engine.running():
   if not messagebox.askyesno('Выход','Остановить обработку и выйти? Незавершённый интервал будет обработан заново.',parent=self.root):return
   self.engine.stop()
   def wait():
    if self.engine.running():self.root.after(200,wait)
    else:self.finish_close()
   wait()
  else:self.finish_close()
 def finish_close(self):self.closed=True;self.root.destroy()

class FullImage:
 # Кадр в полном размере с прокруткой и поворотом: так читаются мелкие символы.
 def __init__(self,app,parent,path,key):
  if not path or not Path(path).is_file():messagebox.showinfo('SHIRA','Кадр ещё не загружен',parent=parent);return
  self.app=app;self.path=path;self.key=key;win=self.win=tk.Toplevel(parent);icon(win);win.title('Кадр в полном размере');win.geometry('1280x860');win.minsize(900,640);win.resizable(True,True);center_window(win)
  bar=ttk.Frame(win,padding=6);bar.pack(fill='x')
  for label,delta in [('↺ 90°',-90),('↻ 90°',90),('180°',180)]:ttk.Button(bar,text=label,command=lambda d=delta:self.turn(d)).pack(side='left',padx=2)
  ttk.Button(bar,text='Открыть во внешней программе',command=lambda:app.safe_open(self.path)).pack(side='left',padx=8)
  box=ttk.Frame(win);box.pack(fill='both',expand=True)
  self.canvas=tk.Canvas(box,background=self.app.theme['palette']['surface'],highlightthickness=0);vs=ttk.Scrollbar(box,orient='vertical',command=self.canvas.yview);hs=ttk.Scrollbar(box,orient='horizontal',command=self.canvas.xview)
  self.canvas.configure(yscrollcommand=vs.set,xscrollcommand=hs.set);self.canvas.grid(row=0,column=0,sticky='nsew');vs.grid(row=0,column=1,sticky='ns');hs.grid(row=1,column=0,sticky='ew');box.rowconfigure(0,weight=1);box.columnconfigure(0,weight=1)
  self.draw()
 def draw(self):
  try:
   from PIL import ImageTk
   im=render_image(self.path,self.app.rot.get(self.key),None);self.photo=ImageTk.PhotoImage(im)
   self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo);self.canvas.configure(scrollregion=(0,0,im.width,im.height))
  except Exception as exc:messagebox.showerror('Кадр','Не удалось показать кадр: '+str(exc),parent=self.win)
 def turn(self,delta):
  self.app.rot.add(self.key,delta);self.draw()

class IndexWindow:
 SIZE=(1250,480)
 def __init__(self,app,key):
  self.app=app;self.key=key;self.page=0;self.sort='ts';self.desc=False;self.rows={};self.temp=None;self.current=None;self.fetching=False
  win=self.win=tk.Toplevel(app.root);icon(win);win.title('Индекс этикеток — поиск и таймкоды');win.geometry('1360x980');win.minsize(1100,760);win.resizable(True,True);app.bind_copy(win);center_window(win);win.protocol('WM_DELETE_WINDOW',self.close)
  frame=ttk.Frame(win,padding=10);frame.pack(fill='both',expand=True);bar=ttk.Frame(frame);bar.pack(fill='x')
  self.query=tk.StringVar(value=app.search.get());ttk.Label(bar,text='Трек:').pack(side='left');entry=ttk.Entry(bar,textvariable=self.query,width=36);entry.pack(side='left',padx=4);entry.bind('<Return>',lambda e:self.search());ttk.Button(bar,text='Найти',command=self.search).pack(side='left');ttk.Button(bar,text='←',command=lambda:self.change(-1)).pack(side='left',padx=4);ttk.Button(bar,text='→',command=lambda:self.change(1)).pack(side='left');self.info=tk.StringVar();ttk.Label(bar,textvariable=self.info).pack(side='left',padx=8)
  cols=('number','ts','method','state','name','path');self.tree=ttk.Treeview(frame,columns=cols,show='headings',height=8,selectmode='extended')
  for col,label,width in zip(cols,['Номер','Время','Источник','Проверка','Видео','Путь'],[190,110,150,120,220,350]):self.tree.heading(col,text=label,command=lambda c=col:self.sort_by(c));self.tree.column(col,width=width)
  self.tree.pack(fill='x',pady=7);self.tree.bind('<<TreeviewSelect>>',lambda e:self.select());self.tree.bind('<Control-c>',self.copy);self.tree.bind('<Control-a>',lambda e:self.tree.selection_set(self.tree.get_children()));self.tree.bind('<Double-1>',lambda e:self.preview())
  actions=ttk.Frame(frame);actions.pack(fill='x')
  for label,fn in [('Кадр по таймкоду',self.preview),('Открыть видео',self.open_video),('К файлу',self.reveal),('Копировать строки',self.copy),('Копировать путь',self.copy_path),('Подтвердить трек',self.confirm),('Сводка',self.summary)]:ttk.Button(actions,text=label,command=fn).pack(side='left',padx=2)
  view=ttk.Frame(frame);view.pack(fill='x',pady=(6,0))
  for label,delta in [('↺ 90°',-90),('↻ 90°',90),('180°',180)]:ttk.Button(view,text=label,command=lambda d=delta:self.turn(d)).pack(side='left',padx=2)
  ttk.Button(view,text='Кадр крупно',command=self.full).pack(side='left',padx=8)
  self.path=tk.StringVar();ttk.Entry(frame,textvariable=self.path,state='readonly').pack(fill='x',pady=5)
  self.image=ttk.Label(frame,text='Выберите этикетку. Двойной щелчок — кадр на её таймкоде.');self.image.pack(fill='both',expand=True)
  ttk.Label(frame,text='Время — позиция выбранного кадра, не точные границы появления этикетки. Поиск показывает наблюдения, а не гарантированный список всех посылок.').pack(fill='x')
  if key:ttk.Button(frame,text='Пропуски и история этого видео',command=lambda:app.history(key)).pack(anchor='w')
  self.refresh()
 def sort_by(self,col):
  if self.sort==col:self.desc=not self.desc
  else:self.sort=col;self.desc=False
  self.page=0;self.refresh()
 def summary(self):
  pal=self.app.theme['palette']
  rows=self.app.store.summary(self.key,self.query.get());win=tk.Toplevel(self.win);icon(win);win.title('Сводка: первые / последние наблюдения');win.geometry('1080x620');win.minsize(860,480);win.resizable(True,True);self.app.bind_copy(win);center_window(win)
  text=tk.Text(win,wrap='none',bg=pal['surface'],fg=pal['ink'],insertbackground=pal['ink']);text.pack(fill='both',expand=True)
  text.insert('end','Номер\tПервое наблюдение\tПоследнее наблюдение\tКадров\tВидео\n')
  for r in rows:text.insert('end',f"{r['number']}\t{stamp(r['first_seen'])}\t{stamp(r['last_seen'])}\t{r['samples']}\t{r['path']}\n")
  text.insert('end','\nДо 200 групп на экране. Сводка не определяет количество посылок и точные границы появления. Для всех наблюдений используйте экспорт.');text.configure(state='disabled')
 def search(self):self.page=0;self.refresh()
 def refresh(self):
  rows,total=self.app.store.hits(self.key,self.query.get(),self.page,self.sort,self.desc);self.rows={str(r['id']):r for r in rows};self.total=total;self.tree.delete(*self.tree.get_children())
  for r in rows:self.tree.insert('',tk.END,iid=str(r['id']),values=(r['number'],stamp(r['ts']),r['method'],LABELS.get(r['state'],r['state']),r['name'],r['path']))
  self.info.set(f'Наблюдений {total}, страница {self.page+1}')
 def change(self,delta):
  if 0<=self.page+delta<max(1,(self.total+199)//200):self.page+=delta;self.refresh()
 def selected(self):
  keys=self.tree.selection();return self.rows.get(keys[0]) if keys else None
 def show(self,path,task_id):
  self.current=(path,task_id);self.app.load_image(self.image,path,self.SIZE,self.app.rot.get(task_id))
 def select(self):
  r=self.selected()
  if r:
   self.path.set(r['path'])
   if r['evidence'] and Path(r['evidence']).is_file():self.show(r['evidence'],r['task_id'])
 def turn(self,delta):
  if not self.current:return
  path,task_id=self.current
  if not Path(path).is_file():return
  self.app.rot.add(task_id,delta);self.show(path,task_id)
 def full(self):
  if self.current:FullImage(self.app,self.win,self.current[0],self.current[1])
  else:messagebox.showinfo('SHIRA','Сначала выберите этикетку',parent=self.win)
 def copy(self,event=None):return self.app.clipboard('\n'.join('\t'.join(str(x) for x in self.tree.item(k,'values')) for k in self.tree.selection()))
 def copy_path(self):
  r=self.selected()
  if r:self.app.clipboard(r['path'])
 def reveal(self):
  r=self.selected()
  if r:self.app.safe_open(r['path'],True)
 def open_video(self):
  r=self.selected()
  if r:self.app.safe_open(r['path'])
 def confirm(self):
  r=self.selected()
  if not r:return
  from tkinter.simpledialog import askstring
  number=askstring('Подтверждение','Номер этикетки:',initialvalue=r['number'],parent=self.win)
  if number:
   try:self.app.store.confirm(r['task_id'],number,r['market'],r['id']);self.refresh();self.app.refresh()
   except Exception as exc:messagebox.showerror('Подтверждение',str(exc),parent=self.win)
 def preview(self):
  r=self.selected()
  if not r or self.fetching:return
  self.fetching=True;self.info.set('Извлечение кадра…')
  def done(path,message):
   self.fetching=False
   if path:
    self.drop_temp();self.temp=Path(path);self.show(path,r['task_id']);self.info.set('Кадр на выбранном таймкоде')
   else:self.info.set(message)
  self.app.fetch_frame(self.win,r['path'],r['ts'],done)
 def drop_temp(self):
  if self.temp:self.temp.unlink(missing_ok=True);self.temp=None
 def close(self):
  self.drop_temp();self.win.destroy()

def center_window(win):
 try:
  win.update_idletasks()
  w=win.winfo_width();h=win.winfo_height()
  x=max(0,(win.winfo_screenwidth()-w)//2);y=max(0,(win.winfo_screenheight()-h)//2)
  win.geometry(f'+{x}+{y}')
  win.attributes('-alpha',0)
  def fade(step=0):
   if not win.winfo_exists():return
   step+=1
   win.attributes('-alpha',min(1,step/12))
   if step<12:win.after(16,lambda:fade(step))
  win.after(20,fade)
 except Exception:pass

def enable_dpi():
 if os.name!='nt':return
 import ctypes
 try:ctypes.windll.shcore.SetProcessDpiAwareness(2)
 except Exception:
  try:ctypes.windll.user32.SetProcessDPIAware()
  except Exception:pass

def main():
 app_identity();lock=AppLock()
 try:
  lock.acquire();enable_dpi();root=tk.Tk()
  try:root.tk.call('tk','scaling',root.winfo_fpixels('1i')/72.0)
  except tk.TclError:pass
  Application(root,Store());root.mainloop()
 finally:lock.close()
if __name__=='__main__':multiprocessing.freeze_support();main()
