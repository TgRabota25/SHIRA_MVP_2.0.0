from pathlib import Path
import logging,multiprocessing,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))

def run():
    from config import data_dir
    logdir=data_dir()/'logs'
    logdir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=str(logdir/'desktop-startup.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8',force=True)
    import main as app
    if '--standard' not in sys.argv:
        import premium_ui
        for name in ('premium_layout','premium_compact','premium_consistent'):
            module=__import__(name)
            module.install(premium_ui)
        premium_ui.install(app)
        import premium_titlebar,premium_windows
        premium_titlebar.install(app)
        premium_windows.install(app)
    import archive_delete
    archive_delete.install(app)
    app.main()

if __name__=='__main__':
    multiprocessing.freeze_support()
    try:
        run()
    except Exception:
        text=traceback.format_exc()
        logging.exception('Startup failed')
        try:
            from config import data_dir
            (data_dir()/'startup-error.txt').write_text(text,encoding='utf-8')
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw()
            messagebox.showerror('SHIRA — ошибка запуска',text,parent=root)
            root.destroy()
        except Exception:
            print(text,file=sys.stderr)
        sys.exit(1)
