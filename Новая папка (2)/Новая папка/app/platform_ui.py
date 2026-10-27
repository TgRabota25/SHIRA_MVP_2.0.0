import os,sys,subprocess
from pathlib import Path
from config import ROOT,APPID

def app_identity():
 if os.name=='nt':
  import ctypes
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)

def icon(window):
 try:
  if os.name=='nt':window.iconbitmap(default=str(ROOT/'app/icon.ico'));window.iconbitmap(str(ROOT/'app/icon.ico'))
  else:
   import tkinter as tk
   window._shira_icon=tk.PhotoImage(file=str(ROOT/'app/icon.png'));window.iconphoto(True,window._shira_icon)
 except Exception:pass

def open_path(path,select=False):
 path=Path(path).resolve()
 if not path.exists():raise FileNotFoundError(str(path))
 if os.name=='nt':
  if select:subprocess.Popen(['explorer.exe','/select,',str(path)])
  else:os.startfile(str(path))
 elif sys.platform=='darwin':subprocess.Popen(['open','-R',str(path)] if select else ['open',str(path)])
 else:subprocess.Popen(['xdg-open',str(path.parent if select else path)])

def copy_files(window,paths):
 paths=[str(Path(p).resolve()) for p in paths if Path(p).is_file()]
 if not paths:raise ValueError('Файл не найден')
 if os.name!='nt':
  window.clipboard_clear();window.clipboard_append('\n'.join(paths));window.update();return 'text'
 import ctypes,struct,time
 from ctypes import wintypes
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);user=ctypes.WinDLL('user32',use_last_error=True)
 kernel.GlobalAlloc.argtypes=[wintypes.UINT,ctypes.c_size_t];kernel.GlobalAlloc.restype=wintypes.HGLOBAL
 kernel.GlobalLock.argtypes=[wintypes.HGLOBAL];kernel.GlobalLock.restype=ctypes.c_void_p
 kernel.GlobalUnlock.argtypes=[wintypes.HGLOBAL];kernel.GlobalFree.argtypes=[wintypes.HGLOBAL]
 user.SetClipboardData.argtypes=[wintypes.UINT,wintypes.HANDLE];user.SetClipboardData.restype=wintypes.HANDLE
 user.OpenClipboard.argtypes=[wintypes.HWND]
 hwnd=window.winfo_id()
 for _ in range(10):
  if user.OpenClipboard(hwnd):break
  time.sleep(.05)
 else:raise OSError('Буфер обмена занят другим приложением')
 try:
  if not user.EmptyClipboard():raise OSError('Не удалось очистить буфер обмена')
  payload=struct.pack('<IiiII',20,0,0,0,1)+('\0'.join(paths)+'\0\0').encode('utf-16-le')
  handle=kernel.GlobalAlloc(0x42,len(payload))
  if not handle:raise MemoryError('GlobalAlloc')
  ptr=kernel.GlobalLock(handle)
  if not ptr:kernel.GlobalFree(handle);raise OSError('GlobalLock')
  ctypes.memmove(ptr,payload,len(payload));kernel.GlobalUnlock(handle)
  if not user.SetClipboardData(15,handle):kernel.GlobalFree(handle);raise OSError('SetClipboardData')
 finally:user.CloseClipboard()
 return 'files'
