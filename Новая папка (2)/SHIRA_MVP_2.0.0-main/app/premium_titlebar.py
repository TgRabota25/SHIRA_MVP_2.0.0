"""Native Windows caption colors; keep native window controls."""
import sys,logging
import tkinter as tk
LOG=logging.getLogger('shira.premium')
def attach(root):
    if sys.platform!='win32':return
    import ctypes
    from ctypes import wintypes
    user=ctypes.WinDLL('user32',use_last_error=True)
    dwm=ctypes.WinDLL('dwmapi',use_last_error=True)
    user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    user.GetAncestor.restype=wintypes.HWND
    dwm.DwmSetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
    dwm.DwmSetWindowAttribute.restype=ctypes.c_long
    user.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
    user.SetWindowPos.restype=wintypes.BOOL
    def color(hexcode):
        r,g,b=bytes.fromhex(hexcode.lstrip('#'))
        return r|(g<<8)|(b<<16)
    def paint(window):
        try:
            if not window.winfo_exists() or not window.winfo_ismapped():return
            raw=window.winfo_id();hwnd=user.GetAncestor(raw,2) or raw
            results=[]
            for attr,value in [(20,1),(35,color('#171A21')),(36,color('#EDF1F7')),(34,color('#252E3D'))]:
                data=wintypes.DWORD(value)
                hr=dwm.DwmSetWindowAttribute(hwnd,attr,ctypes.byref(data),ctypes.sizeof(data))
                results.append((attr,int(hr)))
            user.SetWindowPos(hwnd,None,0,0,0,0,0x0001|0x0002|0x0004|0x0010|0x0020)
            LOG.info('Native caption: %s',results)
        except Exception:LOG.exception('Native caption styling failed')
    seen=set()
    def scan():
        if not root.winfo_exists():return
        def visit(w):
            if isinstance(w,(tk.Tk,tk.Toplevel)) and w.winfo_ismapped() and str(w) not in seen:
                paint(w);seen.add(str(w))
            for c in w.winfo_children():visit(c)
        try:visit(root)
        except tk.TclError:pass
        root.after(900,scan)
    root.after(150,scan)
def install(module):
    original=module.Application
    class CaptionApplication(original):
        def __init__(self,root,*args,**kwargs):
            super().__init__(root,*args,**kwargs)
            root.after_idle(lambda:attach(root))
    module.Application=CaptionApplication
