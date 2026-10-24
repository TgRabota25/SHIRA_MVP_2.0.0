"""Readable, compact toolbar controls for SHIRA Tactile."""
import logging
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.premium')

def install(theme):
    original_apply=theme.apply
    def image(root,top,bottom,pressed=False,focus=False):
        from PIL import Image,ImageDraw,ImageTk
        f=font.Font(root=root,family='Segoe UI',size=11)
        height=max(28,f.metrics('linespace')+8)
        width=80;scale=3
        bg=getattr(theme,'BG','#111318')
        im=Image.new('RGB',(width*scale,height*scale),bg)
        mask=Image.new('L',im.size,0)
        y=2 if pressed else 0
        ImageDraw.Draw(mask).rounded_rectangle((scale,y*scale,(width-2)*scale,(height-4)*scale),radius=5*scale,fill=255)
        layer=Image.new('RGB',im.size);draw=ImageDraw.Draw(layer)
        a=tuple(bytes.fromhex(top.lstrip('#')));b=tuple(bytes.fromhex(bottom.lstrip('#')))
        for row in range(height*scale):
            t=min(1,max(0,(row-y*scale)/max(1,(height-4-y)*scale)))
            rgb=tuple(round(x+(z-x)*t) for x,z in zip(a,b))
            draw.line((0,row,width*scale,row),fill=rgb)
        ImageDraw.Draw(im).rounded_rectangle((scale,3*scale,(width-2)*scale,(height-1)*scale),radius=5*scale,fill='#090C12')
        im.paste(layer,(0,0),mask);d=ImageDraw.Draw(im)
        if not pressed:d.line((8*scale,scale,(width-9)*scale,scale),fill='#455061',width=scale)
        if focus:d.line((9*scale,(height-6)*scale,(width-10)*scale,(height-6)*scale),fill='#7AA9DF',width=scale)
        return ImageTk.PhotoImage(im.resize((width,height),Image.Resampling.LANCZOS),master=root)
    theme.button_image=image
    def compact(root):
        s=ttk.Style(root)
        root._compact_font=font.Font(root=root,family='Segoe UI',size=11)
        f=root._compact_font
        images=getattr(root,'_shira_button_images',[])
        if len(images)==10:
            for offset,element,targets in [(0,'Readable.surface',('TButton',)),(5,'ReadableAccent.surface',('Premium.TButton','Accent.TButton'))]:
                normal,hover,down,focus,disabled=images[offset:offset+5]
                if element not in s.element_names():
                    s.element_create(element,'image',normal,('disabled',disabled),('pressed',down),('focus',focus),('active',hover),border=(10,4,10,6),sticky='nsew')
                layout=[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})]
                for target in targets:s.layout(target,layout)
        for name in ('TButton','Premium.TButton','Accent.TButton'):
            s.configure(name,font=f,padding=(10,2),width=0,anchor='center')
        for name in ('TEntry','TCombobox','TSpinbox'):
            s.configure(name,font=f,padding=(8,3))
        parents=set()
        def walk(parent):
            for w in parent.winfo_children():
                if isinstance(w,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Spinbox)) and w.winfo_manager()=='pack':
                    if str(w.pack_info().get('side')) in ('left','right'):
                        parents.add(w.master)
                        w.pack_configure(ipady=0,pady=0,anchor='center')
                        if isinstance(w,ttk.Button):w.configure(width=0)
                        elif isinstance(w,ttk.Combobox):
                            values=tuple(w.cget('values'))
                            text=max([str(v) for v in values]+[w.get()],key=f.measure)
                            unit=max(1,f.measure('0'))
                            w.configure(width=max(5,(f.measure(text)+unit-1)//unit+1))
                walk(w)
        walk(root);root.update_idletasks()
        for parent in parents:
            controls=[w for w in parent.winfo_children() if isinstance(w,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Spinbox)) and w.winfo_manager()=='pack' and str(w.pack_info().get('side')) in ('left','right')]
            if not controls:continue
            target=max(w.winfo_reqheight() for w in controls)
            for w in controls:w.pack_configure(ipady=max(0,(target-w.winfo_reqheight())//2),anchor='center')
        LOG.info('Readable toolbar applied: font=11pt, linespace=%s',f.metrics('linespace'))
    def apply(root,*args,**kwargs):
        result=original_apply(root,*args,**kwargs)
        def finish():
            try:compact(root)
            except Exception:LOG.exception('Compact layout failed')
        root.after_idle(finish)
        return result
    theme.apply=apply
