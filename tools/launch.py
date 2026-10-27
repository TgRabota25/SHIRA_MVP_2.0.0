"""Запуск SHIRA из собранного окружения (вызывается из 02_START.cmd)."""
import logging
import multiprocessing
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))


def run():
    from config import data_dir

    logdir = data_dir() / 'logs'
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(logdir / 'desktop-startup.log'),
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        encoding='utf-8',
        force=True,
    )
    import main as app

    # Необязательные расширения premium-версии — отсутствие не фатально.
    for mod_name in ('studio_ui', 'premium_windows'):
        try:
            mod = __import__(mod_name)
            if hasattr(mod, 'install'):
                mod.install(app)
        except Exception as exc:
            logging.warning('optional module %s not installed: %s', mod_name, exc)
    try:
        import archive_delete
        if hasattr(archive_delete, 'install'):
            archive_delete.install(app)
    except Exception as exc:
        logging.warning('archive_delete not installed: %s', exc)

    app.main()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    try:
        run()
    except Exception:
        text = traceback.format_exc()
        logging.exception('Startup failed')
        try:
            from config import data_dir
            (data_dir() / 'startup-error.txt').write_text(text, encoding='utf-8')
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror('SHIRA — ошибка запуска', text, parent=root)
            root.destroy()
        except Exception:
            print(text, file=sys.stderr)
        sys.exit(1)
