"""Optional SHIRA tactile theme. No processing or storage changes."""
import logging
import tkinter as tk
from tkinter import ttk
LOG=logging.getLogger('shira.premium')
BG='#111318';SURFACE='#181D26';FIELD='#131923';TEXT='#EDF1F7';MUTED='#A6B0C0'

def button_image(root,top,bottom,pressed=False,focus=False):
    from PIL import Image,ImageDraw,ImageTk
    scale=3;w=120;h=42
    im=Image.new('RGB',(w*scale,h*scale),BG)
    mask=Image.new('L',im.size,0);d=ImageDraw.Draw(mask)
    y=3 if pressed else 0
    d.rounded_rectangle((2*scale,y*scale,(w-3)*scale,(h-5)*scale),radius=7*scale,fill=255)
    layer=Image.new('RGB',im.size)
    a=tuple(bytes.fromhex(top.lstrip('#')));b=tuple(bytes.fromhex(bottom.lstrip('#')))
    draw=ImageDraw.Draw(layer)
    for row in range(h*scale):
        t=min(1,max(0,(row-y*scale)/max(1,(h-5-y)*scale)))
        color=tuple(round(x+(z-x)*t) for x,z in zip(a,b))
        draw.line((0,row,w*scale,row),fill=color)
    shadow=ImageDraw.Draw(im)
    shadow.rounded_rectangle((2*scale,4*scale,(w-3)*scale,(h-1)*scale),radius=7*scale,fill='#090C12')
    im.paste(layer,(0,0),mask)
    d=ImageDraw.Draw(im)
    if not pressed:
        light='#45627F' if focus else '#455061'
        d.line((10*scale,1*scale,(w-11)*scale,1*scale),fill=light,width=scale)
    if focus:
        d.line((12*scale,(h-7)*scale,(w-13)*scale,(h-7)*scale),fill='#7AA9DF',width=scale)
    return ImageTk.PhotoImage(im.resize((w,h),Image.Resampling.LANCZOS),master=root)

def apply(root):
    s=ttk.Style(root)
    name='shira_tactile'
    if name not in s.theme_names():s.theme_create(name,parent='clam')
    s.theme_use(name)
    root.configure(background=BG)
    s.configure('.',background=BG,foreground=TEXT)
    s.configure('TFrame',background=BG)
    s.configure('TLabel',background=BG,foreground=TEXT)
    root._shira_button_images=[]
    for prefix,colors,fg in [('Tactile',('#333E50','#202937'),'#EDF1F7'),('TactileAccent',('#86B8F1','#477AB7'),'#0C1C32')]:
        normal=button_image(root,*colors)
        hover=button_image(root,'#42516A','#2B374B') if prefix=='Tactile' else button_image(root,'#A0CDFF','#6396D2')
        down=button_image(root,'#1B2432','#2C3748',True) if prefix=='Tactile' else button_image(root,'#3E6592','#6C9CD1',True)
        focus=button_image(root,*colors,focus=True)
        disabled=button_image(root,'#232A35','#1B212B')
        root._shira_button_images.extend([normal,hover,down,focus,disabled])
        element=prefix+'.surface'
        s.element_create(element,'image',normal,('disabled',disabled),('pressed',down),('focus',focus),('active',hover),border=(12,10,12,10),sticky='nsew')
        layout=[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})]
        targets=['TButton'] if prefix=='Tactile' else ['Premium.TButton','Accent.TButton']
        for target in targets:
            s.layout(target,layout)
            s.configure(target,foreground=fg,background=BG,padding=(11,8),anchor='center',borderwidth=0)
            s.map(target,foreground=[('disabled','#718097')])
    for name_ in ['TEntry','TCombobox','TSpinbox']:
        s.configure(name_,fieldbackground=FIELD,background='#253041',foreground=TEXT,insertcolor=TEXT,arrowcolor=MUTED,bordercolor='#242E3C',lightcolor='#242E3C',darkcolor='#0B1018',borderwidth=1)
        s.map(name_,fieldbackground=[('readonly',FIELD)],foreground=[('disabled','#68758A'),('readonly',TEXT)],bordercolor=[('focus','#5D83B4'),('!focus','#242E3C')],lightcolor=[('focus','#5D83B4'),('!focus','#242E3C')],darkcolor=[('focus','#344D6D'),('!focus','#0B1018')],selectbackground=[('readonly',FIELD)],selectforeground=[('readonly',TEXT)])
    root.option_add('*TCombobox*Listbox.background',FIELD)
    root.option_add('*TCombobox*Listbox.foreground',TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground','#304765')
    s.configure('TCheckbutton',background=BG,foreground=TEXT,indicatorbackground=FIELD,indicatorforeground='#81B5FF',bordercolor='#303C4D',lightcolor='#303C4D',darkcolor='#0B1018')
    s.map('TCheckbutton',background=[('active',BG)])
    s.configure('TLabelframe',background=BG,bordercolor='#252E3D',lightcolor='#252E3D',darkcolor='#252E3D')
    s.configure('TLabelframe.Label',background=BG,foreground=MUTED)
    s.configure('Treeview',background=SURFACE,fieldbackground=SURFACE,foreground=TEXT,bordercolor=BG,lightcolor=BG,darkcolor=BG,borderwidth=0)
    s.configure('Treeview.Heading',background='#252E3D',foreground=MUTED,bordercolor='#252E3D',lightcolor='#303B4D',darkcolor='#10151E',relief='flat')
    s.map('Treeview',background=[('selected','#2D4564')],foreground=[('selected','#FFFFFF')])
    s.configure('TScrollbar',background='#303C4E',troughcolor=BG,arrowcolor=MUTED,bordercolor=BG,lightcolor='#3C485B',darkcolor='#151A23')
    s.configure('TNotebook',background=BG,borderwidth=0)
    s.configure('TNotebook.Tab',background='#232C3A',foreground=MUTED,lightcolor='#344155',darkcolor='#10151E',bordercolor=BG)
    s.map('TNotebook.Tab',background=[('selected',SURFACE)],foreground=[('selected',TEXT)])
    s.configure('TProgressbar',background='#81B5FF',troughcolor=FIELD,bordercolor=FIELD,lightcolor='#A2CCFF',darkcolor='#527DB3')
    seen=set()
    def decorate(parent):
        for w in parent.winfo_children():
            try:
                key=str(w)
                if key not in seen:
                    if isinstance(w,(tk.Canvas,tk.Toplevel)):w.configure(background=BG)
                    elif isinstance(w,tk.Text):w.configure(background=SURFACE,foreground=MUTED,insertbackground=TEXT,relief='flat',borderwidth=0,highlightthickness=0)
                    elif isinstance(w,ttk.Button) and str(w.cget('text'))=='Обработать очередь':w.configure(style='Premium.TButton')
                    elif isinstance(w,ttk.Treeview):
                        for tag,b,f in [('review','#302B20','#E6C184'),('error','#34242A','#F0AFB9'),('partial','#302A23','#E3C09B'),('done','#1C302A','#90D6B7'),('accepted','#20314A','#A5CEFF')]:w.tag_configure(tag,background=b,foreground=f)
                    seen.add(key)
                decorate(w)
            except tk.TclError:LOG.exception('Decoration error')
    def refresh():
        if not root.winfo_exists():return
        decorate(root)
        root.after(800,refresh)
    refresh()
    root.title(root.title()+' [Premium Tactile]')
    LOG.info('Tactile theme applied')

def install(module):
    original=module.Application
    class PremiumApplication(original):
        def __init__(self,root,*args,**kwargs):
            super().__init__(root,*args,**kwargs)
            def finish():
                try:apply(root)
                except Exception:
                    LOG.exception('Theme setup failed')
                    from tkinter import messagebox
                    messagebox.showerror('SHIRA Premium','Не удалось применить тему. Подробности: premium-startup.log',parent=root)
            root.after_idle(finish)
    module.Application=PremiumApplication
