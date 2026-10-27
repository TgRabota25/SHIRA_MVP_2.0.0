from pathlib import Path
import logging,multiprocessing,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
def run():
    try:
        logging.basicConfig(filename=str(ROOT/'premium-startup.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8',force=True)
        import main as app
        logging.info('Application: %s',app.__file__)
        if '--standard' not in sys.argv:
            from premium_ui import install
            install(app)
        app.main()
        return 0
    except Exception:
        logging.exception('Startup failed')
        print(traceback.format_exc(),flush=True)
        return 1
if __name__=='__main__':
    multiprocessing.freeze_support()
    sys.exit(run())
