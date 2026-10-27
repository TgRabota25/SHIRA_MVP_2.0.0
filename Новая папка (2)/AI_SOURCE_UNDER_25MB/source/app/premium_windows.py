"""Bound oversized dialogs without delayed centering. Keep native window placement."""
import logging,sys
import tkinter as tk
LOG=logging.getLogger('shira.premium')

def workarea(root):
    fallback=(0,0,root.winfo_screenwidth(),root.winfo_screenheight())
    if sys.platform!='win32':
        return fallback
    try:
        import ctypes
        from ctypes import wintypes
        u=ctypes.WinDLL('user32',use_last_error=True)
        u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
        u.GetAncestor.restype=wintypes.HWND
        u.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
        u.MonitorFromWindow.restype=wintypes.HANDLE
        class Info(ctypes.Structure):
            _fields_=[('cbSize',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
        u.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Info)]
        u.GetMonitorInfoW.restype=wintypes.BOOL
        hwnd=u.GetAncestor(root.winfo_id(),2) or root.winfo_id()
        info=Info();info.cbSize=ctypes.sizeof(info)
        if u.GetMonitorInfoW(u.MonitorFromWindow(hwnd,2),ctypes.byref(info)):
            r=info.work
            return r.left,r.top,r.right-r.left,r.bottom-r.top
    except Exception:
        LOG.exception('Work area fallback')
    return fallback

def fit(win,root):
    if not win.winfo_exists():
        return
    _,_,sw,sh=workarea(root)
    maxw=max(250,sw-48);maxh=max(200,sh-78)
    width=win.winfo_width();height=win.winfo_height()
    win.minsize(min(500,maxw),min(300,maxh))
    win.resizable(True,True)
    if width>maxw or height>maxh:
        win.geometry(f'{min(width,maxw)}x{min(height,maxh)}')
        LOG.info('Oversized dialog bounded, position unchanged: %s',win.title())

def attach(root):
    seen=set()
    def maximize():
        try:
            root.state('zoomed')
        except tk.TclError:
            x,y,w,h=workarea(root)
            root.geometry(f'{w}x{max(200,h-40)}{x:+d}{y:+d}')
    root.after_idle(maximize)
    def mapped(event):
        win=event.widget
        if not isinstance(win,tk.Toplevel) or win in seen:
            return
        seen.add(win)
        def finish():
            try:
                fit(win,root)
            except tk.TclError:
                pass
            except Exception:
                LOG.exception('Dialog bounds failed')
        root.after_idle(finish)
    root.bind_all('<Map>',mapped,add='+')

def install(module):
    original=module.Application
    class WindowApplication(original):
        def __init__(self,root,*args,**kwargs):
            super().__init__(root,*args,**kwargs)
            attach(root)
    module.Application=WindowApplication
