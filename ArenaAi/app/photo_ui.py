"""Окно режима «Фото»: группировка фотографий по разделителям и копирование/перенос."""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import data_dir
from photo import (
    DEFAULT_SEPARATOR_RULES, OP_COPY, OP_MOVE, PhotoRegistry, classify_photos,
    execute_plan, natural_key, split_groups,
)
from platform_ui import icon, open_path


class PhotoWindow:
    def __init__(self, parent, theme=None):
        self.parent = parent
        self.theme = theme or {'palette': {'surface': '#ffffff', 'surface_alt': '#f8fafc', 'ink': '#0f172a', 'muted': '#475569', 'accent': '#2563eb', 'accent_soft': '#eef2ff'}}
        self.palette = self.theme['palette']
        self.win = tk.Toplevel(parent)
        icon(self.win)
        self.win.title('SHIRA — фото: группировка по товарам')
        self.win.geometry('1200x820')
        self.win.minsize(900, 600)
        self.win.resizable(True, True)
        self.win.configure(bg=self.palette['surface_alt'])
        self.win.protocol('WM_DELETE_WINDOW', self.close)
        self.files = []
        self.classifications = {}
        self.groups = []
        self.park = []
        self.session_id = None
        self.registry = None
        self.busy = False
        self._build()

    def _build(self):
        frame = ttk.Frame(self.win, padding=10)
        frame.pack(fill='both', expand=True)

        bar = ttk.Frame(frame)
        bar.pack(fill='x', pady=(0, 6))
        ttk.Button(bar, text='Добавить фото', command=self.add_files).pack(side='left')
        ttk.Button(bar, text='Добавить папку', command=self.add_folder).pack(side='left', padx=4)
        ttk.Button(bar, text='Удалить выбранное', command=self.remove_selected).pack(side='left', padx=4)
        ttk.Button(bar, text='Очистить список', command=self.clear_files).pack(side='left', padx=4)
        ttk.Button(bar, text='Классифицировать', command=self.classify).pack(side='left', padx=12)
        ttk.Button(bar, text='Обновить группировку', command=self.refresh_preview).pack(side='left')

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill='both', expand=True, pady=(0, 6))
        ttk.Label(list_frame, text='Фото для группировки (порядок — естественный по имени файла):').pack(anchor='w')
        self.listbox = tk.Listbox(list_frame, selectmode='extended', height=6,
            bg=self.palette['surface'], fg=self.palette['ink'],
            selectbackground=self.palette['accent_soft'], selectforeground=self.palette['ink'],
            borderwidth=1, relief='solid', highlightthickness=0)
        vs = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vs.set)
        self.listbox.pack(side='left', fill='both', expand=True)
        vs.pack(side='right', fill='y')
        self.count_var = tk.StringVar(value='файлов: 0')
        ttk.Label(list_frame, textvariable=self.count_var).pack(anchor='e')

        # preview of groups
        prev = ttk.LabelFrame(frame, text='Группировка (после классификации)', padding=6)
        prev.pack(fill='both', expand=True, pady=(0, 6))
        cols = ('group', 'kind', 'separator', 'items')
        self.tree = ttk.Treeview(prev, columns=cols, show='headings', height=6, selectmode='none')
        for col, label, width in zip(cols, ['Группа', 'Тип', 'Разделитель', 'Файлы'], [180, 80, 220, 500]):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=80)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.open_group_folder_dbl)

        ops = ttk.Frame(frame)
        ops.pack(fill='x', pady=(0, 6))
        ttk.Label(ops, text='Папка назначения:').pack(side='left')
        self.dest_var = tk.StringVar(value=str(data_dir() / 'photo-out'))
        ttk.Entry(ops, textvariable=self.dest_var, width=52).pack(side='left', padx=4, fill='x', expand=True)
        ttk.Button(ops, text='Обзор…', command=self.choose_dest).pack(side='left', padx=4)
        self.op_var = tk.StringVar(value=OP_COPY)
        ttk.Radiobutton(ops, text='Скопировать (исходники остаются)', variable=self.op_var, value=OP_COPY).pack(side='left', padx=(14, 4))
        ttk.Radiobutton(ops, text='Перенести (удаление после проверенной копии)', variable=self.op_var, value=OP_MOVE).pack(side='left')

        run_frame = ttk.Frame(frame)
        run_frame.pack(fill='x', pady=(0, 6))
        self.run_btn = ttk.Button(run_frame, text='Выполнить операцию', command=self.run_plan)
        self.run_btn.pack(side='left')
        ttk.Button(run_frame, text='Открыть папку назначения', command=self.open_dest).pack(side='left', padx=8)
        self.progress = ttk.Progressbar(run_frame, mode='determinate')
        self.progress.pack(side='right', fill='x', expand=True, padx=8)

        self.log = tk.Text(frame, height=7, wrap='word', state='disabled',
            bg=self.palette['surface'], fg=self.palette['ink'], insertbackground=self.palette['ink'],
            borderwidth=1, relief='solid', highlightthickness=0)
        self.log.pack(fill='both', expand=True, pady=(0, 0))
        self.status = tk.StringVar(value='Готово')
        ttk.Label(frame, textvariable=self.status).pack(anchor='e')

    def log_msg(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def count(self):
        self.count_var.set(f'файлов: {len(self.files)}')
        self.listbox.delete(0, tk.END)
        for p in self.files:
            self.listbox.insert(tk.END, str(p))

    def add_files(self):
        paths = filedialog.askopenfilenames(parent=self.win, title='Выберите фотографии',
                                            filetypes=[('Изображения', '*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.webp'),
                                                       ('Все файлы', '*.*')])
        if paths:
            self.files.extend(Path(p) for p in paths)
            self.count()

    def add_folder(self):
        folder = filedialog.askdirectory(parent=self.win)
        if folder:
            base = Path(folder)
            found = [p for p in base.rglob('*') if p.is_file() and p.suffix.lower() in
                     {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'}]
            self.files.extend(found)
            self.count()

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for index in reversed(sel):
            del self.files[index]
        self.count()

    def clear_files(self):
        self.files = []
        self.count()
        self.classifications = {}
        self.groups = []
        self.park = []
        self.tree.delete(*self.tree.get_children())

    def choose_dest(self):
        folder = filedialog.askdirectory(parent=self.win, title='Папка назначения')
        if folder:
            self.dest_var.set(folder)

    def classify(self):
        if not self.files:
            messagebox.showinfo('SHIRA', 'Добавьте фотографии сначала', parent=self.win)
            return
        if self.busy:
            return
        self.busy = True
        self.run_btn.configure(state='disabled')
        self.log_msg('Классификация фотографий…')
        total = len(self.files)

        def work():
            done = [0]

            def progress(frac):
                self.win.after(0, lambda: self._classify_progress(frac))

            try:
                from config import settings, worker_config
                cfg = worker_config(settings())
                classifications = classify_photos(self.files, cfg, progress=progress)
                self.win.after(0, lambda: self._classify_finished(classifications))
            except Exception as exc:
                self.win.after(0, lambda: self._classify_failed(str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _classify_progress(self, frac):
        self.progress['value'] = int(frac * 100)
        self.status.set(f'Классификация: {int(frac * 100)}%')

    def _classify_finished(self, classifications):
        self.classifications = classifications
        self.busy = False
        self.run_btn.configure(state='normal')
        self.progress['value'] = 100
        ambiguous = [p for p, k in classifications.items() if k == 'ambiguous']
        self.log_msg(f'Классифицировано {len(self.files)} файлов; '
                     f'разделителей: {sum(1 for k in classifications.values() if k in ("A","B"))}; '
                     f'неясных: {len(ambiguous)}')
        self.refresh_preview()

    def _classify_failed(self, error):
        self.busy = False
        self.run_btn.configure(state='normal')
        self.progress['value'] = 0
        messagebox.showerror('Классификация', error, parent=self.win)
        self.log_msg('Ошибка классификации: ' + error)

    def refresh_preview(self):
        self.tree.delete(*self.tree.get_children())
        self.groups, self.park = split_groups(self.files, self.classifications)
        for group in self.groups:
            items = ', '.join(p.name for p in group.all_items)
            self.tree.insert('', tk.END, values=(group.label, group.kind,
                                                 (group.separator.name if group.separator else '—'), items))
        for item, reason in self.park:
            self.tree.insert('', tk.END, values=('Парковка', 'park', item.name, reason))
        self.status.set(f'Групп: {len(self.groups)}, в парковке: {len(self.park)}')
        self.run_btn.configure(state=bool(self.files))

    def open_group_folder_dbl(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        values = self.tree.item(row, 'values')
        if values and values[1] == 'park':
            return
        messagebox.showinfo('SHIRA', 'Откройте папку назначения после выполнения операции', parent=self.win)

    def run_plan(self):
        if not self.files:
            return
        if self.busy:
            return
        if not self.classifications:
            if not messagebox.askyesno('SHIRA', 'Фото не классифицированы. Выполнить без группировки (всё в парковку)?', parent=self.win):
                return
        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showerror('SHIRA', 'Укажите папку назначения', parent=self.win)
            return
        op = self.op_var.get()
        if not self.classifications:
            self.classifications = {}
            self.refresh_preview()
        self.registry = PhotoRegistry()
        groups_count = len(self.groups)
        files_count = len(self.files)
        self.session_id = self.registry.start_session(op, dest, groups_count, files_count)
        self.busy = True
        self.run_btn.configure(state='disabled')
        self.progress['value'] = 0
        self.log_msg(f'Выполнение: {"копирование" if op == OP_COPY else "перенос"} → {dest}')

        def work():
            try:
                done, failed = execute_plan(
                    self.session_id, self.groups, self.park, dest, op, self.registry,
                    progress=lambda d, f, t: self.win.after(0, lambda: self._run_progress(d, f, t)))
                self.win.after(0, lambda: self._run_finished(done, failed))
            except Exception as exc:
                self.win.after(0, lambda: self._run_failed(str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _run_progress(self, done, failed, total):
        self.progress['value'] = int(done / max(1, total) * 100)
        self.status.set(f'Выполнено: {done}, ошибок: {failed} из {total}')

    def _run_finished(self, done, failed):
        self.busy = False
        self.run_btn.configure(state='normal')
        counts = self.registry.counts(self.session_id) if self.registry else {}
        self.log_msg(f'Готово: выполнено {done}, ошибок {failed}. Реестр: {counts}')
        self.status.set('Готово')
        if failed and not done:
            messagebox.showwarning('SHIRA', 'Операция завершена с ошибками. См. лог и реестр photo-v2.sqlite3', parent=self.win)
        elif not failed:
            messagebox.showinfo('SHIRA', 'Операция выполнена', parent=self.win)

    def _run_failed(self, error):
        self.busy = False
        self.run_btn.configure(state='normal')
        self.progress['value'] = 0
        messagebox.showerror('Операция', error, parent=self.win)
        self.log_msg('Ошибка операции: ' + error)

    def open_dest(self):
        dest = self.dest_var.get().strip()
        if dest and Path(dest).exists():
            open_path(dest)

    def close(self):
        if self.busy:
            if not messagebox.askyesno('SHIRA', 'Идёт операция. Закрыть окно?', parent=self.win):
                return
        self.win.destroy()
