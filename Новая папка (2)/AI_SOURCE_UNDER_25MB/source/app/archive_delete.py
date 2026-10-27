"""Explicit archive deletion. File operations run only after UI confirmation."""
import os,sys,uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox

def remove_records(db,keys):
    for key in keys:
        row=db.execute('SELECT state FROM tasks WHERE id=?',(key,)).fetchone()
        if row and row[0]=='running':raise RuntimeError('Остановите обработку')
    for key in keys:
        for table in ('hits','gaps','audit'):
            db.execute('DELETE FROM '+table+' WHERE task_id=?',(key,))
        db.execute('DELETE FROM tasks WHERE id=?',(key,))

def recycle(path):
    if sys.platform!='win32':raise RuntimeError('Удаление файлов доступно только в Windows')
    import ctypes
    from ctypes import wintypes
    class Operation(ctypes.Structure):
        _fields_=[('hwnd',wintypes.HWND),('wFunc',wintypes.UINT),('pFrom',wintypes.LPCWSTR),('pTo',wintypes.LPCWSTR),('fFlags',wintypes.WORD),('aborted',wintypes.BOOL),('mapping',ctypes.c_void_p),('title',wintypes.LPCWSTR)]
    shell=ctypes.WinDLL('shell32',use_last_error=True)
    shell.SHFileOperationW.argtypes=[ctypes.POINTER(Operation)]
    shell.SHFileOperationW.restype=ctypes.c_int
    buf=ctypes.create_unicode_buffer(str(path)+'\0')
    op=Operation();op.wFunc=3;op.pFrom=ctypes.cast(buf,wintypes.LPCWSTR)
    op.fFlags=0x0040|0x4000
    result=shell.SHFileOperationW(ctypes.byref(op))
    if result or op.aborted:raise RuntimeError('Windows отменил удаление или вернул ошибку '+str(result))
    if path.exists():raise RuntimeError('Файл остался на месте; запись сохранена')

def samepath(value):return os.path.normcase(os.path.abspath(value))

def targets(store,keys,with_files):
    with store.db() as db:
        selected=[dict(row) for key in keys for row in db.execute('SELECT * FROM tasks WHERE id=?',(key,))]
        paths={samepath(row['path']) for row in selected}
        rows=[dict(row) for row in db.execute('SELECT * FROM tasks') if samepath(row['path']) in paths] if with_files else selected
    return rows

def install(module):
    original=module.Application
    class DeleteApplication(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.tree.bind('<Delete>',self.delete_ui)
        def context(self,event):
            row=self.tree.identify_row(event.y)
            if not row:return 'break'
            if row not in self.selected():self.tree.selection_set(row)
            menu=tk.Menu(self.root,tearoff=False)
            for label,fn in [('Проверить',self.review),('Копировать строки',self.copy_rows),('Копировать номера',self.copy_numbers),('Копировать пути',self.copy_paths),('Копировать файлы для письма',self.copy_selected_files),('Показать в папке',self.reveal),('Повторить выбранные',self.retry),('Повторить пропуски',self.retry_gaps_ui)]:menu.add_command(label=label,command=fn)
            menu.add_separator();menu.add_command(label='Удалить…',accelerator='Del',command=self.delete_ui)
            try:menu.tk_popup(event.x_root,event.y_root)
            finally:menu.grab_release();menu.destroy()
            return 'break'
        def delete_ui(self,event=None):
            if self.busy or self.engine.running():
                messagebox.showinfo('Удаление','Сначала завершите обработку и фоновые операции.',parent=self.root);return 'break'
            keys=tuple(self.selected())
            if not keys:return 'break'
            win=tk.Toplevel(self.root);win.withdraw();win.title('Удаление из архива SHIRA');win.transient(self.root)
            frame=ttk.Frame(win,padding=22);frame.pack(fill='both',expand=True)
            ttk.Label(frame,text=f'Выбрано записей: {len(keys)}',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(0,12))
            ttk.Label(frame,text='Выберите действие. Перед выполнением будет показан список.',wraplength=520).pack(anchor='w')
            choice=tk.StringVar(value='info')
            ttk.Radiobutton(frame,text='Только информацию из базы — исходные файлы оставить',variable=choice,value='info').pack(anchor='w',pady=(14,6))
            ttk.Radiobutton(frame,text='Видеофайл и всю информацию о нём из базы',variable=choice,value='both').pack(anchor='w',pady=6)
            ttk.Label(frame,text='Для удаления файла используется Windows с запросом корзины. Если корзина недоступна, Windows может запросить безвозвратное удаление. При отмене запись сохраняется.',wraplength=520).pack(anchor='w',pady=(10,14))
            selected={'value':None}
            def accept():selected['value']=choice.get();win.destroy()
            bar=ttk.Frame(frame);bar.pack(fill='x')
            ttk.Button(bar,text='Продолжить',command=accept).pack(side='left')
            cancel=ttk.Button(bar,text='Отмена',command=win.destroy);cancel.pack(side='right')
            win.bind('<Escape>',lambda e:win.destroy());win.update_idletasks();win.deiconify();win.grab_set();cancel.focus_set()
            self.busy+=1
            try:
                self.root.wait_window(win)
                mode=selected['value']
                if mode is None:return 'break'
                rows=targets(self.store,keys,mode=='both')
                if not rows:return 'break'
                if any(row['state']=='running' for row in rows):raise RuntimeError('Есть обрабатываемые записи. Сначала остановите обработку.')
                groups={}
                for row in rows:groups.setdefault(row['path'],[]).append(row['id'])
                listing='\n'.join(groups)
                text=f'Записей: {len(rows)}. Файлов: {len(groups)}.\n\n'+listing[:3500]
                text+='\n\nФайлы и связанные записи будут удалены.' if mode=='both' else '\n\nБудет удалена только информация. Файлы останутся.'
                if not messagebox.askyesno('Подтвердите удаление',text,parent=self.root,default='no'):return 'break'
                from config import data_dir
                folder=data_dir()/'backups';folder.mkdir(parents=True,exist_ok=True)
                backup=folder/('before-delete-'+uuid.uuid4().hex+'.sqlite3')
                self.store.backup(backup)
                errors=[];count=0
                for path,ids in groups.items():
                    try:
                        with self.store.db() as db:
                            db.execute('BEGIN IMMEDIATE')
                            if db.execute("SELECT 1 FROM tasks WHERE state='running' LIMIT 1").fetchone():raise RuntimeError('Обработка возобновилась; удаление запрещено')
                            for key in ids:
                                current=db.execute('SELECT path FROM tasks WHERE id=?',(key,)).fetchone()
                                if not current or current[0]!=path:raise RuntimeError('Запись изменилась; повторите выбор')
                            if mode=='both':
                                file=Path(path)
                                if file.is_symlink():raise RuntimeError('Удаление символических ссылок запрещено')
                                if file.exists():
                                    if not file.is_file():raise RuntimeError('Путь не является файлом')
                                    recycle(file)
                            remove_records(db,ids)
                        count+=len(ids)
                    except Exception as exc:errors.append(path+': '+str(exc))
                self.refresh();self.status.set(f'Удалено записей: {count}. Бэкап: {backup}')
                if errors:messagebox.showwarning('Удаление завершено не полностью','\n'.join(errors)[:3500]+f'\n\nБэкап базы: {backup}\nФайл и БД не являются одной транзакцией: при ошибке БД после удаления файла проверьте бэкап.',parent=self.root)
            except Exception as exc:messagebox.showerror('Удаление',str(exc),parent=self.root)
            finally:self.busy=max(0,self.busy-1)
            return 'break'
    module.Application=DeleteApplication
