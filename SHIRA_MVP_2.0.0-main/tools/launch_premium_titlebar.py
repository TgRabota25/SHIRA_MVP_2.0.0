from pathlib import Path
import logging,multiprocessing,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
def run():
    try:
        logging.basicConfig(filename=str(ROOT/'premium-titlebar.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8',force=True)
        import main as app
        import premium_ui
        if (ROOT/'app/premium_layout.py').is_file():
            import premium_layout
            premium_layout.install(premium_ui)
        premium_ui.install(app)
        import premium_titlebar
        premium_titlebar.install(app)
        app.main()
        return 0
    except Exception:
        logging.exception('Startup failed');print(traceback.format_exc(),flush=True);return 1
if __name__=='__main__':
    multiprocessing.freeze_support();sys.exit(run())
