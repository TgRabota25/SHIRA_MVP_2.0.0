"""Unified SHIRA editor UI with a distinct local icon for every action."""
import logging,sys
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.ui')
BG='#002B36';PANEL='#073642';FIELD='#03313D';BUTTON='#124654';TEXT='#E3EDF0';MUTED='#A6BDC5';ACCENT='#1687A7'

def caption(win):
    if sys.platform!='win32':return
    try:
        import ctypes
        from ctypes import wintypes
        u=ctypes.WinDLL('user32');d=ctypes.WinDLL('dwmapi')
        u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];u.GetAncestor.restype=wintypes.HWND
        d.DwmSetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        d.DwmSetWindowAttribute.restype=ctypes.c_long
        hwnd=u.GetAncestor(win.winfo_id(),2) or win.winfo_id()
        for key,value in [(20,1),(35,0x00423607),(36,0x00F0EDE3),(34,0x00544612)]:
            data=wintypes.DWORD(value);d.DwmSetWindowAttribute(hwnd,key,ctypes.byref(data),4)
    except Exception:LOG.exception('Caption styling failed')

def icon_image(root,kind,disabled=False):
    from PIL import Image,ImageDraw,ImageTk
    unit=max(1.0,root.winfo_fpixels('1i')/96)
    size=max(20,round(20*unit));gap=max(7,round(7*unit));scale=4
    im=Image.new('RGBA',(24*scale,24*scale));d=ImageDraw.Draw(im)
    color='#718F99' if disabled else '#E3EDF0'
    def line(points):d.line([(x*scale,y*scale) for x,y in points],fill=color,width=2*scale,joint='curve')
    def box(rect):d.rectangle(tuple(v*scale for v in rect),outline=color,width=2*scale)
    def ellipse(rect):d.ellipse(tuple(v*scale for v in rect),outline=color,width=2*scale)
    def arc(rect,start,end):d.arc(tuple(v*scale for v in rect),start,end,fill=color,width=2*scale)
    if kind=='file':
        line([(5,3),(14,3),(19,8),(19,21),(5,21),(5,3)]);line([(14,3),(14,8),(19,8)]);line([(9,14),(15,14)]);line([(12,11),(12,17)])
    elif kind=='folder':line([(3,6),(10,6),(12,9),(21,9),(21,20),(3,20),(3,6)])
    elif kind=='folder_open':line([(3,7),(9,7),(11,10),(21,10),(21,20),(3,20),(3,7)]);line([(6,13),(18,13)])
    elif kind=='play':line([(7,4),(20,12),(7,20),(7,4)])
    elif kind=='stop':box((6,6,18,18))
    elif kind=='search':ellipse((3,3,16,16));line([(16,16),(22,22)])
    elif kind=='export':line([(12,3),(12,16),(7,11)]);line([(12,16),(17,11)]);line([(4,16),(4,21),(20,21),(20,16)])
    elif kind=='settings':
        for y,x in [(5,8),(12,16),(19,10)]:line([(3,y),(21,y)]);box((x-2,y-3,x+2,y+3))
    elif kind=='auto':line([(14,2),(5,14),(11,14),(9,22),(20,9),(13,9),(14,2)])
    elif kind=='info':ellipse((3,3,21,21));line([(12,10),(12,17)]);ellipse((11,6,13,8))
    elif kind=='database':ellipse((3,4,21,10));line([(3,7),(3,17)]);line([(21,7),(21,17)]);arc((3,14,21,20),0,180)
    elif kind=='redo':arc((4,4,20,20),300,180);line([(17,3),(17,10),(10,10)])
    elif kind=='gaps':line([(4,4),(20,4)]);line([(4,12),(9,12)]);line([(15,12),(20,12)]);line([(4,20),(20,20)])
    elif kind=='restart':arc((4,4,20,20),120,420);line([(4,3),(4,10),(11,10)])
    elif kind=='tag':line([(3,12),(12,3),(21,12),(12,21),(3,12)]);ellipse((9,9,13,13))
    elif kind=='select_all':box((3,3,21,21));line([(7,12),(11,16),(18,7)])
    elif kind=='link':ellipse((3,9,13,19));ellipse((11,5,21,15));line([(8,16),(16,8)])
    elif kind=='file_copy':box((8,7,20,21));line([(15,4),(4,4),(4,17)])
    elif kind=='table_copy':box((3,3,21,21));line([(3,9),(21,9)]);line([(3,15),(21,15)]);line([(12,9),(12,21)])
    elif kind=='video':box((3,5,21,19));line([(10,9),(16,12),(10,15),(10,9)])
    elif kind=='history':arc((4,4,20,20),90,360);line([(12,7),(12,13),(17,16)]);line([(4,3),(4,10),(11,10)])
    elif kind=='summary':line([(4,4),(20,4)]);line([(4,10),(16,10)]);line([(4,16),(12,16)]);line([(17,14),(21,18)]);line([(21,14),(17,18)])
    elif kind=='save':line([(4,3),(17,3),(20,6),(20,21),(4,21),(4,3)]);box((8,13,16,21));line([(8,3),(8,10),(16,10),(16,3)])
    elif kind=='close':line([(6,6),(18,18)]);line([(18,6),(6,18)])
    elif kind=='cancel':ellipse((3,3,21,21));line([(8,8),(16,16)]);line([(16,8),(8,16)])
    elif kind=='continue':line([(5,4),(17,12),(5,20),(5,4)])
    elif kind=='check':line([(4,12),(10,18),(21,5)])
    elif kind=='confirm_number':box((3,3,21,21));line([(7,12),(11,16),(18,7)]);line([(7,20),(17,20)])
    elif kind=='confirm_track':ellipse((3,3,21,21));line([(7,12),(11,16),(18,7)])
    elif kind=='delete':line([(4,6),(20,6)]);line([(9,3),(15,3)]);line([(6,6),(7,21),(17,21),(18,6)]);line([(10,10),(10,17)]);line([(14,10),(14,17)])
    elif kind=='frame':box((3,3,21,21));line([(3,8),(8,8),(8,3)]);line([(16,3),(16,8),(21,8)]);line([(21,16),(16,16),(16,21)]);line([(8,21),(8,16),(3,16)])
    elif kind=='grid':
        for y in (4,11,18):
            for x in (4,11,18):box((x,y,x+2,y+2))
    elif kind=='import':line([(12,21),(12,8),(7,13)]);line([(12,8),(17,13)]);line([(4,3),(20,3),(20,7)])
    elif kind=='report':line([(5,3),(14,3),(19,8),(19,21),(5,21),(5,3)]);line([(14,3),(14,8),(19,8)]);line([(8,12),(16,12)]);line([(8,16),(16,16)])
    elif kind=='left':line([(15,4),(7,12),(15,20)])
    elif kind=='right':line([(9,4),(17,12),(9,20)])
    elif kind=='list':
        for y in (5,12,19):line([(4,y),(5,y)]);line([(9,y),(21,y)])
    else:line([(19,9),(17,5),(12,3),(6,5),(3,11),(5,18),(12,21),(19,18)]);line([(19,3),(19,9),(13,9)])
    raster=Image.new('RGBA',(size+gap,size))
    raster.paste(im.resize((size,size),Image.Resampling.LANCZOS),(0,0))
    return ImageTk.PhotoImage(raster,master=root)

MAPPING={
 'Добавить файлы':'file','Добавить папку':'folder','Обработать очередь':'play','Стоп':'stop','Найти':'search','Экспорт':'export','Настройки / шаблоны':'settings','Авто':'auto','Инструкция':'info','Бэкап БД':'database','Повторить выбранные':'redo','Повторить пропуски':'gaps','Сначала / переиндексировать':'restart','Индекс этикеток':'tag','Выделить страницу':'select_all','К файлу':'folder_open','Копировать путь':'link','Копировать файл':'file_copy','Копировать строки':'table_copy','Копировать файл для письма':'file_copy','Открыть видео':'video','История':'history','Сводка':'summary','Сохранить':'save','Закрыть':'close','Отмена':'cancel','Продолжить':'continue','Подтвердить номер':'confirm_number','Подтвердить трек':'confirm_track','Удалить…':'delete','Кадр крупно':'frame','Индекс / все кадры':'grid','Импортировать результаты предыдущего MVP':'import','Открыть отчёт сканирования (scan-v2.log)':'report'}

def apply(root):
    root._studio_font=font.Font(root=root,family='Segoe UI',size=11)
    f=root._studio_font;s=ttk.Style(root)
    if 'shira_editor_v3' not in s.theme_names():s.theme_create('shira_editor_v3',parent='clam')
    s.theme_use('shira_editor_v3');s.configure('.',font=f,background=BG,foreground=TEXT)
    for name in ('TFrame','TLabel','TCheckbutton','TRadiobutton','TLabelframe','TLabelframe.Label'):s.configure(name,background=BG,foreground=TEXT,font=f)
    s.configure('TLabelframe',borderwidth=0,relief='flat')
    s.configure('TButton',background=BUTTON,foreground=TEXT,font=f,padding=(10,4),borderwidth=1,bordercolor=BUTTON,lightcolor=BUTTON,darkcolor=BUTTON,relief='flat',anchor='center')
    s.map('TButton',background=[('disabled',PANEL),('pressed','#0D3D4C'),('active','#1B5B6D')],foreground=[('disabled','#718F99')],bordercolor=[('focus','#63BBD1'),('!focus',BUTTON)])
    s.configure('Primary.TButton',background=ACCENT,bordercolor=ACCENT,lightcolor=ACCENT,darkcolor=ACCENT,foreground='#FFFFFF')
    s.map('Primary.TButton',background=[('disabled',PANEL),('pressed','#116A85'),('active','#219FBD')],bordercolor=[('focus','#9DE4F3'),('!focus',ACCENT)])
    for name in ('TEntry','TCombobox','TSpinbox'):
        s.configure(name,font=f,fieldbackground=FIELD,background=PANEL,foreground=TEXT,insertcolor=TEXT,arrowcolor=MUTED,padding=(8,4),bordercolor='#32606D',lightcolor='#32606D',darkcolor='#32606D',borderwidth=1)
        s.map(name,fieldbackground=[('readonly',FIELD)],foreground=[('readonly',TEXT)],selectbackground=[('readonly',FIELD)],selectforeground=[('readonly',TEXT)],bordercolor=[('focus',ACCENT)])
    s.configure('Treeview',font=f,rowheight=f.metrics('linespace')+12,background=BG,fieldbackground=BG,foreground=TEXT,borderwidth=0)
    s.configure('Treeview.Heading',font=f,background=PANEL,foreground=MUTED,padding=(9,8),relief='flat',borderwidth=0)
    s.map('Treeview',background=[('selected','#12536A')],foreground=[('selected','#FFFFFF')])
    s.configure('TScrollbar',background='#32606D',troughcolor=BG,arrowcolor=MUTED,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    s.configure('TNotebook',background=BG,borderwidth=0)
    s.configure('TNotebook.Tab',font=f,background=PANEL,foreground=MUTED,padding=(12,6))
    s.map('TNotebook.Tab',background=[('selected',BG)],foreground=[('selected',TEXT)])
    s.configure('TProgressbar',background=ACCENT,troughcolor=PANEL)
    for pattern,value in [('*Menu.background',PANEL),('*Menu.foreground',TEXT),('*Menu.activeBackground','#12536A'),('*Menu.activeForeground','#FFFFFF'),('*Menu.font','{Segoe UI} 11'),('*TCombobox*Listbox.background',FIELD),('*TCombobox*Listbox.foreground',TEXT),('*TCombobox*Listbox.font','{Segoe UI} 11')]:root.option_add(pattern,value)
    kinds=set(MAPPING.values())|{'left','right','refresh'}
    root._studio_icons={kind:(icon_image(root,kind),icon_image(root,kind,True)) for kind in kinds}
    seen=set()
    def decorate(w):
        if w in seen:return
        try:
            if isinstance(w,(tk.Tk,tk.Toplevel)):w.configure(background=BG);caption(w)
            elif isinstance(w,(tk.Frame,tk.Canvas)):w.configure(background=BG,highlightthickness=0)
            elif isinstance(w,tk.Text):w.configure(font=f,background=BG,foreground=TEXT,insertbackground=TEXT,selectbackground='#12536A',relief='flat',borderwidth=0,highlightthickness=0)
            elif isinstance(w,(tk.Entry,tk.Listbox)):w.configure(font=f,background=FIELD,foreground=TEXT,selectbackground='#12536A',selectforeground='#FFFFFF',relief='flat',highlightthickness=0)
            elif isinstance(w,tk.Menu):w.configure(font=f,background=PANEL,foreground=TEXT,activebackground='#12536A',activeforeground='#FFFFFF')
            elif isinstance(w,ttk.Label):w.configure(font=f,foreground=TEXT)
            elif isinstance(w,(ttk.Entry,ttk.Combobox,ttk.Spinbox)):w.configure(font=f)
            elif isinstance(w,ttk.Button):
                label=str(w.cget('text'));w.configure(style='Primary.TButton' if label=='Обработать очередь' else 'TButton',width=0)
                kind=MAPPING.get(label)
                if label in ('←','→'):
                    kind='left' if label=='←' else 'right';w.configure(text='')
                if kind:
                    normal,disabled=root._studio_icons[kind]
                    w.configure(image=(normal,'disabled',disabled),compound='left')
                if w.winfo_manager()=='pack':w.pack_configure(ipady=0)
            elif isinstance(w,ttk.Treeview):
                for tag,color in [('review','#E0BD79'),('error','#F29696'),('partial','#E0BD79'),('done','#91C9AC'),('accepted','#86CFFF')]:w.tag_configure(tag,background=BG,foreground=color)
                widths={'name':270,'mode':120,'state':200,'number':260,'market':160,'cursor':130,'duration':155,'hit_count':115,'path':400}
                for col in w.cget('columns'):
                    measured=f.measure(str(w.heading(col,'text')))+28
                    w.column(col,width=max(widths.get(col,130),measured),minwidth=max(90,measured),stretch=(col=='path'))
            seen.add(w)
        except tk.TclError:LOG.exception('Editor widget styling failed')
    def walk(w):
        decorate(w)
        for child in w.winfo_children():walk(child)
    def mapped(event):
        w=event.widget
        if not hasattr(w,'winfo_exists') or w in seen:return
        def later():
            try:
                if w.winfo_exists():walk(w)
            except tk.TclError:pass
        root.after_idle(later)
    walk(root);root.bind_all('<Map>',mapped,add='+')
    LOG.info('Editor UI v3 active: distinct action icons, Segoe UI 11pt')

def install(module):
    original=module.Application
    class EditorApplication(original):
        def build(self):
            super().build();apply(self.root)
    module.Application=EditorApplication
