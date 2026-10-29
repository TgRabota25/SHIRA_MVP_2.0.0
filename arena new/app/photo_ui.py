"""Окно режима «Фото»: группировка фотографий по разделителям и копирование/перенос.
Современный визуал: карточки, акцентные кнопки, статус-бэджи, мягкие границы.
"""
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
from theme import SPACE, stat_card


class PhotoWindow:
    def __init__(self, parent, theme=None):
        self.parent = parent
        self.theme = theme or {'palette': {'surface': '#ffffff', 'surface_alt': '#f3f4f6', 'ink': '#0f172a', 'muted': '#64748b', 'accent': '#2563eb', 'accent_soft': '#eef2ff', 'border': '#e2e8f0'}}
        self.palette = self.theme['palette']
        self.win = tk.Toplevel(parent)
        icon(self.win)
        self.win.title('SHIRA — фото: группировка по товарам')
        self.win.geometry('1300x850')
        self.win.minsize(1000, 650)
        self.win.resizable(True, True)
        self.win.configure(bg=self.palette['canvas'] if 'canvas' in self.palette else self.palette['surface_alt'])
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
        pal = self.palette
        # Корневой контейнер
        root = tk.Frame(self.win, bg=pal.get('canvas', pal['surface_alt']))
        root.pack(fill='both', expand=True)

        # Шапка окна
        header = tk.Frame(root, bg=pal.get('canvas', pal['surface_alt']), height=56)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text='SHIRA • Фото', bg=pal.get('canvas', pal['surface_alt']),
                 fg=pal['ink'], font=('Segoe UI', 14, 'bold')).pack(side='left', padx=SPACE['4'], pady=14)

        # Тело: слева список, справа группы
        body = tk.Frame(root, bg=pal.get('canvas', pal['surface_alt']))
        body.pack(fill='both', expand=True, padx=SPACE['4'], pady=SPACE['4'])

        # --- Левая колонка: список файлов ---
        left = tk.Frame(body, bg=pal.get('canvas', pal['surface_alt']))
        left.pack(side='left', fill='both', expand=True, padx=(0, SPACE['3']))

        # Верхняя панель действий
        bar = tk.Frame(left, bg=pal.get('canvas', pal['surface_alt']))
        bar.pack(fill='x', pady=(0, SPACE['3']))
        btn_conf = dict(bg=pal['surface'], fg=pal['ink'], font=('Segoe UI', 10), bd=1,
                        highlightbackground=pal['border'], highlightthickness=1,
                        cursor='hand2', padx=12, pady=8)
        tk.Button(bar, text='Добавить фото', command=self.add_files, **btn_conf).pack(side='left', padx=(0, SPACE['2']))
        tk.Button(bar, text='Добавить папку', command=self.add_folder, **btn_conf).pack(side='left', padx=(0, SPACE['2']))
        tk.Button(bar, text='Удалить выбранное', command=self.remove_selected, **btn_conf).pack(side='left', padx=(0, SPACE['2']))
        tk.Button(bar, text='Очистить список', command=self.clear_files, **btn_conf).pack(side='left', padx=(0, SPACE['4']))
        tk.Button(bar, text='Классифицировать', command=self.classify, bg=pal['accent_btn'], fg='#ffffff',
                  font=('Segoe UI', 10, 'bold'), bd=0, highlightthickness=0, cursor='hand2',
                  padx=16, pady=8).pack(side='left')

        # Карточка со списком
        list_card = tk.Frame(left, bg=pal['surface'], highlightbackground=pal['border'], highlightthickness=1, bd=0)
        list_card.pack(fill='both', expand=True)
        list_inner = tk.Frame(list_card, bg=pal['surface'])
        list_inner.pack(fill='both', expand=True, padx=SPACE['3'], pady=SPACE['3'])
        tk.Label(list_inner, text='Фото для группировки (порядок — естественный по имени файла)',
                 bg=pal['surface'], fg=pal['muted'], font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, SPACE['2']))
        self.listbox = tk.Listbox(list_inner, selectmode='extended', height=8,
            bg=pal['surface'], fg=pal['ink'], selectbackground=pal['accent_soft'],
            selectforeground=pal['ink'], borderwidth=0, highlightthickness=0, font=('Segoe UI', 10))
        self.listbox.pack(fill='both', expand=True)
        vs = ttk.Scrollbar(list_inner, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vs.set)
        vs.pack(side='right', fill='y')
        self.count_var = tk.StringVar(value='файлов: 0')
        tk.Label(left, textvariable=self.count_var, bg=pal.get('canvas', pal['surface_alt']),
                 fg=pal['muted'], font=('Segoe UI', 9)).pack(anchor='e', pady=(SPACE['1'], 0))

        # --- Правая колонка: группы и операции ---
        right = tk.Frame(body, bg=pal.get('canvas', pal['surface_alt']), width=420)
        right.pack(side='right', fill='y')
        right.pack_propagate(False)

        # Карточка группировки
        group_card = tk.Frame(right, bg=pal['surface'], highlightbackground=pal['border'], highlightthickness=1, bd=0)
        group_card.pack(fill='both', expand=True, pady=(0, SPACE['3']))
        group_inner = tk.Frame(group_card, bg=pal['surface'])
        group_inner.pack(fill='both', expand=True, padx=SPACE['3'], pady=SPACE['3'])
        tk.Label(group_inner, text='Группировка (после классификации)',
                 bg=pal['surface'], fg=pal['muted'], font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, SPACE['2']))
        cols = ('group', 'kind', 'separator', 'items')
        self.tree = ttk.Treeview(group_inner, columns=cols, show='headings', height=8, selectmode='none')
        for col, label, width in zip(cols, ['Группа', 'Тип', 'Разделитель', 'Файлы'], [120, 60, 150, 280]):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=60)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.open_group_folder_dbl)

        # Операции
        ops_card = tk.Frame(right, bg=pal['surface'], highlightbackground=pal['border'], highlightthickness=1, bd=0)
        ops_card.pack(fill='x')
        ops_inner = tk.Frame(ops_card, bg=pal['surface'])
        ops_inner.pack(fill='x', padx=SPACE['3'], pady=SPACE['3'])
        tk.Label(ops_inner, text='Папка назначения:', bg=pal['surface'], fg=pal['ink'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, SPACE['2']))
        dest_row = tk.Frame(ops_inner, bg=pal['surface'])
        dest_row.pack(fill='x', pady=(0, SPACE['3']))
        self.dest_var = tk.StringVar(value=str(data_dir() / 'photo-out'))
        dest_entry = tk.Entry(dest_row, textvariable=self.dest_var, bg=pal['surface'], fg=pal['ink'],
                              bd=1, highlightbackground=pal['border'], highlightthickness=1,
                              font=('Segoe UI', 10))
        dest_entry.pack(side='left', fill='x', expand=True, padx=(0, SPACE['2']))
        tk.Button(dest_row, text='Обзор…', command=self.choose_dest, bg=pal['neutral_bg'], fg=pal['neutral_text'],
                  font=('Segoe UI', 9), bd=0, highlightthickness=0, cursor='hand2', padx=12, pady=6).pack(side='left')
        # Радиокнопки операции
        self.op_var = tk.StringVar(value=OP_COPY)
        op_frame = tk.Frame(ops_inner, bg=pal['surface'])
        op_frame.pack(fill='x', pady=(SPACE['2'], 0))
        tk.Radiobutton(op_frame, text='Скопировать (исходники остаются)', variable=self.op_var, value=OP_COPY,
                       bg=pal['surface'], fg=pal['ink'], font=('Segoe UI', 10), selectcolor=pal['surface'],
                       activebackground=pal['surface'], cursor='hand2').pack(anchor='w', pady=1)
        tk.Radiobutton(op_frame, text='Перенести (после проверенной копии)', variable=self.op_var, value=OP_MOVE,
                       bg=pal['surface'], fg=pal['ink'], font=('Segoe UI', 10), selectcolor=pal['surface'],
                       activebackground=pal['surface'], cursor='hand2').pack(anchor='w', pady=1)

        # Кнопка выполнения и прогресс
        run_frame = tk.Frame(right, bg=pal.get('canvas', pal['surface_alt']))
        run_frame.pack(fill='x', pady=(SPACE['3'], 0))
        self.run_btn = tk.Button(run_frame, text='Выполнить операцию', command=self.run_plan,
                                 bg=pal['success_btn'], fg='#ffffff', font=('Segoe UI', 10, 'bold'),
                                 bd=0, highlightthickness=0, cursor='hand2', padx=16, pady=10)
        self.run_btn.pack(fill='x')
        self.progress = ttk.Progressbar(run_frame, mode='determinate')
        self.progress.pack(fill='x', pady=(SPACE['2'], 0))

        # Лог
        log_card = tk.Frame(right, bg=pal['surface'], highlightbackground=pal['border'], highlightthickness=1, bd=0)
        log_card.pack(fill='both', expand=True, pady=(SPACE['3'], 0))
        log_inner = tk.Frame(log_card, bg=pal['surface'])
        log_inner.pack(fill='both', expand=True, padx=SPACE['3'], pady=SPACE['3'])
        tk.Label(log_inner, text='Лог операций', bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, SPACE['2']))
        self.log = tk.Text(log_inner, height=8, wrap='word', state='disabled',
            bg=pal['surface'], fg=pal['ink'], insertbackground=pal['ink'],
            borderwidth=0, highlightthickness=0, font=('Consolas', 9))
        self.log.pack(fill='both', expand=True)
        self.status = tk.StringVar(value='Готово')
        tk.Label(log_inner, textvariable=self.status, bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 8)).pack(anchor='e', pady=(SPACE['1'], 0))

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
                                            filetypes=[('Изображения', '*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp'),
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
