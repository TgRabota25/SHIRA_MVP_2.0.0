from pathlib import Path
import multiprocessing,os,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:
  from main import main
  main()
 except BaseException:
  text=traceback.format_exc()
  from config import data_dir
  (data_dir()/'startup-error.txt').write_text(text,encoding='utf-8')
  try:
   import tkinter as tk
   from tkinter import messagebox
   root=tk.Tk();root.withdraw();messagebox.showerror('SHIRA — ошибка запуска',text);root.destroy()
  except Exception:print(text,file=sys.stderr)
  sys.exit(1)
