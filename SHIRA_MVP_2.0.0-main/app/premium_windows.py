"""Size application dialogs from their content, including canvas windows."""
import sys,logging
import tkinter as tk
from tkinter import ttk,font
LOG=logging.getLogger('shira.premium')

def workarea(root):
    fallback=(0,0,root.winfo_screenwidth(),root.winfo_screenheight())
    if sys.platform!='win32':return fallback
    try:
        import ctypes
        from ctypes import wintypes
        u=ctypes.WinDLL('user32',use_last_error=True)
        u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];u.GetAncestor.restype=wintypes.HWND
        u.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD];u.MonitorFromWindow.restype=wintypes.HANDLE
        class Info(ctypes.Structure):
            _fields_=[('cbSize',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
        u.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Info)];u.GetMonitorInfoW.restype=wintypes.BOOL
        hwnd=u.GetAncestor(root.winfo_id(),2) or root.winfo_id()
        info=Info();info.cbSize=ctypes.sizeof(info)
        if u.GetMonitorInfoW(u.MonitorFromWindow(hwnd,2),ctypes.byref(info)):
            r=info.work;return r.left,r.top,r.right-r.left,r.bottom-r.top
    except Exception:LOG.exception('Work area fallback')
    return fallback

def widgets(parent):
    for w in parent.winfo_children():
        if isinstance(w,tk.Toplevel):continue
        yield w
        yield from widgets(w)

def canvas_frames(win):
    result=[]
    for w in widgets(win):
        if isinstance(w,tk.Canvas):
            for item in w.find_all():
                if w.type(item)=='window':
                    path=w.itemcget(item,'window')
                    if path:
                        try:result.append((w,item,w.nametowidget(path)))
                        except KeyError:pass
    return result

def fit(win,root):
    if not win.winfo_exists():return
    win.update_idletasks()
    x,y,sw,sh=workarea(root)
    maxw=max(250,sw-48);maxh=max(200,sh-78)
    frames=canvas_frames(win)
    # Include natural content dimensions rather than only Canvas default size.
    neededw=max([win.winfo_reqwidth()]+[inner.winfo_reqwidth()+48 for _,_,inner in frames])
    width=min(maxw,max(min(720,maxw),neededw))
    for w in widgets(win):
        if isinstance(w,(ttk.Label,ttk.Checkbutton)) and str(w.cget('text')):
            available=max(160,width-64)
            if w.winfo_manager()=='grid':
                siblings=w.master.winfo_children()
                inputs=[s for s in siblings if isinstance(s,(ttk.Entry,ttk.Combobox,ttk.Spinbox))]
                available=max(160,available-max([0]+[s.winfo_reqwidth()+30 for s in inputs]))
                try:w.master.columnconfigure(0,weight=1)
                except tk.TclError:pass
            try:w.configure(wraplength=available)
            except tk.TclError:pass
            if str(w.cget('foreground'))=='#666':w.configure(foreground='#A6B0C0')
    for canvas,item,inner in frames:
        canvas.itemconfigure(item,width=max(150,width-48))
    win.update_idletasks()
    overhead=max(24,win.winfo_reqheight()-max([0]+[c.winfo_reqheight() for c,_,_ in frames])) if frames else 0
    neededh=max([win.winfo_reqheight()]+[inner.winfo_reqheight()+overhead+20 for _,_,inner in frames])
    # If necessary shrink only multiline editors, not labels/buttons or fonts.
    if neededh>maxh:
        budget=neededh-maxh
        for w in widgets(win):
            if not isinstance(w,tk.Text):continue
            try:
                current=int(w.cget('height'));f=font.Font(root=root,font=w.cget('font'));line=max(1,f.metrics('linespace'))
                reduce=min(max(0,current-4),(budget+line-1)//line)
                if reduce:w.configure(height=current-reduce);budget=max(0,budget-reduce*line)
            except (tk.TclError,ValueError):pass
        win.update_idletasks()
        neededh=max([win.winfo_reqheight()]+[inner.winfo_reqheight()+overhead+20 for _,_,inner in frames])
    height=min(maxh,max(min(350,maxh),neededh))
    win.minsize(min(500,width),min(300,height));win.resizable(True,True)
    win.geometry(f'{width}x{height}{x+max(0,(sw-width)//2):+d}{y+max(0,(sh-height-30)//2):+d}')
    for canvas,item,inner in frames:
        canvas.configure(scrollregion=canvas.bbox('all'))
        canvas.yview_moveto(0)
    LOG.info('Content fit: %s width=%s height=%s needed=%s area=%sx%s',win.title(),width,height,neededh,sw,sh)

def attach(root):
    def maximize():
        try:root.state('zoomed')
        except tk.TclError:
            x,y,w,h=workarea(root);root.geometry(f'{w}x{max(200,h-40)}{x:+d}{y:+d}')
    root.after(180,maximize)
    seen=set()
    def scan():
        if not root.winfo_exists():return
        def visit(parent):
            for w in parent.winfo_children():
                if isinstance(w,tk.Toplevel) and w.winfo_ismapped() and w not in seen:
                    seen.add(w)
                    def later(window=w):
                        try:fit(window,root)
                        except Exception:LOG.exception('Dialog fit failed')
                    root.after(350,later)
                visit(w)
        try:visit(root)
        except tk.TclError:pass
        root.after(400,scan)
    root.after(250,scan)

def install(module):
    original=module.Application
    class WindowApplication(original):
        def __init__(self,root,*args,**kwargs):
            super().__init__(root,*args,**kwargs)
            attach(root)
    module.Application=WindowApplication
