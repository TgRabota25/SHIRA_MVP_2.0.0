from pathlib import Path
import logging,multiprocessing,runpy,sys,traceback
BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
sys.path.insert(0,str(BASE/'app'))
def run():
    if len(sys.argv)>1 and sys.argv[1]=='--frame-preview':
        sys.argv=[str(BASE/'tools/frame_preview.py')]+sys.argv[2:]
        runpy.run_path(str(BASE/'tools/frame_preview.py'),run_name='__main__');return
    from config import data_dir
    folder=data_dir()/'logs';folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=str(folder/'desktop-startup.log'),level=logging.INFO,encoding='utf-8',force=True)
    import main as app
    if '--standard' not in sys.argv:
        import studio_ui,premium_windows
        studio_ui.install(app);premium_windows.install(app)
    import archive_delete
    archive_delete.install(app);app.main()
if __name__=='__main__':
    multiprocessing.freeze_support()
    try:run()
    except Exception:
        text=traceback.format_exc();logging.exception('Startup failed')
        try:
            from config import data_dir
            (data_dir()/'startup-error.txt').write_text(text,encoding='utf-8')
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw();messagebox.showerror('SHIRA',text,parent=root);root.destroy()
        except Exception:print(text,file=sys.stderr)
        sys.exit(1)
