"""Compact, text-sized toolbar controls for SHIRA Tactile."""
import logging
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.premium')

def install(theme):
    original_apply=theme.apply
    original_image=theme.button_image
    def image(root,top,bottom,pressed=False,focus=False):
        from PIL import Image,ImageDraw,ImageTk
        f=font.Font(root=root,family='Segoe UI',size=10)
        height=max(30,f.metrics('linespace')+14)
        width=80;scale=3
        bg=getattr(theme,'BG','#111318')
        im=Image.new('RGB',(width*scale,height*scale),bg)
        mask=Image.new('L',im.size,0)
        y=2 if pressed else 0
        ImageDraw.Draw(mask).rounded_rectangle((1*scale,y*scale,(width-2)*scale,(height-4)*scale),radius=6*scale,fill=255)
        layer=Image.new('RGB',im.size)
        draw=ImageDraw.Draw(layer)
        a=tuple(bytes.fromhex(top.lstrip('#')));b=tuple(bytes.fromhex(bottom.lstrip('#')))
        for row in range(height*scale):
            t=min(1,max(0,(row-y*scale)/max(1,(height-4-y)*scale)))
            rgb=tuple(round(x+(z-x)*t) for x,z in zip(a,b))
            draw.line((0,row,width*scale,row),fill=rgb)
        ImageDraw.Draw(im).rounded_rectangle((scale,3*scale,(width-2)*scale,(height-1)*scale),radius=6*scale,fill='#090C12')
        im.paste(layer,(0,0),mask)
        d=ImageDraw.Draw(im)
        if not pressed:d.line((8*scale,scale,(width-9)*scale,scale),fill='#455061',width=scale)
        if focus:d.line((9*scale,(height-6)*scale,(width-10)*scale,(height-6)*scale),fill='#7AA9DF',width=scale)
        return ImageTk.PhotoImage(im.resize((width,height),Image.Resampling.LANCZOS),master=root)
    theme.button_image=image
    def compact(root):
        s=ttk.Style(root)
        root._compact_font=font.Font(root=root,family='Segoe UI',size=10)
        f=root._compact_font
        for name in ('TButton','Premium.TButton','Accent.TButton'):
            s.configure(name,font=f,padding=(10,4),width=0)
        for name in ('TEntry','TCombobox','TSpinbox'):
            s.configure(name,font=f,padding=(8,4))
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
                            # Tk entry widths use average character units.
                            chars=max(5,(f.measure(text)+f.measure('0')-1)//max(1,f.measure('0'))+1)
                            w.configure(width=chars)
                walk(w)
        walk(root);root.update_idletasks()
        for parent in parents:
            controls=[w for w in parent.winfo_children() if isinstance(w,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Spinbox)) and w.winfo_manager()=='pack' and str(w.pack_info().get('side')) in ('left','right')]
            if not controls:continue
            target=max(w.winfo_reqheight() for w in controls)
            for w in controls:
                w.pack_configure(ipady=max(0,(target-w.winfo_reqheight())//2),anchor='center')
        LOG.info('Compact toolbar applied; font linespace=%s',f.metrics('linespace'))
    def apply(root,*args,**kwargs):
        result=original_apply(root,*args,**kwargs)
        # Previous layout fix schedules its own idle pass first.
        def finish():
            try:compact(root)
            except Exception:LOG.exception('Compact layout failed')
        root.after_idle(finish)
        return result
    theme.apply=apply
