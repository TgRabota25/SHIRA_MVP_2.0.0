"""SHIRA editor-inspired UI. No database changes; icons are original drawings."""
import logging,sys
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.ui')
BG='#002B36';PANEL='#073642';FIELD='#003440';TEXT='#D1DEE1';MUTED='#9AAFB6';ACCENT='#1687A7'

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
        for key,value in [(20,1),(35,0x00362B00),(36,0x00E1DED1),(34,0x00423607)]:
            data=wintypes.DWORD(value);d.DwmSetWindowAttribute(hwnd,key,ctypes.byref(data),4)
    except Exception:LOG.exception('Caption styling failed')

def icon_image(root,kind):
    from PIL import Image,ImageDraw,ImageTk
    f=font.Font(root=root,family='Segoe UI',size=11)
    size=max(16,round(f.metrics('linespace')*.8));scale=3
    im=Image.new('RGBA',(20*scale,20*scale));d=ImageDraw.Draw(im);color=TEXT
    def line(points):d.line([(x*scale,y*scale) for x,y in points],fill=color,width=scale*1)
    def box(rect):d.rectangle(tuple(v*scale for v in rect),outline=color,width=scale)
    if kind=='file':
        line([(5,2),(12,2),(16,6),(16,18),(5,18),(5,2)]);line([(12,2),(12,6),(16,6)]);line([(8,11),(13,11)]);line([(10.5,8.5),(10.5,13.5)])
    elif kind=='folder':line([(2,5),(8,5),(10,7),(18,7),(18,17),(2,17),(2,5)])
    elif kind=='play':line([(6,3),(16,10),(6,17),(6,3)])
    elif kind=='stop':box((5,5,15,15))
    elif kind=='search':
        d.ellipse((3*scale,3*scale,12*scale,12*scale),outline=color,width=scale);line([(12,12),(17,17)])
    elif kind=='export':line([(10,2),(10,13),(6,9)]);line([(10,13),(14,9)]);line([(3,13),(3,18),(17,18),(17,13)])
    elif kind=='settings':
        for y,x in [(5,7),(10,13),(15,9)]:line([(3,y),(17,y)]);box((x-1,y-2,x+1,y+2))
    else:
        line([(5,5),(15,5),(15,15),(5,15)]);line([(5,5),(5,9)]);line([(5,5),(9,5)])
    return ImageTk.PhotoImage(im.resize((size,size),Image.Resampling.LANCZOS),master=root)

def apply(root):
    root._studio_font=font.Font(root=root,family='Segoe UI',size=11)
    f=root._studio_font;s=ttk.Style(root)
    if 'shira_editor' not in s.theme_names():s.theme_create('shira_editor',parent='clam')
    s.theme_use('shira_editor');s.configure('.',font=f,background=BG,foreground=TEXT)
    for name in ('TFrame','TLabel','TCheckbutton','TRadiobutton','TLabelframe','TLabelframe.Label'):s.configure(name,background=BG,foreground=TEXT,font=f)
    s.configure('TLabelframe',borderwidth=0,relief='flat')
    s.configure('TButton',background=PANEL,foreground=TEXT,font=f,padding=(9,4),borderwidth=0,relief='flat',anchor='center')
    s.layout('TButton',[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})])
    s.map('TButton',background=[('pressed','#125467'),('active','#104554')],foreground=[('disabled','#687E86')])
    s.configure('Primary.TButton',background=ACCENT,foreground='#FFFFFF')
    s.map('Primary.TButton',background=[('pressed','#126781'),('active','#239EBD')])
    for name in ('TEntry','TCombobox','TSpinbox'):
        s.configure(name,font=f,fieldbackground=FIELD,background=PANEL,foreground=TEXT,insertcolor=TEXT,arrowcolor=MUTED,padding=(7,4),bordercolor='#28505B',lightcolor='#28505B',darkcolor='#28505B',borderwidth=1)
        s.map(name,fieldbackground=[('readonly',FIELD)],foreground=[('readonly',TEXT)],selectbackground=[('readonly',FIELD)],selectforeground=[('readonly',TEXT)],bordercolor=[('focus',ACCENT)],lightcolor=[('focus',ACCENT)],darkcolor=[('focus',ACCENT)])
    s.configure('Treeview',font=f,rowheight=f.metrics('linespace')+12,background=BG,fieldbackground=BG,foreground=TEXT,borderwidth=0)
    s.configure('Treeview.Heading',font=f,background=PANEL,foreground=MUTED,padding=(9,8),relief='flat',borderwidth=0)
    s.map('Treeview',background=[('selected','#12536A')],foreground=[('selected','#FFFFFF')])
    s.configure('TScrollbar',background='#28505B',troughcolor=BG,arrowcolor=MUTED,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    s.configure('TNotebook',background=BG,borderwidth=0)
    s.configure('TNotebook.Tab',font=f,background=PANEL,foreground=MUTED,padding=(12,6))
    s.map('TNotebook.Tab',background=[('selected',BG)],foreground=[('selected',TEXT)])
    s.configure('TProgressbar',background=ACCENT,troughcolor=PANEL)
    for pattern,value in [('*Menu.background',PANEL),('*Menu.foreground',TEXT),('*Menu.activeBackground','#12536A'),('*Menu.activeForeground','#FFFFFF'),('*Menu.font','{Segoe UI} 11'),('*TCombobox*Listbox.background',FIELD),('*TCombobox*Listbox.foreground',TEXT),('*TCombobox*Listbox.font','{Segoe UI} 11')]:root.option_add(pattern,value)
    root._studio_icons={key:icon_image(root,key) for key in ('file','folder','play','stop','search','export','settings','refresh')}
    mapping={'Добавить файлы':'file','Добавить папку':'folder','Обработать очередь':'play','Стоп':'stop','Найти':'search','Экспорт':'export','Настройки / шаблоны':'settings','Сброс':'refresh','Повторить выбранные':'refresh','Повторить пропуски':'refresh'}
    seen=set()
    def decorate(w):
        if w in seen:return
        try:
            if isinstance(w,(tk.Tk,tk.Toplevel)):
                w.configure(background=BG);caption(w)
            elif isinstance(w,(tk.Frame,tk.Canvas)):w.configure(background=BG,highlightthickness=0)
            elif isinstance(w,tk.Text):w.configure(font=f,background=BG,foreground=TEXT,insertbackground=TEXT,selectbackground='#12536A',relief='flat',borderwidth=0,highlightthickness=0)
            elif isinstance(w,(tk.Entry,tk.Listbox)):w.configure(font=f,background=FIELD,foreground=TEXT,selectbackground='#12536A',selectforeground='#FFFFFF',relief='flat',highlightthickness=0)
            elif isinstance(w,tk.Menu):w.configure(font=f,background=PANEL,foreground=TEXT,activebackground='#12536A',activeforeground='#FFFFFF')
            elif isinstance(w,ttk.Label):w.configure(font=f,foreground=TEXT)
            elif isinstance(w,(ttk.Entry,ttk.Combobox,ttk.Spinbox)):w.configure(font=f)
            elif isinstance(w,ttk.Button):
                label=str(w.cget('text'));w.configure(style='Primary.TButton' if label=='Обработать очередь' else 'TButton',width=0)
                if label in mapping:w.configure(image=root._studio_icons[mapping[label]],compound='left')
                if w.winfo_manager()=='pack':w.pack_configure(ipady=0)
            elif isinstance(w,ttk.Treeview):
                for tag,color in [('review','#E0BD79'),('error','#F29696'),('partial','#E0BD79'),('done','#91C9AC'),('accepted','#86CFFF')]:w.tag_configure(tag,background=BG,foreground=color)
                widths={'name':270,'mode':120,'state':200,'number':260,'market':160,'cursor':130,'duration':155,'hit_count':115,'path':400}
                for col in w.cget('columns'):
                    width=max(widths.get(col,130),f.measure(str(w.heading(col,'text')))+28)
                    w.column(col,width=width,minwidth=min(width,max(90,f.measure(str(w.heading(col,'text')))+28)),stretch=(col=='path'))
            seen.add(w)
        except tk.TclError:LOG.exception('Editor widget styling failed')
    def walk(w):
        decorate(w)
        for child in w.winfo_children():walk(child)
    def mapped(event):
        w=event.widget
        if w not in seen:
            def later():
                try:
                    if w.winfo_exists():walk(w)
                except tk.TclError:pass
            root.after_idle(later)
    walk(root);root.bind_all('<Map>',mapped,add='+')
    LOG.info('Editor UI active: Segoe UI 11pt, teal palette')

def install(module):
    original=module.Application
    class EditorApplication(original):
        def build(self):
            super().build()
            apply(self.root)
    module.Application=EditorApplication
