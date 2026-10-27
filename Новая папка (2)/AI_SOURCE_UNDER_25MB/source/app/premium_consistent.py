"""Consistent application widgets; native OS dialogs are not replaced."""
import logging
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.premium')

def attach(root):
    if getattr(root,'_consistent_attached',False):return
    root._consistent_attached=True
    root._consistent_font=font.Font(root=root,family='Segoe UI',size=11)
    body=root._consistent_font
    style=ttk.Style(root)
    for name in ('TLabel','TButton','Premium.TButton','Accent.TButton','TEntry','TCombobox','TSpinbox','TCheckbutton','TRadiobutton','TNotebook.Tab','TLabelframe.Label'):
        style.configure(name,font=body)
    style.configure('TRadiobutton',background='#111318',foreground='#EDF1F7')
    style.map('TRadiobutton',background=[('active','#111318')])
    style.configure('TSeparator',background='#283243')
    root.option_add('*Menu.background','#181D26')
    root.option_add('*Menu.foreground','#EDF1F7')
    root.option_add('*Menu.activeBackground','#304765')
    root.option_add('*Menu.activeForeground','#FFFFFF')
    root.option_add('*Menu.font','{Segoe UI} 11')
    root.option_add('*TCombobox*Listbox.font','{Segoe UI} 11')
    root.option_add('*TCombobox*Listbox.background','#131923')
    root.option_add('*TCombobox*Listbox.foreground','#EDF1F7')
    seen=set()
    def decorate(widget):
        if widget in seen:return
        try:
            if isinstance(widget,(tk.Tk,tk.Toplevel,tk.Frame)):
                widget.configure(background='#111318')
            elif isinstance(widget,tk.Canvas):
                widget.configure(background='#111318',highlightthickness=0)
            elif isinstance(widget,tk.Text):
                widget.configure(background='#181D26',foreground='#EDF1F7',insertbackground='#EDF1F7',selectbackground='#304765',selectforeground='#FFFFFF',relief='flat',borderwidth=0,highlightthickness=0)
            elif isinstance(widget,tk.Entry):
                widget.configure(background='#131923',foreground='#EDF1F7',insertbackground='#EDF1F7',font=body,relief='flat',highlightbackground='#283243',highlightcolor='#5D83B4',highlightthickness=1)
            elif isinstance(widget,tk.Listbox):
                widget.configure(background='#131923',foreground='#EDF1F7',selectbackground='#304765',selectforeground='#FFFFFF',font=body,relief='flat',highlightthickness=0)
            elif isinstance(widget,tk.Menu):
                widget.configure(background='#181D26',foreground='#EDF1F7',activebackground='#304765',activeforeground='#FFFFFF',font=body)
            elif isinstance(widget,ttk.Label):
                explicit=str(widget.cget('font'))
                if not explicit or int(font.Font(root=root,font=explicit).actual('size'))<=11:
                    widget.configure(font=body)
                if str(widget.cget('foreground')).lower() in ('#666','#666666','black','#000000'):
                    widget.configure(foreground='#A6B0C0')
            seen.add(widget)
        except (tk.TclError,ValueError):
            LOG.exception('Consistent widget decoration failed')
    def walk(parent):
        decorate(parent)
        for child in parent.winfo_children():walk(child)
    def mapped(event):
        widget=event.widget
        if widget in seen:return
        def later():
            try:
                if widget.winfo_exists():walk(widget)
            except tk.TclError:pass
        root.after_idle(later)
    walk(root)
    root.bind_all('<Map>',mapped,add='+')
    LOG.info('Consistent application window styling enabled')

def install(theme):
    original=theme.apply
    def apply(root,*args,**kwargs):
        result=original(root,*args,**kwargs)
        root.after_idle(lambda:attach(root))
        return result
    theme.apply=apply
