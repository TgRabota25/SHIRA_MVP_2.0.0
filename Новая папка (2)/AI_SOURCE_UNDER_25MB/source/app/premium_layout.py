"""Layout-only correction for the SHIRA tactile theme."""
import logging
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.premium')

def adjust(root):
    s=ttk.Style(root)
    root._premium_table_font=font.Font(root=root,family='Segoe UI',size=10)
    root._premium_heading_font=font.Font(root=root,family='Segoe UI',size=10,weight='bold')
    body=root._premium_table_font
    heading=root._premium_heading_font
    line=body.metrics('linespace')
    s.configure('Treeview',font=body,rowheight=line+14)
    s.configure('Treeview.Heading',font=heading,padding=(10,9))
    # The button image sets a minimum height. Match fields via internal padding,
    # then equalize the pack allocations without changing parent geometry.
    for name in ('TEntry','TCombobox','TSpinbox'):
        s.configure(name,padding=(9,8),arrowsize=max(12,int(line*.6)))
    parents=set()
    def walk(w):
        for child in w.winfo_children():
            if isinstance(child,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Spinbox)) and child.winfo_manager()=='pack':
                if str(child.pack_info().get('side')) in ('left','right'):parents.add(child.master)
            if isinstance(child,ttk.Treeview):
                cols=tuple(child.cget('columns'))
                sizes={'name':(290,230),'mode':(120,110),'state':(205,180),'number':(260,230),'market':(155,140),'cursor':(125,115),'duration':(150,135),'hit_count':(110,100),'path':(440,260)}
                labels={'market':'Маркетплейс','cursor':'Пройдено','duration':'Длительность','hit_count':'Этикеток'}
                for col in cols:
                    if col in sizes:
                        preferred,minimum=sizes[col]
                        text=labels.get(col,str(child.heading(col,'text')))
                        measured=heading.measure(text)+32
                        child.column(col,width=max(preferred,measured),minwidth=max(minimum,measured),stretch=(col=='path'))
                        if col in labels:child.heading(col,text=labels[col])
                # Retain state tags and selection semantics; no row values are changed.
            walk(child)
    walk(root)
    root.update_idletasks()
    for parent in parents:
        widgets=[w for w in parent.winfo_children() if isinstance(w,(ttk.Button,ttk.Entry,ttk.Combobox,ttk.Spinbox)) and w.winfo_manager()=='pack' and str(w.pack_info().get('side')) in ('left','right')]
        if len(widgets)<2:continue
        height=max(w.winfo_reqheight() for w in widgets)
        for w in widgets:
            extra=max(0,(height-w.winfo_reqheight())//2)
            w.pack_configure(ipady=extra,pady=0,anchor='center')
    LOG.info('Table correction applied: linespace=%s rowheight=%s',line,line+14)

def install(theme):
    original=theme.apply
    def fixed(root,*args,**kwargs):
        result=original(root,*args,**kwargs)
        root.after_idle(lambda:adjust(root))
        return result
    theme.apply=fixed
