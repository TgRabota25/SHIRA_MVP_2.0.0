from pathlib import Path
import logging,multiprocessing,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
def run():
    try:
        logging.basicConfig(filename=str(ROOT/'premium-windows.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8',force=True)
        import main as app
        import premium_ui
        for name in ('premium_layout','premium_compact'):
            if (ROOT/'app'/(name+'.py')).is_file():__import__(name).install(premium_ui)
        premium_ui.install(app)
        if (ROOT/'app/premium_titlebar.py').is_file():
            import premium_titlebar
            premium_titlebar.install(app)
        import premium_windows
        premium_windows.install(app)
        app.main();return 0
    except Exception:
        logging.exception('Startup failed');print(traceback.format_exc(),flush=True);return 1
if __name__=='__main__':
    multiprocessing.freeze_support();sys.exit(run())
