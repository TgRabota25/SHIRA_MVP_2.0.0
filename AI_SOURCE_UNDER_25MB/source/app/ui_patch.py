"""Runtime UI improvements for SHIRA: icons, centered dialogs, click-to-clear selection."""
import tkinter as tk
from tkinter import ttk

def plain(value):
    value=str(value)
    return value.split(' ',1)[1] if value.startswith(('⚡ ','🚀 ','📋 ','🗂 ')) else value

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

def install(main_module):
    Application=main_module.Application
    class UIImprovedApplication(Application):
        def __init__(self,root,store):
            super().__init__(root,store)
            root.bind('<Button-1>',self.clear_selection_if_empty,add='+')
        def clear_selection_if_empty(self,event):
            if event.widget is self.tree:return
            if self.tree.selection():self.tree.selection_remove(*self.tree.selection())
        def active_cfg(self):
            self.cfg['profile']=self.profile.get()
            self.cfg['mode']='short' if plain(self.mode.get())=='Короткая' else 'long'
            from config import atomic_json,data_dir
            atomic_json(data_dir()/'settings-v2.json',self.cfg)
            return super().active_cfg()
        def refresh(self):
            # translate decorated filter values back to plain ones before super().refresh()
            self.state.set(plain(self.state.get()))
            self.filter_mode.set(plain(self.filter_mode.get()))
            super().refresh()
        def clear_filter(self):
            self.search.set('')
            self.state.set('📋 Все статусы')
            self.filter_mode.set('🗂 Все сессии')
            self.find()
    main_module.Application=UIImprovedApplication
