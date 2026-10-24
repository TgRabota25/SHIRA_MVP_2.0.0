from pathlib import Path
import ast,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'app/premium_windows.py'
old="win.geometry(f'{width}x{height}{x+max(0,(sw-width)//2):+d}{y+max(0,(sh-height)//2):+d}')"
new="if oldw>limitw or oldh>limith:win.geometry(f'{width}x{height}')"
try:
    if not path.is_file():raise RuntimeError('app/premium_windows.py not found. Install the windows package first.')
    src=path.read_text(encoding='utf-8')
    if '# no-delayed-centering-v1' in src:
        print('[OK] Fix already installed. Start 13_START_PREMIUM_WINDOWS.cmd.');sys.exit(0)
    if old not in src:raise RuntimeError('Different module version. No files changed; provide app/premium_windows.py.')
    updated=src.replace(old,new,1)
    updated=updated.replace("root.after(180,maximize)","root.after_idle(maximize)",1)
    updated+='\n# no-delayed-centering-v1\n'
    ast.parse(updated)
    backup=path.with_name('premium_windows.py.before-no-centering')
    if not backup.exists():shutil.copy2(path,backup)
    temp=path.with_suffix('.py.tmp')
    temp.write_text(updated,encoding='utf-8');temp.replace(path)
    print('[OK] Delayed centering removed. Restart via 13_START_PREMIUM_WINDOWS.cmd.')
    print('[INFO] Oversized dialogs can still be resized to fit; their position is not changed.')
except Exception as exc:
    print('[ERROR] '+str(exc));sys.exit(1)
