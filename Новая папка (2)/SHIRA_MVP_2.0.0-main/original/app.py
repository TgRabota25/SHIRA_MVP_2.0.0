"""
app.py — SHIRA. VS Code-стиль.
"""
import os
import sys
import json
import queue
import shutil
import subprocess
import multiprocessing
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import customtkinter as ctk

import base64 as _brand_b64
import io as _brand_io
from PIL import Image as _BrandImage, ImageTk as _BrandImageTk
_SHIRA_LOGO = "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"

def _brand_image(owner, size):
    image = _BrandImage.open(_brand_io.BytesIO(_brand_b64.b64decode(_SHIRA_LOGO))).convert("RGBA")
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))

def _brand_window(owner):
    def apply():
        try:
            image = _BrandImage.open(_brand_io.BytesIO(_brand_b64.b64decode(_SHIRA_LOGO))).convert("RGBA")
            owner._brand_photo = _BrandImageTk.PhotoImage(image, master=owner)
            owner.iconphoto(True, owner._brand_photo)
        except Exception:
            pass
    owner.after(400, apply)



from scanner_core import (ScannerEngine, default_config, ALL_METHODS,
                          VideoCache, list_videos,
                          check_license, activate_license,
                          LICENSE_PERIOD_DAYS,
                          _app_dir, _resource_path,
                          _default_data_dir, _ensure_dir,
                          auto_detect_config, apply_performance_mode,
                          check_free_space)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    HAS_DND = False

SETTINGS_DIR = _default_data_dir()
_ensure_dir(SETTINGS_DIR)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
ERROR_LOG = os.path.join(SETTINGS_DIR, "error.log")


# ================= ERROR LOG =================

def _install_excepthook():
    def hook(exc_type, exc_value, exc_tb):
        try:
            with open(ERROR_LOG, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"{datetime.now()}  ({exc_type.__name__})\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


# ================= ТЕМЫ =================

THEMES = {'dark': {'bg': '#1F2024', 'sidebar': '#25262B', 'titlebar': '#292B31', 'toolbar': '#25262B', 'tab_active': '#1F2024', 'tab_inactive': '#2B2D34', 'input_bg': '#30323A', 'border': '#383B44', 'border_light': '#484C57', 'hover': '#32353D', 'hover_light': '#3B3E48', 'accent': '#3479BC', 'accent_hover': '#286AA9', 'success': '#74C6AA', 'warn': '#DDC080', 'error': '#E89996', 'text': '#E0E3EA', 'text_dim': '#A5ACB9', 'text_bright': '#ffffff', 'chip_on': '#3479BC', 'chip_off': '#30323A', 'dock_bg': '#222329'}, 'light': {'bg': '#FAFBFD', 'sidebar': '#F1F3F7', 'titlebar': '#EBEEF4', 'toolbar': '#F1F3F7', 'tab_active': '#FAFBFD', 'tab_inactive': '#E9EDF3', 'input_bg': '#FFFFFF', 'border': '#DDE2EB', 'border_light': '#C7CFDB', 'hover': '#E6EBF3', 'hover_light': '#DCE4F0', 'accent': '#276BA5', 'accent_hover': '#20598B', 'success': '#226E54', 'warn': '#856119', 'error': '#AC4545', 'text': '#28303D', 'text_dim': '#596578', 'text_bright': '#000000', 'chip_on': '#276BA5', 'chip_off': '#E3E8F0', 'dock_bg': '#EAEFF5'}}

REF_WIDTH = 1280
REF_HEIGHT = 800
SCALE_MIN = 0.75
SCALE_MAX = 1.25

BASE = {
    'titlebar_h': 56, 'toolbar_h': 44, 'status_h': 26,
    'sidebar_w': 340, 'pad': 8, 'radius': 6,
    'entry_h': 26, 'btn_h': 26, 'btn_h_big': 30, 'gap': 6,
    'chip_h': 22,
}

FONT_BASE = {
    'title':    ('Segoe UI', 14, 'bold'),
    'section':  ('Segoe UI', 10, 'bold'),
    'label':    ('Segoe UI', 9,  'normal'),
    'entry':    ('Segoe UI', 9,  'normal'),
    'button':   ('Segoe UI', 9,  'normal'),
    'button_b': ('Segoe UI', 9,  'bold'),
    'checkbox': ('Segoe UI', 9,  'normal'),
    'table':    ('Segoe UI', 9,  'normal'),
    'table_h':  ('Segoe UI', 9,  'bold'),
    'log':      ('Consolas', 9,  'normal'),
    'status':   ('Segoe UI', 9,  'normal'),
    'chip':     ('Segoe UI', 8,  'normal'),
}

SEARCH_DEBOUNCE_MS = 250


def load_settings():
    cfg = default_config()
    for candidate in (SETTINGS_FILE, SETTINGS_FILE + '.bak'):
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                cfg.update(loaded)
                break
        except (OSError, json.JSONDecodeError):
            continue
    cfg.setdefault('theme', 'dark')
    cfg.setdefault('sort_column', None)
    cfg.setdefault('sort_reverse', False)
    return cfg


def save_settings(cfg):
    tmp = SETTINGS_FILE + f'.tmp-{os.getpid()}'
    try:
        _ensure_dir(os.path.dirname(SETTINGS_FILE))
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.isfile(SETTINGS_FILE):
            shutil.copy2(SETTINGS_FILE, SETTINGS_FILE + '.bak')
        os.replace(tmp, SETTINGS_FILE)
    except (OSError, TypeError, ValueError) as e:
        print("Не удалось сохранить настройки:", e)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


# ================= АКТИВАЦИЯ =================

def run_activation_window(reason_msg, allow_cancel=True):
    result = {'success': False, 'days_left': 0, 'closed': False}
    P = THEMES['dark']

    win = ctk.CTk()
    win.title("SHIRA — Активация")
    win.geometry("520x440")
    win.resizable(False, False)
    win.configure(fg_color=P['bg'])
    ctk.set_appearance_mode('dark')

    _brand_window(win)
    win._brand_image = _brand_image(win, 46)
    ctk.CTkLabel(win, text="SHIRA", image=win._brand_image, compound="left",
        padx=12, font=ctk.CTkFont("Segoe UI", 18, "bold"),
        text_color=P['text']).pack(pady=(16, 0))
    ctk.CTkLabel(win, text="Активация лицензии",
                 font=ctk.CTkFont('Segoe UI', 16, 'bold'),
                 text_color=P['text']).pack(pady=(24, 6))
    ctk.CTkLabel(win, text=reason_msg,
                 font=ctk.CTkFont('Segoe UI', 10),
                 text_color=P['text_dim'],
                 wraplength=440, justify="center").pack(pady=(0, 16))
    ctk.CTkLabel(win, text="Лицензионный ключ:",
                 font=ctk.CTkFont('Segoe UI', 9),
                 text_color=P['text_dim']).pack(anchor="w", padx=36)

    entry = ctk.CTkEntry(win, height=32, corner_radius=3,
                         font=ctk.CTkFont('Consolas', 11),
                         fg_color=P['input_bg'],
                         border_color=P['border_light'],
                         text_color=P['text'])
    entry.pack(fill="x", padx=36, pady=(4, 8))
    entry.focus_set()

    try:
        inner = entry._entry
    except AttributeError:
        inner = entry

    def _paste(_e=None):
        try:
            text = win.clipboard_get()
        except Exception:
            return "break"
        if not text:
            return "break"
        text = "".join(text.split())
        try:
            if inner.selection_present():
                inner.delete("sel.first", "sel.last")
        except Exception:
            pass
        inner.insert("insert", text)
        return "break"

    def _copy(_e=None):
        try:
            if inner.selection_present():
                win.clipboard_clear()
                win.clipboard_append(inner.selection_get())
        except Exception:
            pass
        return "break"

    def _cut(_e=None):
        try:
            if inner.selection_present():
                win.clipboard_clear()
                win.clipboard_append(inner.selection_get())
                inner.delete("sel.first", "sel.last")
        except Exception:
            pass
        return "break"

    def _sel_all(_e=None):
        try:
            inner.select_range(0, "end")
            inner.icursor("end")
        except Exception:
            pass
        return "break"

    for w in (entry, inner):
        w.bind("<Control-v>", _paste); w.bind("<Control-V>", _paste)
        w.bind("<Control-Insert>", _paste); w.bind("<Shift-Insert>", _paste)
        w.bind("<Control-c>", _copy); w.bind("<Control-C>", _copy)
        w.bind("<Control-x>", _cut); w.bind("<Control-X>", _cut)
        w.bind("<Control-a>", _sel_all); w.bind("<Control-A>", _sel_all)

    ctx = tk.Menu(win, tearoff=0, bg=P['input_bg'], fg=P['text'],
                  activebackground=P['accent'],
                  activeforeground='#ffffff',
                  bd=0, relief="flat", font=("Segoe UI", 9))
    ctx.add_command(label="Вставить", command=_paste)
    ctx.add_command(label="Копировать", command=_copy)
    ctx.add_command(label="Вырезать", command=_cut)
    ctx.add_separator()
    ctx.add_command(label="Выделить всё", command=_sel_all)

    def _ctx_show(e):
        try:
            ctx.tk_popup(e.x_root, e.y_root)
        finally:
            try:
                ctx.grab_release()
            except Exception:
                pass
        return "break"

    entry.bind("<Button-3>", _ctx_show)
    inner.bind("<Button-3>", _ctx_show)

    err_lbl = ctk.CTkLabel(win, text="",
                           font=ctk.CTkFont('Segoe UI', 9),
                           text_color=P['error'])
    err_lbl.pack(pady=(0, 4))

    btns = ctk.CTkFrame(win, fg_color="transparent")
    btns.pack(fill="x", padx=36, pady=(4, 16))

    def try_activate(_e=None):
        ok, msg = activate_license(entry.get().strip())
        if ok:
            lic = check_license()
            result['success'] = True
            result['days_left'] = lic.get('days_left', LICENSE_PERIOD_DAYS)
            win.destroy()
        else:
            err_lbl.configure(text=msg)
        return "break"

    def on_cancel():
        result['success'] = False
        result['closed'] = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_cancel)

    ctk.CTkButton(btns, text="Активировать", height=32, corner_radius=3,
                  font=ctk.CTkFont('Segoe UI', 10, 'bold'),
                  fg_color=P['accent'], hover_color=P['accent_hover'],
                  command=try_activate).pack(side="left", fill="x",
                                              expand=True, padx=(0, 4))

    if allow_cancel:
        ctk.CTkButton(btns, text="Отмена", height=32, corner_radius=3,
                      font=ctk.CTkFont('Segoe UI', 9),
                      fg_color=P['input_bg'],
                      hover_color=P['hover_light'],
                      text_color=P['text'], border_width=1,
                      border_color=P['border'],
                      command=on_cancel).pack(side="left", fill="x",
                                               expand=True, padx=(4, 0))

    entry.bind("<Return>", try_activate)
    ctk.CTkLabel(win,
                 text=f"Лицензия действует {LICENSE_PERIOD_DAYS} дней",
                 font=ctk.CTkFont('Segoe UI', 8),
                 text_color=P['text_dim']).pack(pady=(0, 12))

    win.mainloop()
    return result['success'], result['days_left']


# ================= БАЗОВЫЙ КЛАСС (DnD) =================

if HAS_DND:
    class _BaseApp(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            super().__init__()
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass
else:
    class _BaseApp(ctk.CTk):
        pass


# ================= ГЛАВНОЕ ОКНО =================

class App(_BaseApp):
    def __init__(self, days_left=0):
        super().__init__()

        self.days_left = days_left
        self.cfg = load_settings()
        self.theme_name = self.cfg.get('theme', 'dark')
        self.palette = THEMES[self.theme_name]

        ctk.set_appearance_mode(self.theme_name)
        ctk.set_default_color_theme("blue")

        self.engine = None
        self.msg_queue = queue.Queue()
        self.saved_results = []
        self.saved_log_lines = []
        self.current_filter = ""
        self.filter_mode = 'all'
        self.row_map = {}
        self.current_scanning_file = ""

        self.sort_column = self.cfg.get('sort_column')
        self.sort_reverse = bool(self.cfg.get('sort_reverse', False))

        self.COL_MAP = {
            'file':        'Название файла',
            'number':      'Внутренний номер',
            'marketplace': 'Маркетплейс',
            'qr':          'QR-код',
            'time':        'Время (с)',
            'source':      'Источник',
            'date':        'Дата и время создания',
        }
        self._heading_labels = {
            'file':        'Файл',
            'number':      'Номер',
            'marketplace': 'Маркетплейс',
            'qr':          'QR-код',
            'time':        'Время',
            'source':      'Источник',
            'date':        'Создан',
        }

        self._search_job = None

        self.scale = 1.0
        self._resize_job = None
        self._last_size = (0, 0)
        self._ui_ready = False

        self.title("SHIRA")
        self.geometry(f"{REF_WIDTH}x{REF_HEIGHT}")
        self.minsize(1000, 650)
        self.configure(fg_color=self.palette['bg'])

        try:
            icon = _resource_path("icon.ico")
            if os.path.isfile(icon):
                self.iconbitmap(icon)
        except Exception:
            pass

        _brand_window(self)
        self._build_ui()
        self._bind_hotkeys()
        self._setup_drag_and_drop()

        self.after(200, self._initial_scale)
        self.after(250, self._load_history_from_db)
        self.after(400, self._autofind_folder)
        self._poll_queue()
        self.bind("<Configure>", self._on_configure)

    # ================= ГОРЯЧИЕ КЛАВИШИ =================

    def _bind_hotkeys(self):
        self.bind("<F5>", lambda e: self._on_start())
        self.bind("<Escape>", lambda e: self._on_stop())
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Control-F>", lambda e: self._focus_search())
        self.bind("<Control-e>", lambda e: self._open_excel())
        self.bind("<Control-E>", lambda e: self._open_excel())
        self.bind("<Control-r>", lambda e: self._refresh_history(silent=False))
        self.bind("<Control-R>", lambda e: self._refresh_history(silent=False))
        self.bind("<Control-s>", lambda e: self._export_csv())
        self.bind("<Control-S>", lambda e: self._export_csv())

    def _focus_search(self):
        try:
            self.search_entry.focus_set()
            self.search_entry.select_range(0, "end")
        except Exception:
            pass

    # ================= DRAG & DROP =================

    def _setup_drag_and_drop(self):
        if not HAS_DND:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        try:
            raw = event.data
            paths = self.tk.splitlist(raw)
        except Exception:
            return

        if not paths:
            return

        first = paths[0]

        if os.path.isdir(first):
            self.folder_var.set(first)
            self._append_log(f"Drag&Drop: папка {first}")
            self.progress_label.configure(
                text=f"Папка: {os.path.basename(first) or first}")
        elif os.path.isfile(first):
            parent = os.path.dirname(first)
            self.folder_var.set(parent)
            self._append_log(f"Drag&Drop: {len(paths)} файл(ов) → {parent}")
            self.progress_label.configure(
                text=f"Файлов перетащено: {len(paths)}")

    # ================= ПОСТРОЕНИЕ UI =================

    def _build_ui(self):
        P = self.palette
        self._ui_ready = False

        # TITLEBAR
        self.titlebar = ctk.CTkFrame(self, fg_color=P['titlebar'],
                                     corner_radius=0,
                                     height=BASE['titlebar_h'])
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)

        self.brand_box = ctk.CTkFrame(self.titlebar, width=38, height=38,
            corner_radius=8, fg_color=P['input_bg'], border_width=1,
            border_color=P['border'])
        self.brand_box.pack(side="left", padx=(12, 0), pady=4)
        self.brand_box.pack_propagate(False)
        self.brand_image = _brand_image(self, 30)
        self.brand_icon = ctk.CTkLabel(self.brand_box, text="", image=self.brand_image)
        self.brand_icon.pack(expand=True)
        self.logo_lbl = ctk.CTkLabel(self.titlebar, text="SHIRA",
            font=ctk.CTkFont(*FONT_BASE['title']), text_color=P['text'])
        self.logo_lbl.pack(side="left", padx=(10, 12))

        self.version_lbl = ctk.CTkLabel(
            self.titlebar, text="v1.6",
            font=ctk.CTkFont('Segoe UI', 9),
            text_color=P['text_dim'])
        self.version_lbl.pack(side="left")

        self.status_badge = ctk.CTkLabel(
            self.titlebar, text="● ГОТОВ",
            font=ctk.CTkFont('Segoe UI', 9, 'bold'),
            text_color=P['success'])
        self.status_badge.pack(side="right", padx=10)

        self.license_lbl = ctk.CTkLabel(
            self.titlebar, text=f"🔑 {self.days_left} дн.",
            font=ctk.CTkFont('Segoe UI', 9),
            text_color=P['success'] if self.days_left > 7 else P['warn'])
        self.license_lbl.pack(side="right", padx=(0, 10))

        self.theme_btn = ctk.CTkButton(
            self.titlebar,
            text="☀" if self.theme_name == 'dark' else "🌙",
            width=30, height=24, corner_radius=3,
            font=ctk.CTkFont('Segoe UI', 11),
            fg_color="transparent", hover_color=P['hover'],
            text_color=P['text'],
            command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=(0, 6))

        # TOOLBAR
        self.toolbar = ctk.CTkFrame(self, fg_color=P['toolbar'],
                                    corner_radius=0,
                                    height=BASE['toolbar_h'])
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        self.folder_lbl = ctk.CTkLabel(
            self.toolbar, text="Папка:",
            font=ctk.CTkFont(*FONT_BASE['label']),
            text_color=P['text_dim'])
        self.folder_lbl.pack(side="left", padx=(10, 6), pady=8)

        self.folder_var = tk.StringVar(value=self.cfg.get('video_folder', ''))
        self.folder_entry = ctk.CTkEntry(
            self.toolbar, textvariable=self.folder_var,
            height=BASE['entry_h'], corner_radius=BASE['radius'],
            fg_color=P['input_bg'], border_color=P['border_light'],
            text_color=P['text'], font=ctk.CTkFont(*FONT_BASE['entry']))
        self.folder_entry.pack(side="left", fill="x", expand=True,
                                padx=(0, 4), pady=8)

        self.browse_btn = ctk.CTkButton(
            self.toolbar, text="📂", width=32, height=BASE['entry_h'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont('Segoe UI', 11),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['text'], border_width=1, border_color=P['border'],
            command=self._browse_folder)
        self.browse_btn.pack(side="left", padx=(0, 8), pady=8)

        self.start_btn = ctk.CTkButton(
            self.toolbar, text="▶  СТАРТ", width=90,
            height=BASE['btn_h_big'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont(*FONT_BASE['button_b']),
            fg_color=P['accent'], hover_color=P['accent_hover'],
            command=self._on_start)
        self.start_btn.pack(side="left", padx=(0, 4), pady=8)

        self.stop_btn = ctk.CTkButton(
            self.toolbar, text="■  СТОП", width=80,
            height=BASE['btn_h_big'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['text'], border_width=1, border_color=P['border'],
            state="disabled", command=self._on_stop)
        self.stop_btn.pack(side="left", padx=(0, 4), pady=8)

        self.excel_btn = ctk.CTkButton(
            self.toolbar, text="📊 Excel", width=80,
            height=BASE['btn_h_big'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['text'], border_width=1, border_color=P['border'],
            command=self._open_excel)
        self.excel_btn.pack(side="left", padx=(0, 4), pady=8)

        self.csv_btn = ctk.CTkButton(
            self.toolbar, text="📋 CSV", width=70,
            height=BASE['btn_h_big'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['text'], border_width=1, border_color=P['border'],
            command=self._export_csv)
        self.csv_btn.pack(side="left", padx=(0, 4), pady=8)

        self.data_btn = ctk.CTkButton(
            self.toolbar, text="💾 Данные", width=85,
            height=BASE['btn_h_big'],
            corner_radius=BASE['radius'],
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['text'], border_width=1, border_color=P['border'],
            command=self._open_data_dir)
        self.data_btn.pack(side="left", padx=(0, 10), pady=8)

        # BODY
        self.body = ctk.CTkFrame(self, fg_color=P['bg'], corner_radius=0)
        self.body.pack(fill="both", expand=True)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(
            self.body, fg_color=P['sidebar'],
            corner_radius=0, width=BASE['sidebar_w'])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.sidebar_dock = ctk.CTkFrame(
            self.sidebar, fg_color=P['dock_bg'], corner_radius=0)
        self.sidebar_dock.pack(side="bottom", fill="x")
        self._build_dock_panel(self.sidebar_dock)

        self.sidebar_top = ctk.CTkScrollableFrame(
            self.sidebar, fg_color=P['sidebar'], corner_radius=0,
            scrollbar_button_color=P['border'],
            scrollbar_button_hover_color=P['accent'])
        self.sidebar_top.pack(side="top", fill="both", expand=True)
        try:
            self.sidebar_top._scrollbar.configure(width=8)
        except Exception:
            pass

        self._build_settings_card(self.sidebar_top)
        self._build_methods_card(self.sidebar_top)
        self._build_stats_card(self.sidebar_top)

        # MAIN
        self.main = ctk.CTkFrame(self.body, fg_color=P['bg'], corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        # SEARCH BAR
        self.search_bar = ctk.CTkFrame(self.main, fg_color=P['toolbar'],
                                       corner_radius=0, height=32)
        self.search_bar.pack(fill="x")
        self.search_bar.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.search_bar, textvariable=self.search_var,
            placeholder_text="🔍  Поиск по номеру или имени файла...",
            height=24, corner_radius=BASE['radius'],
            fg_color=P['input_bg'], border_color=P['border_light'],
            text_color=P['text'], font=ctk.CTkFont(*FONT_BASE['entry']),
            placeholder_text_color=P['text_dim'])
        self.search_entry.pack(side="left", fill="x", expand=True,
                                padx=6, pady=4)
        self.search_var.trace("w", lambda *a: self._schedule_filter())

        self._attach_entry_clipboard(self.search_entry)

        self.clear_search_btn = ctk.CTkButton(
            self.search_bar, text="✕", width=26, height=24,
            corner_radius=BASE['radius'],
            font=ctk.CTkFont('Segoe UI', 10),
            fg_color="transparent", hover_color=P['hover_light'],
            text_color=P['text_dim'], command=self._clear_search)
        self.clear_search_btn.pack(side="left", padx=(0, 6), pady=4)

        # FILTER CHIPS
        self.filter_bar = ctk.CTkFrame(self.main, fg_color=P['toolbar'],
                                       corner_radius=0, height=28)
        self.filter_bar.pack(fill="x")
        self.filter_bar.pack_propagate(False)

        self._filter_chips = {}
        for key, label in [
            ('all',       'Все'),
            ('found',     '✓ Найденные'),
            ('not_found', '✗ Не найдено'),
            ('ozon',      'Ozon'),
            ('yandex',    'Yandex'),
        ]:
            chip = ctk.CTkButton(
                self.filter_bar, text=label, height=BASE['chip_h'],
                width=len(label) * 8 + 20,
                corner_radius=BASE['chip_h'] // 2,
                font=ctk.CTkFont(*FONT_BASE['chip']),
                fg_color=P['chip_on'] if key == 'all' else P['chip_off'],
                hover_color=P['accent_hover'],
                text_color='#ffffff' if key == 'all' else P['text'],
                command=lambda k=key: self._set_filter_mode(k))
            chip.pack(side="left", padx=(6 if key == 'all' else 2, 2), pady=3)
            self._filter_chips[key] = chip
        ctk.CTkFrame(self.filter_bar, fg_color="transparent",
                     width=1).pack(side="left")

        # TABS
        self.tabview = ctk.CTkTabview(
            self.main, fg_color=P['bg'], corner_radius=0,
            segmented_button_fg_color=P['tab_inactive'],
            segmented_button_selected_color=P['tab_active'],
            segmented_button_selected_hover_color=P['tab_active'],
            segmented_button_unselected_color=P['tab_inactive'],
            segmented_button_unselected_hover_color=P['hover_light'],
            text_color=P['text'])
        self.tabview.pack(fill="both", expand=True)
        self.tabview.add("Результаты")
        self.tabview.add("Журнал")
        self.tabview.add("Сводка")

        self._build_results_table(self.tabview.tab("Результаты"))
        self._build_log_view(self.tabview.tab("Журнал"))
        self._build_summary_view(self.tabview.tab("Сводка"))

        # STATUS BAR
        self.status_bar = ctk.CTkFrame(self, fg_color=P['toolbar'],
                                       corner_radius=0,
                                       height=BASE['status_h'])
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.progress = ctk.CTkProgressBar(
            self.status_bar, height=2, corner_radius=0,
            fg_color=P['border'], progress_color=P['accent'])
        self.progress.pack(fill="x", side="top")
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            self.status_bar, text="Готов к запуску",
            font=ctk.CTkFont(*FONT_BASE['status']),
            text_color=P['text'])
        self.progress_label.pack(side="left", padx=10, pady=2)

        self.time_label = ctk.CTkLabel(
            self.status_bar, text="",
            font=ctk.CTkFont(*FONT_BASE['status']),
            text_color=P['text'])
        self.time_label.pack(side="right", padx=10, pady=2)

        self._ui_ready = True

    # ================= БУФЕР ОБМЕНА ENTRY =================

    def _attach_entry_clipboard(self, ctk_entry):
        try:
            inner = ctk_entry._entry
        except AttributeError:
            inner = ctk_entry

        def _paste(_e=None):
            try:
                text = self.clipboard_get()
            except Exception:
                return "break"
            if not text:
                return "break"
            try:
                if inner.selection_present():
                    inner.delete("sel.first", "sel.last")
            except Exception:
                pass
            inner.insert("insert", text)
            return "break"

        def _copy(_e=None):
            try:
                if inner.selection_present():
                    self.clipboard_clear()
                    self.clipboard_append(inner.selection_get())
            except Exception:
                pass
            return "break"

        def _cut(_e=None):
            try:
                if inner.selection_present():
                    self.clipboard_clear()
                    self.clipboard_append(inner.selection_get())
                    inner.delete("sel.first", "sel.last")
            except Exception:
                pass
            return "break"

        def _sel_all(_e=None):
            try:
                inner.select_range(0, "end")
                inner.icursor("end")
            except Exception:
                pass
            return "break"

        for w in (ctk_entry, inner):
            w.bind("<Control-v>", _paste)
            w.bind("<Control-V>", _paste)
            w.bind("<Control-Insert>", _paste)
            w.bind("<Shift-Insert>", _paste)
            w.bind("<Control-c>", _copy)
            w.bind("<Control-C>", _copy)
            w.bind("<Control-x>", _cut)
            w.bind("<Control-X>", _cut)
            w.bind("<Control-a>", _sel_all)
            w.bind("<Control-A>", _sel_all)

        P = self.palette
        ctx = tk.Menu(self, tearoff=0, bg=P['input_bg'], fg=P['text'],
                      activebackground=P['accent'],
                      activeforeground='#ffffff',
                      bd=0, relief="flat", font=("Segoe UI", 9))
        ctx.add_command(label="Вставить", command=_paste)
        ctx.add_command(label="Копировать", command=_copy)
        ctx.add_command(label="Вырезать", command=_cut)
        ctx.add_separator()
        ctx.add_command(label="Выделить всё", command=_sel_all)

        def _ctx_show(e):
            try:
                ctx.tk_popup(e.x_root, e.y_root)
            finally:
                try:
                    ctx.grab_release()
                except Exception:
                    pass
            return "break"

        ctk_entry.bind("<Button-3>", _ctx_show)
        inner.bind("<Button-3>", _ctx_show)

    # ------- НАСТРОЙКИ -------

    def _build_settings_card(self, parent):
        P = self.palette

        header = ctk.CTkFrame(parent, fg_color=P['sidebar'],
                              corner_radius=0, height=26)
        header.pack(fill="x")
        header.pack_propagate(False)

        self.settings_title = ctk.CTkLabel(
            header, text="⚙  НАСТРОЙКИ", anchor="w",
            font=ctk.CTkFont(*FONT_BASE['section']),
            text_color=P['text'])
        self.settings_title.pack(side="left", fill="x", expand=True,
                                  padx=10, pady=4)

        self.auto_btn = ctk.CTkButton(
            header, text="🔄 Авто", width=70, height=22,
            corner_radius=BASE['radius'],
            font=ctk.CTkFont('Segoe UI', 9),
            fg_color=P['accent'], hover_color=P['accent_hover'],
            text_color='#ffffff',
            command=self._on_auto_detect)
        self.auto_btn.pack(side="right", padx=(0, 6), pady=2)

        content = ctk.CTkFrame(parent, fg_color=P['sidebar'], corner_radius=0)
        content.pack(fill="x", padx=8, pady=(0, 6))

        self.entries = {}
        self._setting_rows = []

        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 4))
        row1.grid_columnconfigure(0, weight=1, uniform="col")
        row1.grid_columnconfigure(1, weight=1, uniform="col")
        self._add_setting_grid(row1, 0, 'scan_seconds', 'Секунд', int, 1, 15)
        self._add_setting_grid(row1, 1, 'frames_count', 'Кадров', int, 1, 10)

        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 4))
        row2.grid_columnconfigure(0, weight=1, uniform="col")
        row2.grid_columnconfigure(1, weight=1, uniform="col")
        self._add_setting_grid(row2, 0, 'worker_threads', 'Потоков', int, 1, 32)
        self._add_setting_grid(row2, 1, 'easyocr_concurrency', 'EasyOCR',
                               int, 1, 8)

        self._add_setting_full(content, 'data_dir', 'Папка данных',
                               with_browse=True)

        self.opt_vars = {}
        for key, label, default in [
            ('enable_qr_align', 'Выравнивать по QR', True),
            ('enable_rotation', 'Ротация кадров', True),
            ('enable_stacking', 'Стек кадров', True),
            ('resume',          'Продолжать с места остановки', True),
        ]:
            var = tk.BooleanVar(value=bool(self.cfg.get(key, default)))
            cb = ctk.CTkCheckBox(
                content, text=label, variable=var,
                font=ctk.CTkFont('Segoe UI', 9),
                text_color=P['text_dim'],
                fg_color=P['accent'], hover_color=P['accent_hover'],
                checkmark_color='#ffffff',
                border_color=P['border_light'],
                corner_radius=2, checkbox_width=12, checkbox_height=12)
            cb.pack(anchor="w", pady=1)
            self.opt_vars[key] = var

        self.pc_info_lbl = ctk.CTkLabel(
            content, text="", anchor="w",
            font=ctk.CTkFont('Segoe UI', 8),
            text_color=P['text_dim'], justify="left")
        self.pc_info_lbl.pack(fill="x", pady=(2, 0))
        self._refresh_pc_info()

        ctk.CTkFrame(parent, fg_color=P['border'], height=1,
                     corner_radius=0).pack(fill="x")

    def _refresh_pc_info(self):
        try:
            info = auto_detect_config().get('_info', {})
            self.pc_info_lbl.configure(
                text=f"💻 CPU: {info.get('cpu', '?')} ядер  ·  "
                     f"RAM: {info.get('ram_gb', '?')} ГБ  ·  "
                     f"{info.get('name', '')}")
        except Exception:
            pass

    def _on_auto_detect(self):
        try:
            rec = auto_detect_config()
        except Exception as e:
            messagebox.showerror("Ошибка",
                                  f"Не удалось определить параметры:\n{e}")
            return

        info = rec.get('_info', {})
        for key in ('scan_seconds', 'frames_count',
                    'worker_threads', 'easyocr_concurrency'):
            if key in self.entries and key in rec:
                var, _, _, _ = self.entries[key]
                var.set(str(rec[key]))

        self._refresh_pc_info()
        messagebox.showinfo(
            "Автонастройка",
            f"Определены оптимальные параметры:\n\n"
            f"  • Ядер CPU: {info.get('cpu', '?')}\n"
            f"  • ОЗУ:      {info.get('ram_gb', '?')} ГБ\n"
            f"  • Уровень:  {info.get('name', '?')}\n\n"
            f"  • Сканировать:  {rec['scan_seconds']} сек\n"
            f"  • Кадров:       {rec['frames_count']}\n"
            f"  • Потоков:      {rec['worker_threads']}\n"
            f"  • EasyOCR:      {rec['easyocr_concurrency']}\n\n"
            f"Нажмите СТАРТ, чтобы применить.")

    def _add_setting_grid(self, parent, col, key, label, cast, mn, mx):
        P = self.palette
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, sticky="ew", padx=(0, 4))

        lbl = ctk.CTkLabel(f, text=label, anchor="w",
                           font=ctk.CTkFont(*FONT_BASE['label']),
                           text_color=P['text_dim'])
        lbl.pack(fill="x")

        var = tk.StringVar(value=str(self.cfg.get(key, mn)))
        entry = ctk.CTkEntry(f, textvariable=var, height=BASE['entry_h'],
                             corner_radius=BASE['radius'],
                             fg_color=P['input_bg'],
                             border_color=P['border_light'],
                             text_color=P['text'],
                             font=ctk.CTkFont(*FONT_BASE['entry']))
        entry.pack(fill="x")

        self.entries[key] = (var, cast, mn, mx)
        self._setting_rows.append((lbl, entry))

    def _add_setting_full(self, parent, key, label, with_browse=False):
        P = self.palette
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(0, 4))

        lbl = ctk.CTkLabel(f, text=label, anchor="w",
                           font=ctk.CTkFont(*FONT_BASE['label']),
                           text_color=P['text_dim'])
        lbl.pack(fill="x")

        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.pack(fill="x")

        var = tk.StringVar(value=str(self.cfg.get(key, '') or ''))
        entry = ctk.CTkEntry(inner, textvariable=var,
                             height=BASE['entry_h'],
                             corner_radius=BASE['radius'],
                             fg_color=P['input_bg'],
                             border_color=P['border_light'],
                             text_color=P['text'],
                             font=ctk.CTkFont(*FONT_BASE['entry']))
        entry.pack(side="left", fill="x", expand=True)

        if with_browse:
            btn = ctk.CTkButton(
                inner, text="📂", width=28, height=BASE['entry_h'],
                corner_radius=BASE['radius'],
                font=ctk.CTkFont('Segoe UI', 11),
                fg_color=P['input_bg'], hover_color=P['hover_light'],
                text_color=P['text'], border_width=1,
                border_color=P['border'],
                command=lambda: self._browse_data_dir(var))
            btn.pack(side="left", padx=(4, 0))

        self.entries[key] = (var, str, None, None)
        self._setting_rows.append((lbl, entry))

    def _browse_data_dir(self, var):
        folder = filedialog.askdirectory(
            title="Папка для данных (БД, логи, Excel, videos)")
        if folder:
            var.set(folder)

    # ------- МЕТОДЫ -------

    def _build_methods_card(self, parent):
        P = self.palette

        header = ctk.CTkFrame(parent, fg_color=P['sidebar'],
                              corner_radius=0, height=26)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.methods_title = ctk.CTkLabel(
            header, text="🔍  МЕТОДЫ", anchor="w",
            font=ctk.CTkFont(*FONT_BASE['section']),
            text_color=P['text'])
        self.methods_title.pack(fill="x", padx=10, pady=4)

        content = ctk.CTkFrame(parent, fg_color=P['sidebar'], corner_radius=0)
        content.pack(fill="x", padx=10, pady=(0, 6))

        self.method_vars = {}
        self._method_cbs = []

        for key, name, _, _, _ in ALL_METHODS:
            var = tk.BooleanVar(
                value=self.cfg['enabled_methods'].get(key, True))
            cb = ctk.CTkCheckBox(
                content, text=name, variable=var,
                font=ctk.CTkFont(*FONT_BASE['checkbox']),
                text_color=P['text'],
                fg_color=P['accent'], hover_color=P['accent_hover'],
                checkmark_color='#ffffff',
                border_color=P['border_light'],
                corner_radius=2, checkbox_width=14, checkbox_height=14)
            cb.pack(anchor="w", pady=1)
            self.method_vars[key] = var
            self._method_cbs.append(cb)

        ctk.CTkFrame(parent, fg_color=P['border'], height=1,
                     corner_radius=0).pack(fill="x")

    # ------- СТАТИСТИКА -------

    def _build_stats_card(self, parent):
        P = self.palette

        header = ctk.CTkFrame(parent, fg_color=P['sidebar'],
                              corner_radius=0, height=24)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.stats_title = ctk.CTkLabel(
            header, text="📊  СТАТИСТИКА", anchor="w",
            font=ctk.CTkFont(*FONT_BASE['section']),
            text_color=P['text'])
        self.stats_title.pack(fill="x", padx=10, pady=2)

        content = ctk.CTkFrame(parent, fg_color=P['sidebar'], corner_radius=0)
        content.pack(fill="x", padx=10, pady=(0, 8))

        self.stats_lbl = ctk.CTkLabel(
            content, text="—", anchor="w", justify="left",
            font=ctk.CTkFont('Consolas', 9),
            text_color=P['text_dim'])
        self.stats_lbl.pack(fill="x")

        ctk.CTkFrame(parent, fg_color=P['border'], height=1,
                     corner_radius=0).pack(fill="x")

    def _refresh_stats(self):
        try:
            data_dir = self.cfg.get('data_dir') or _default_data_dir()
            db_path = self.cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)
            if not os.path.isfile(db_path):
                self.stats_lbl.configure(text="—")
                return
            cache = VideoCache(db_path)
            stats = cache.marketplace_stats()
            mps = stats['marketplaces']
            sts = stats['statuses']

            total = sum(mps.values()) or 1
            lines = []
            for mp in ('Ozon', 'Yandex Market', 'Неизвестно', '-'):
                cnt = mps.get(mp, 0)
                if cnt == 0:
                    continue
                pct = cnt / total * 100
                lines.append(f"{mp:<15} {cnt:>5} ({pct:.0f}%)")
            lines.append("")
            for st_name, st_label in [('found', '✓ найдено'),
                                       ('not_found', '✗ не найдено'),
                                       ('error', '⚠ ошибок')]:
                cnt = sts.get(st_name, 0)
                if cnt:
                    lines.append(f"{st_label:<15} {cnt:>5}")
            self.stats_lbl.configure(text="\n".join(lines) or "—")
        except Exception:
            self.stats_lbl.configure(text="—")

    # ------- DOCK -------

    def _build_dock_panel(self, parent):
        P = self.palette

        ctk.CTkFrame(parent, fg_color=P['border'], height=1,
                     corner_radius=0).pack(fill="x")

        header = ctk.CTkFrame(parent, fg_color=P['dock_bg'],
                              corner_radius=0, height=24)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.dock_title = ctk.CTkLabel(
            header, text="💾  БАЗА ПРОВЕРЕННЫХ", anchor="w",
            font=ctk.CTkFont(*FONT_BASE['section']),
            text_color=P['text'])
        self.dock_title.pack(side="left", fill="x", expand=True,
                              padx=10, pady=2)

        content = ctk.CTkFrame(parent, fg_color=P['dock_bg'],
                               corner_radius=0)
        content.pack(fill="x", padx=8, pady=(0, 8))

        self.db_info_lbl = ctk.CTkLabel(
            content, text="—", anchor="w", justify="left",
            font=ctk.CTkFont(*FONT_BASE['label']),
            text_color=P['text_dim'])
        self.db_info_lbl.pack(fill="x", pady=(0, 6))

        self.refresh_db_btn = ctk.CTkButton(
            content, text="🔄  Обновить из БД",
            height=BASE['btn_h'] + 4,
            corner_radius=BASE['radius'] + 1,
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['accent'], hover_color=P['accent_hover'],
            text_color='#ffffff',
            command=lambda: self._refresh_history(silent=False))
        self.refresh_db_btn.pack(fill="x", pady=(0, 4))

        self.retry_btn = ctk.CTkButton(
            content, text="🔁  Перепроверить не найденные",
            height=BASE['btn_h'] + 4,
            corner_radius=BASE['radius'] + 1,
            font=ctk.CTkFont(*FONT_BASE['button']),
            fg_color=P['input_bg'], hover_color=P['hover_light'],
            text_color=P['warn'], border_width=1,
            border_color=P['border'],
            command=self._on_retry_not_found)
        self.retry_btn.pack(fill="x", pady=(0, 6))

        links = ctk.CTkFrame(content, fg_color="transparent")
        links.pack(fill="x")
        links.grid_columnconfigure(0, weight=1)
        links.grid_columnconfigure(1, weight=1)

        self.clear_table_btn = ctk.CTkButton(
            links, text="📄 Очистить таблицу",
            height=BASE['btn_h'] - 2, corner_radius=3,
            font=ctk.CTkFont('Segoe UI', 8),
            fg_color="transparent",
            hover_color=P['hover_light'],
            text_color=P['text_dim'],
            command=self._clear_table)
        self.clear_table_btn.grid(row=0, column=0, sticky="ew",
                                   padx=(0, 2))

        self.clear_db_btn = ctk.CTkButton(
            links, text="🗑 Удалить БД",
            height=BASE['btn_h'] - 2, corner_radius=3,
            font=ctk.CTkFont('Segoe UI', 8),
            fg_color="transparent",
            hover_color=P['hover_light'],
            text_color=P['error'],
            command=self._clear_db)
        self.clear_db_btn.grid(row=0, column=1, sticky="ew",
                                padx=(2, 0))

        self._refresh_db_info()

    def _refresh_db_info(self):
        try:
            data_dir = self.cfg.get('data_dir') or _default_data_dir()
            db_path = self.cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)
            if not os.path.isfile(db_path):
                self.db_info_lbl.configure(text="База пуста")
                return
            st = VideoCache(db_path).stats()
            self.db_info_lbl.configure(
                text=f"{st['total']} видео  ·  {st['found']} найдено")
        except Exception as e:
            self.db_info_lbl.configure(text=f"Ошибка: {e}")

    def _clear_db(self):
        if not messagebox.askyesno("Удалить базу?",
                                    "Все проверенные видео будут забыты.\n"
                                    "Лицензия не пострадает."):
            return
        try:
            data_dir = self.cfg.get('data_dir') or _default_data_dir()
            db_path = self.cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)
            VideoCache(db_path).clear()
            self._refresh_db_info()
            self._refresh_stats()
            messagebox.showinfo("Готово", "База очищена.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ------- ТАБЛИЦА -------

    def _build_results_table(self, parent):
        P = self.palette
        self.tree_style = ttk.Style()
        try:
            self.tree_style.theme_use("clam")
        except Exception:
            pass
        self._style_tree(1.0)

        wrap = ctk.CTkFrame(parent, fg_color=P['bg'], corner_radius=0)
        wrap.pack(fill="both", expand=True)

        cols = ("file", "number", "marketplace", "qr", "time",
                "source", "date")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings",
                                 style="Treeview")

        for col in cols:
            self.tree.heading(
                col, text=self._heading_labels[col],
                command=lambda c=col: self._on_header_click(c))

        self.tree.column("file",        width=220, anchor="w")
        self.tree.column("number",      width=200, anchor="w")
        self.tree.column("marketplace", width=110, anchor="center")
        self.tree.column("qr",          width=140, anchor="w")
        self.tree.column("time",        width=65,  anchor="center")
        self.tree.column("source",      width=90,  anchor="center")
        self.tree.column("date",        width=140, anchor="center")

        vsb = ttk.Scrollbar(wrap, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("found",     foreground=P['success'])
        self.tree.tag_configure("not_found", foreground=P['warn'])
        self.tree.tag_configure("error",     foreground=P['error'])

        self.tree.bind("<Double-1>", self._on_row_double_click)
        self.tree.bind("<Button-3>", self._on_row_right_click)

        self._update_heading_arrows()

    def _style_tree(self, scale=1.0):
        P = self.palette
        fam, size, weight = FONT_BASE['table']
        fam_h, size_h, weight_h = FONT_BASE['table_h']
        size = max(8, int(round(size * scale)))
        size_h = max(8, int(round(size_h * scale)))
        row_h = max(20, int(round(24 * scale)))

        s = self.tree_style
        s.configure("Treeview",
                    background=P['bg'], foreground=P['text'],
                    fieldbackground=P['bg'], borderwidth=0,
                    font=(fam, size, weight), rowheight=row_h)
        s.configure("Treeview.Heading",
                    background=P['toolbar'], foreground=P['text_dim'],
                    borderwidth=0, font=(fam_h, size_h, weight_h))
        s.map("Treeview",
              background=[("selected", P['accent'])],
              foreground=[("selected", '#ffffff')])

    def _build_log_view(self, parent):
        P = self.palette
        wrap = ctk.CTkFrame(parent, fg_color=P['bg'], corner_radius=0)
        wrap.pack(fill="both", expand=True)
        self.log_box = ctk.CTkTextbox(
            wrap, fg_color=P['bg'], text_color=P['text'],
            font=ctk.CTkFont(*FONT_BASE['log']),
            corner_radius=0, wrap="word", activate_scrollbars=True)
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _build_summary_view(self, parent):
        P = self.palette
        wrap = ctk.CTkFrame(parent, fg_color=P['bg'], corner_radius=0)
        wrap.pack(fill="both", expand=True)
        self.summary_box = ctk.CTkTextbox(
            wrap, fg_color=P['bg'], text_color=P['text'],
            font=ctk.CTkFont(*FONT_BASE['log']),
            corner_radius=0, wrap="word")
        self.summary_box.pack(fill="both", expand=True)
        self.summary_box.configure(state="disabled")

    # ================= ФИЛЬТРЫ =================

    def _set_filter_mode(self, mode):
        self.filter_mode = mode
        P = self.palette
        for key, chip in self._filter_chips.items():
            try:
                if key == mode:
                    chip.configure(fg_color=P['chip_on'], text_color='#ffffff')
                else:
                    chip.configure(fg_color=P['chip_off'], text_color=P['text'])
            except Exception:
                pass
        self._apply_filter()

    def _matches_filter(self, r):
        m = self.filter_mode
        if m == 'all':
            return True
        if m == 'found':
            return r.get('Статус') == 'found'
        if m == 'not_found':
            return r.get('Статус') == 'not_found'
        if m == 'ozon':
            return (r.get('Маркетплейс') or '').lower() == 'ozon'
        if m == 'yandex':
            return 'yandex' in (r.get('Маркетплейс') or '').lower()
        return True

    # ================= СОРТИРОВКА =================

    def _on_header_click(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        self._update_heading_arrows()
        self._apply_filter()

    def _update_heading_arrows(self):
        for col, base in self._heading_labels.items():
            arrow = ''
            if self.sort_column == col:
                arrow = '  ▼' if self.sort_reverse else '  ▲'
            try:
                self.tree.heading(col, text=base + arrow)
            except Exception:
                pass

    # ================= КЛИКИ ПО ТАБЛИЦЕ =================

    def _on_row_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, 'values')
        if values:
            self._open_file_folder(values[0])

    def _on_row_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        values = self.tree.item(item, 'values')
        if not values:
            return
        fname = values[0]
        number = values[1] if len(values) > 1 else ''
        P = self.palette

        menu = tk.Menu(self, tearoff=0, bg=P['input_bg'], fg=P['text'],
                       activebackground=P['accent'],
                       activeforeground='#ffffff', bd=0, relief="flat",
                       font=("Segoe UI", 9))
        menu.add_command(label="📂 Открыть папку с файлом",
                         command=lambda: self._open_file_folder(fname))
        menu.add_command(label="🔁 Перепроверить этот файл",
                         command=lambda: self._retry_one(fname))
        menu.add_separator()
        menu.add_command(label="📊 Открыть Excel",
                         command=self._open_excel)
        menu.add_command(label="📁 Открыть папку данных",
                         command=self._open_data_dir)
        menu.add_separator()
        menu.add_command(label="📋 Копировать номер",
                         command=lambda: self._copy_to_clip(number))
        menu.add_command(label="📋 Копировать имя файла",
                         command=lambda: self._copy_to_clip(fname))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _find_source_for(self, fname):
        """
        Ищет файл по всем возможным путям.
        Возвращает (full_path или None, existing_folder или None).
        Если файл не найден — возвращает (None, None).
        """
        if not fname:
            return None, None
        key = (fname or '').lower().strip()

        # 1. source_folder из saved_results
        source = None
        for r in self.saved_results:
            if (r.get('Название файла', '').lower().strip() == key):
                sf = (r.get('source_folder') or '').strip()
                if sf and os.path.isdir(sf):
                    source = sf
                break

        # 2. Собираем кандидатов (только СУЩЕСТВУЮЩИЕ папки)
        candidates = []
        if source:
            candidates.append(source)

        # Из поля UI
        vf = (self.folder_var.get() or '').strip()
        if vf:
            if not os.path.isabs(vf):
                dd = self.cfg.get('data_dir') or _default_data_dir()
                vf = os.path.join(dd, vf)
            if os.path.isdir(vf) and vf not in candidates:
                candidates.append(vf)

        # Из cfg
        vf2 = (self.cfg.get('video_folder', '') or '').strip()
        if vf2:
            if not os.path.isabs(vf2):
                dd = self.cfg.get('data_dir') or _default_data_dir()
                vf2 = os.path.join(dd, vf2)
            if os.path.isdir(vf2) and vf2 not in candidates:
                candidates.append(vf2)

        dd = self.cfg.get('data_dir') or _default_data_dir()
        fb = os.path.join(dd, 'videos')
        if os.path.isdir(fb) and fb not in candidates:
            candidates.append(fb)

        # 3. Прямой поиск
        for folder in candidates:
            p = os.path.join(folder, fname)
            if os.path.isfile(p):
                return p, folder

        # 4. Рекурсивный поиск (2 уровня вглубь)
        for folder in candidates:
            try:
                for root, dirs, files in os.walk(folder):
                    depth = root[len(folder):].count(os.sep)
                    if depth > 2:
                        dirs[:] = []
                        continue
                    if fname in files:
                        return os.path.join(root, fname), root
            except Exception:
                continue

        return None, None

    def _open_file_folder(self, fname):
        """
        Открывает Проводник с выделенным файлом.
        Если файл не найден — показывает сообщение.
        Никогда не открывает "первую попавшуюся" папку.
        """
        if not fname:
            return

        full_path, folder = self._find_source_for(fname)

        if full_path and os.path.isfile(full_path):
            self._append_log(f"Открыт: {full_path}")
            try:
                # ВАЖНО: кавычки вокруг пути для explorer
                # (иначе пути с пробелами парсятся неверно)
                subprocess.Popen(f'explorer /select,"{full_path}"',
                                  shell=False)
                return
            except Exception as e:
                self._append_log(f"Ошибка explorer: {e}")
                # Fallback — открыть папку через startfile
                try:
                    os.startfile(os.path.dirname(full_path))
                    return
                except Exception as e2:
                    messagebox.showerror(
                        "Ошибка",
                        f"Не удалось открыть файл:\n{full_path}\n\n{e2}")
                    return

        # Файл не найден — показываем сообщение, ничего не открываем
        vf = (self.folder_var.get() or '').strip() or '(не указана)'
        dd = self.cfg.get('data_dir') or _default_data_dir()
        messagebox.showinfo(
            "Файл не найден",
            f"Файл отсутствует на диске:\n{fname}\n\n"
            f"Проверенные папки:\n"
            f"  • {vf}\n"
            f"  • {dd}\\videos\n\n"
            f"Возможно, видео было перемещено или удалено.\n"
            f"Укажите правильную папку в поле «Папка» вверху окна.")

    def _copy_to_clip(self, text):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass

    # ================= ИСТОРИЯ ИЗ БД =================

    def _load_history_from_db(self):
        try:
            data_dir = self.cfg.get('data_dir') or _default_data_dir()
            db_path = self.cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)

            if not os.path.isfile(db_path):
                return

            cache = VideoCache(db_path)
            records = cache.all_records(limit=5000)

            if not records:
                return

            for rec in records:
                checked_at = rec.get('checked_at', '') or ''
                date_str = '-'
                if checked_at:
                    try:
                        dt = datetime.fromisoformat(checked_at)
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        date_str = checked_at

                result = {
                    'Название файла': rec.get('filename', ''),
                    'Внутренний номер': rec.get('number') or 'Не найдено',
                    'Маркетплейс': rec.get('marketplace') or '-',
                    'QR-код': rec.get('qr') or '-',
                    'Время (с)': rec.get('elapsed') or 0.0,
                    'Статус': rec.get('status') or 'not_found',
                    'Источник': 'БД',
                    'Дата и время создания': date_str,
                    'checked_at': checked_at,
                    'source_folder': rec.get('source_folder') or '',
                }
                self.saved_results.append(result)

            self._apply_filter()

            try:
                self.progress_label.configure(
                    text=f"Загружено из БД: {len(records)} записей")
            except Exception:
                pass

        except Exception as e:
            print("Ошибка загрузки истории:", e)
            try:
                self.progress_label.configure(text=f"Ошибка базы: {e}")
                self._append_log(f"Ошибка загрузки базы: {e}")
            except Exception:
                pass

    def _refresh_history(self, silent=False):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_map.clear()
        self.saved_results = []
        self._load_history_from_db()
        self._refresh_stats()

        if not silent:
            try:
                self.progress_label.configure(
                    text=f"Обновлено: {len(self.saved_results)} записей")
            except Exception:
                pass

    def _clear_table(self):
        if not messagebox.askyesno(
                "Очистить таблицу?",
                "Из вида будут убраны все строки.\n"
                "База данных НЕ будет очищена — записи можно "
                "вернуть кнопкой «Обновить из БД»."):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_map.clear()
        self.saved_results = []
        self.progress_label.configure(text="Таблица очищена (БД сохранена)")

    # ================= АВТОПОИСК ПАПКИ =================

    def _autofind_folder(self):
        try:
            vf = self.folder_var.get().strip()
            if vf:
                if not os.path.isabs(vf):
                    dd = self.cfg.get('data_dir') or _default_data_dir()
                    vf_abs = os.path.join(dd, vf)
                else:
                    vf_abs = vf
                if os.path.isdir(vf_abs):
                    self.folder_var.set(vf_abs)
                    return

            candidates = [
                os.path.join(_default_data_dir(), 'videos'),
                os.path.join(_app_dir(), 'videos'),
            ]
            for c in candidates:
                if os.path.isdir(c):
                    self.folder_var.set(c)
                    return

            self._append_log("Папка с видео не найдена. "
                              "Перетащите папку в окно или нажмите 📂")
            self.progress_label.configure(
                text="Перетащите папку в окно или нажмите 📂")
        except Exception:
            pass

    # ================= ПЕРЕПРОВЕРКА =================

    def _check_license_or_activate(self):
        lic = check_license()
        if lic['status'] == 'ok':
            return True
        reason = lic.get('reason', '')
        if lic['status'] == 'expired':
            reason = (f"Срок лицензии истёк "
                      f"({lic['days_overdue']} дн. назад).")
        ok, days_left = run_activation_window(reason)
        if not ok:
            return False
        self.days_left = days_left
        try:
            self.license_lbl.configure(
                text=f"🔑 {self.days_left} дн.",
                text_color=self.palette['success']
                if self.days_left > 7 else self.palette['warn'])
        except Exception:
            pass
        return True

    def _start_engine(self, cfg, files_to_scan, mode_label="Запуск",
                       skip_resume=False):
        P = self.palette
        self.status_badge.configure(text="● РАБОТА", text_color=P['warn'])
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        mode = cfg.get('performance_mode_effective', 'full')
        self.progress_label.configure(text=f"{mode_label} ({mode})...")
        self.time_label.configure(text="")
        self.tabview.set("Результаты")

        self.engine = ScannerEngine(
            cfg, files=files_to_scan, skip_resume=skip_resume,
            on_log=lambda m: self.msg_queue.put(('log', m)),
            on_file_done=lambda r: self.msg_queue.put(('row', r)),
            on_progress=lambda d, t, e: self.msg_queue.put(
                ('progress', d, t, e)),
            on_finished=lambda s: self.msg_queue.put(('finished', s)))
        self.engine.start()

    def _on_retry_not_found(self):
        if self.engine and self.engine.is_running():
            messagebox.showinfo("Занято", "Уже идёт сканирование.")
            return

        if not self._check_license_or_activate():
            return

        cfg = self._collect_config()
        cfg = apply_performance_mode(cfg)
        self.cfg = cfg
        save_settings(cfg)

        data_dir = cfg.get('data_dir') or _default_data_dir()
        _ensure_dir(data_dir)

        video_dir = cfg.get('video_folder', 'videos')
        if not os.path.isabs(video_dir):
            video_dir = os.path.join(data_dir, video_dir)
        cfg['video_folder'] = video_dir

        if not os.path.isdir(video_dir):
            messagebox.showerror("Ошибка",
                                  f"Папка с видео не найдена:\n{video_dir}")
            return

        db_path = cfg.get('db_path', 'checked_videos.db')
        if not os.path.isabs(db_path):
            db_path = os.path.join(data_dir, db_path)
        cache = VideoCache(db_path)

        not_found_records = cache.get_not_found()
        if not not_found_records:
            messagebox.showinfo("Перепроверка",
                                 "В базе нет записей со статусом «Не найдено».")
            return

        files_to_scan = []
        missing_files = []
        for rec in not_found_records:
            fname = rec.get('filename', '')
            if not fname:
                continue
            full = os.path.join(video_dir, fname)
            if os.path.isfile(full):
                if fname not in files_to_scan:
                    files_to_scan.append(fname)
            else:
                missing_files.append(fname)

        if not files_to_scan:
            messagebox.showinfo(
                "Перепроверка",
                f"В базе {len(not_found_records)} неудачных записей.\n"
                f"Но ни одного файла нет в папке:\n{video_dir}")
            return

        answer = messagebox.askyesno(
            "Перепроверить не найденные",
            f"В базе {len(not_found_records)} неудачных записей.\n"
            f"Файлов найдено на диске: {len(files_to_scan)}\n"
            f"Отсутствует файлов: {len(missing_files)}\n\n"
            f"Запустить перепроверку?")
        if not answer:
            return

        self._clear_log()
        self._clear_summary()
        self.saved_log_lines = []

        self._start_engine(cfg, files_to_scan,
                            mode_label="Перепроверка",
                            skip_resume=True)

    def _retry_one(self, fname):
        if self.engine and self.engine.is_running():
            messagebox.showinfo("Занято", "Уже идёт сканирование.")
            return
        if not fname:
            return
        if not self._check_license_or_activate():
            return

        cfg = self._collect_config()
        cfg = apply_performance_mode(cfg)
        self.cfg = cfg
        save_settings(cfg)

        data_dir = cfg.get('data_dir') or _default_data_dir()
        _ensure_dir(data_dir)
        video_dir = cfg.get('video_folder', 'videos')
        if not os.path.isabs(video_dir):
            video_dir = os.path.join(data_dir, video_dir)
        cfg['video_folder'] = video_dir

        full = os.path.join(video_dir, fname)
        if not os.path.isfile(full):
            messagebox.showerror("Файл не найден",
                                  f"Файл отсутствует:\n{full}")
            return

        self._clear_log()
        self._clear_summary()
        self.saved_log_lines = []

        self._start_engine(cfg, [fname],
                            mode_label="Перепроверка",
                            skip_resume=True)

    # ================= ЭКСПОРТ CSV =================

    def _export_csv(self):
        try:
            data_dir = self.cfg.get('data_dir') or _default_data_dir()
            db_path = self.cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)
            if not os.path.isfile(db_path):
                messagebox.showinfo("Экспорт", "База ещё не создана.")
                return

            csv_path = os.path.join(data_dir, 'export.csv')
            cache = VideoCache(db_path)
            n = cache.export_csv(csv_path)
            if n <= 0:
                messagebox.showinfo("Экспорт", "Нет данных для экспорта.")
                return

            messagebox.showinfo(
                "Экспорт завершён",
                f"Сохранено {n} записей:\n{csv_path}")
            try:
                os.startfile(os.path.dirname(csv_path))
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    # ================= ПОИСК (debounce) =================

    def _schedule_filter(self):
        if self._search_job:
            try:
                self.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.after(SEARCH_DEBOUNCE_MS, self._apply_filter)

    def _apply_filter(self):
        self._search_job = None
        q = self.search_var.get().lower().strip()
        self.current_filter = q

        if self.sort_column:
            field = self.COL_MAP.get(self.sort_column)
            if field:
                def sort_key(r):
                    v = r.get(field, '')
                    if self.sort_column == 'time':
                        try:
                            return float(v)
                        except Exception:
                            return 0.0
                    return str(v if v is not None else '').lower()
                try:
                    self.saved_results.sort(
                        key=sort_key, reverse=self.sort_reverse)
                except Exception:
                    pass

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_map.clear()
        for r in self.saved_results:
            fname = (r.get('Название файла') or '').lower()
            number = (r.get('Внутренний номер') or '').lower()
            qr = (r.get('QR-код') or '').lower()
            text_ok = (not q or q in fname or q in number or q in qr)
            if text_ok and self._matches_filter(r):
                self._append_row_internal(r)

    def _clear_search(self):
        self.search_var.set("")

    # ================= МАСШТАБ =================

    def _initial_scale(self):
        if not self._ui_ready:
            self.after(200, self._initial_scale)
            return
        try:
            self.update_idletasks()
        except Exception:
            pass
        self.scale = 0.0
        self._apply_scale(force=True)

    def _on_configure(self, event):
        if event.widget is not self or not self._ui_ready:
            return
        w, h = event.width, event.height
        if abs(w - self._last_size[0]) < 3 and \
                abs(h - self._last_size[1]) < 3:
            return
        self._last_size = (w, h)
        if self._resize_job:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(
            120, lambda: self._apply_scale(False))

    def _compute_scale(self):
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        return max(SCALE_MIN, min(SCALE_MAX,
                                   min(w / REF_WIDTH,
                                       (h / REF_HEIGHT) * 1.05)))

    def _apply_scale(self, force=False):
        if not self._ui_ready:
            return
        s = self._compute_scale()
        if not force and abs(s - self.scale) < 0.03:
            return
        self.scale = s

        def fnt(key):
            fam, size, weight = FONT_BASE[key]
            return ctk.CTkFont(fam, max(8, int(round(size * s))), weight)

        try:
            self.titlebar.configure(height=max(46, int(BASE['titlebar_h'] * s)))
            self.logo_lbl.configure(font=fnt('title'))
            self.version_lbl.configure(
                font=ctk.CTkFont('Segoe UI', max(8, int(8 * s))))
            self.status_badge.configure(
                font=ctk.CTkFont('Segoe UI', max(8, int(9 * s)), 'bold'))
            self.license_lbl.configure(
                font=ctk.CTkFont('Segoe UI', max(8, int(9 * s))))

            self.toolbar.configure(height=int(BASE['toolbar_h'] * s))
            self.folder_lbl.configure(font=fnt('label'))
            self.folder_entry.configure(font=fnt('entry'),
                                         height=int(BASE['entry_h'] * s))
            self.browse_btn.configure(height=int(BASE['entry_h'] * s))
            self.start_btn.configure(height=int(BASE['btn_h_big'] * s),
                                      font=fnt('button_b'))
            self.stop_btn.configure(height=int(BASE['btn_h_big'] * s),
                                     font=fnt('button'))
            self.excel_btn.configure(height=int(BASE['btn_h_big'] * s),
                                      font=fnt('button'))
            self.csv_btn.configure(height=int(BASE['btn_h_big'] * s),
                                    font=fnt('button'))
            self.data_btn.configure(height=int(BASE['btn_h_big'] * s),
                                     font=fnt('button'))

            self.sidebar.configure(width=int(BASE['sidebar_w'] * s))
            self.settings_title.configure(font=fnt('section'))
            self.methods_title.configure(font=fnt('section'))
            try:
                self.auto_btn.configure(
                    font=ctk.CTkFont('Segoe UI', max(8, int(9 * s))))
                self.dock_title.configure(font=fnt('section'))
                self.stats_title.configure(font=fnt('section'))
            except Exception:
                pass

            for lbl, entry in self._setting_rows:
                lbl.configure(font=fnt('label'))
                entry.configure(font=fnt('entry'),
                                 height=int(BASE['entry_h'] * s))

            cb_size = max(12, int(14 * s))
            for cb in self._method_cbs:
                cb.configure(font=fnt('checkbox'),
                             checkbox_width=cb_size,
                             checkbox_height=cb_size)

            for chip in self._filter_chips.values():
                chip.configure(font=fnt('chip'),
                               height=int(BASE['chip_h'] * s))

            self.db_info_lbl.configure(font=fnt('label'))
            self.refresh_db_btn.configure(
                font=fnt('button'),
                height=int((BASE['btn_h'] + 4) * s))
            self.retry_btn.configure(
                font=fnt('button'),
                height=int((BASE['btn_h'] + 4) * s))
            self.clear_table_btn.configure(
                height=int((BASE['btn_h'] - 2) * s))
            self.clear_db_btn.configure(
                height=int((BASE['btn_h'] - 2) * s))

            try:
                self.pc_info_lbl.configure(
                    font=ctk.CTkFont('Segoe UI', max(8, int(8 * s))))
                self.stats_lbl.configure(
                    font=ctk.CTkFont('Consolas', max(8, int(9 * s))))
            except Exception:
                pass

            self._style_tree(s)
            self.search_entry.configure(font=fnt('entry'),
                                         height=int(24 * s))
            self.log_box.configure(font=fnt('log'))
            self.summary_box.configure(font=fnt('log'))

            self.progress_label.configure(font=fnt('status'))
            self.time_label.configure(font=fnt('status'))
        except Exception as e:
            print("Ошибка масштабирования:", e)

    # ================= ТЕМА =================

    def _toggle_theme(self):
        if self.engine and self.engine.is_running():
            messagebox.showwarning("Смена темы",
                                    "Нельзя менять тему при обработке.")
            return

        self.cfg = self._collect_config()
        self.theme_name = 'light' if self.theme_name == 'dark' else 'dark'
        self.cfg['theme'] = self.theme_name
        self.palette = THEMES[self.theme_name]
        save_settings(self.cfg)

        ctk.set_appearance_mode(self.theme_name)
        saved = list(self.saved_results)
        saved_log = list(self.saved_log_lines)
        saved_filter = self.filter_mode

        for w in self.winfo_children():
            w.destroy()
        self.configure(fg_color=self.palette['bg'])
        self._build_ui()
        self._setup_drag_and_drop()

        self.scale = 0.0
        self.after(120, lambda: self._apply_scale(force=True))

        self.saved_results = saved
        self.row_map.clear()
        self.filter_mode = saved_filter
        self._update_heading_arrows()
        self._set_filter_mode(saved_filter)
        for line in saved_log:
            self._append_log_raw(line)

    # ================= ДЕЙСТВИЯ =================

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с видео")
        if folder:
            self.folder_var.set(folder)

    def _open_excel(self):
        data_dir = self.cfg.get('data_dir') or _default_data_dir()
        p = self.cfg.get('output_excel', 'ozon_numbers.xlsx')
        if not os.path.isabs(p):
            p = os.path.join(data_dir, p)
        if not os.path.isfile(p):
            messagebox.showinfo("Файл не найден",
                                 f"Результаты ещё не сохранены:\n{p}")
            return
        try:
            os.startfile(p)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _open_data_dir(self):
        path = self.cfg.get('data_dir') or _default_data_dir()
        _ensure_dir(path)
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _collect_config(self):
        cfg = dict(self.cfg)
        cfg['video_folder'] = self.folder_var.get().strip()

        for key, (var, cast, mn, mx) in self.entries.items():
            if key == 'data_dir':
                cfg['data_dir'] = var.get().strip() or _default_data_dir()
                continue
            try:
                val = cast(var.get())
                if mn is not None:
                    val = max(mn, val)
                if mx is not None:
                    val = min(mx, val)
            except Exception:
                val = self.cfg.get(key, mn)
            cfg[key] = val
            var.set(str(val))

        cfg['enabled_methods'] = {k: bool(v.get())
                                  for k, v in self.method_vars.items()}
        cfg['theme'] = self.theme_name
        cfg['sort_column'] = self.sort_column
        cfg['sort_reverse'] = self.sort_reverse

        for key, var in self.opt_vars.items():
            cfg[key] = bool(var.get())

        return cfg

    def _on_start(self):
        skip_resume_on_start = False

        if self.engine and self.engine.is_running():
            return

        if not self._check_license_or_activate():
            return

        cfg = self._collect_config()
        cfg = apply_performance_mode(cfg)
        self.cfg = cfg
        save_settings(cfg)

        data_dir = cfg.get('data_dir') or _default_data_dir()
        _ensure_dir(data_dir)
        video_dir = cfg.get('video_folder', 'videos')
        if not os.path.isabs(video_dir):
            video_dir = os.path.join(data_dir, video_dir)
        cfg['video_folder'] = video_dir

        if not os.path.isdir(video_dir):
            try:
                os.makedirs(video_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось создать папку:\n{video_dir}\n{e}")
                return

        ok, free_gb = check_free_space(video_dir, required_gb=1.0)
        if not ok:
            answer = messagebox.askyesno(
                "Мало места на диске",
                f"Свободно {free_gb:.1f} ГБ — может не хватить.\n\n"
                f"Продолжить?")
            if not answer:
                return

        tess_builtin = _resource_path(os.path.join("tesseract",
                                                    "tesseract.exe"))
        if not os.path.isfile(tess_builtin):
            tess_builtin = os.path.join(_app_dir(), "tesseract",
                                         "tesseract.exe")
        if not os.path.isfile(tess_builtin):
            sys_tess = cfg.get('tesseract_cmd') or \
                r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if not os.path.isfile(sys_tess):
                if not messagebox.askyesno(
                        "Tesseract не найден",
                        "Не найден ни встроенный, ни системный.\n"
                        "Продолжить?"):
                    return

        if not any(cfg['enabled_methods'].values()):
            messagebox.showerror("Ошибка",
                                  "Включите хотя бы один метод.")
            return

        files = list_videos(video_dir)
        if not files:
            messagebox.showerror("Ошибка", "В папке нет видеофайлов.")
            return

        final_files = list(files)
        try:
            db_path = cfg.get('db_path', 'checked_videos.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(data_dir, db_path)
            cache = VideoCache(db_path)
            existing = cache.find_existing(video_dir, files)
            if existing:
                n = len(existing)
                preview = "\n".join(
                    f"  • {name}" for name, _ in existing[:10])
                more = f"\n  ... и ещё {n - 10}" if n > 10 else ""
                msg = (f"Найдено {n} уже проверенных видео:\n\n"
                       f"{preview}{more}\n\nСканировать повторно?")
                answer = messagebox.askyesno("Проверенные видео", msg)
                if not answer:
                    keys = {(nm.lower().strip(), int(sz))
                            for nm, sz in existing}
                    new_files = []
                    for f in files:
                        try:
                            sz = int(os.path.getsize(
                                os.path.join(video_dir, f)))
                        except Exception:
                            sz = 0
                        if (f.lower().strip(), sz) not in keys:
                            new_files.append(f)
                    final_files = new_files
                else:
                    skip_resume_on_start = True
                    if not final_files:
                        self._clear_log()
                        self._clear_summary()
                        self.saved_log_lines = []
                        self._append_log(
                            f"Все {n} видео уже проверены.")
                        self._append_log("Новых файлов нет.")
                        self.progress_label.configure(
                            text="Нет новых видео")
                        self.tabview.set("Журнал")
                        messagebox.showinfo(
                            "Готово", "Все видео уже проверены.")
                        return
        except Exception as e:
            messagebox.showwarning("Предупреждение",
                                    f"Ошибка БД:\n{e}\n\nБез кэша.")

        self._clear_log()
        self._clear_summary()
        self.saved_log_lines = []

        self._start_engine(cfg, final_files, mode_label="Запуск",
                            skip_resume=skip_resume_on_start)

    def _on_stop(self):
        if self.engine and self.engine.is_running():
            self.engine.stop()
            self.progress_label.configure(text="Останавливаю...")
            self.stop_btn.configure(state="disabled")

    # ================= ОЧЕРЕДЬ =================

    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]
                if kind == 'log':
                    self._append_log(msg[1])
                elif kind == 'row':
                    self._append_row(msg[1])
                elif kind == 'progress':
                    self._update_progress(msg[1], msg[2], msg[3])
                elif kind == 'finished':
                    self._on_engine_finished(msg[1])
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _append_log_raw(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _append_log(self, text):
        ts = datetime.now().strftime('%H:%M:%S')
        line = f"{ts}  {text}"
        self.saved_log_lines.append(line)
        if len(self.saved_log_lines) > 3000:
            self.saved_log_lines = self.saved_log_lines[-3000:]
        self._append_log_raw(line)

    def _append_row(self, result):
        fname = result['Название файла']
        key = fname.lower().strip()

        replaced = False
        for i, r in enumerate(self.saved_results):
            if (r.get('Название файла', '').lower().strip() == key):
                self.saved_results[i] = result
                replaced = True
                break
        if not replaced:
            self.saved_results.append(result)

        q = self.current_filter
        fname_l = fname.lower()
        number_l = (result.get('Внутренний номер') or '').lower()
        qr_l = (result.get('QR-код') or '').lower()
        text_ok = (not q or q in fname_l or q in number_l or q in qr_l)
        if text_ok and self._matches_filter(result):
            self._append_row_internal(result)

    def _append_row_internal(self, result):
        fname = result['Название файла']
        status = result.get('Статус', 'not_found')
        key = fname.lower().strip()

        values = (
            fname,
            result.get('Внутренний номер', 'Не найдено'),
            result.get('Маркетплейс', '-'),
            result.get('QR-код', '-'),
            f"{result.get('Время (с)', 0):.2f}",
            result.get('Источник', '-'),
            result.get('Дата и время создания', '-'),
        )

        existing = self.row_map.get(key)
        if existing and self.tree.exists(existing):
            self.tree.item(existing, values=values, tags=(status,))
            item = existing
        else:
            item = self.tree.insert("", "end", values=values,
                                     tags=(status,))
            self.row_map[key] = item

        self.tree.see(item)

    def _update_progress(self, done, total, elapsed):
        pct = done / max(1, total)
        self.progress.set(pct)
        avg = elapsed / max(1, done)
        remaining = avg * (total - done)
        self.progress_label.configure(
            text=f"{done}/{total}  ·  {pct*100:.0f}%  ·  "
                 f"{self.current_scanning_file}")
        self.time_label.configure(
            text=f"{self._fmt_time(elapsed)}  ·  "
                 f"~{self._fmt_time(remaining)}")

    def _on_engine_finished(self, summary):
        P = self.palette
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress.set(1.0)
        self.current_scanning_file = ""

        if summary.get('error'):
            self.status_badge.configure(text="● ОШИБКА",
                                         text_color=P['error'])
            self.progress_label.configure(
                text=f"Ошибка: {summary['error']}")
            return

        results = summary['results']
        cancelled = summary.get('cancelled', False)
        elapsed = summary['elapsed']

        if not results:
            self.status_badge.configure(text="● ГОТОВ",
                                         text_color=P['success'])
            self.progress_label.configure(
                text="Нет файлов для обработки")
            self._refresh_db_info()
            self._refresh_stats()
            return

        found = sum(1 for r in results if r.get('Статус') == 'found')
        not_found = sum(1 for r in results
                        if r.get('Статус') == 'not_found')
        errors = sum(1 for r in results if r.get('Статус') == 'error')
        rate = (found / len(results) * 100) if results else 0

        self.status_badge.configure(
            text=f"● {'ОСТАНОВЛЕНО' if cancelled else 'ГОТОВО'}",
            text_color=P['warn'] if cancelled else P['success'])
        self.progress_label.configure(
            text=f"Найдено: {found}  ·  Не найдено: {not_found}  ·  "
                 f"Ошибок: {errors}")
        self.time_label.configure(
            text=f"Всего: {self._fmt_time(elapsed)}")

        self._render_summary(results, found, not_found, errors,
                              rate, elapsed, cancelled)
        self._refresh_db_info()
        self._refresh_stats()
        self.tabview.set("Результаты")

        self.after(80, lambda: self._refresh_history(silent=True))

    def _render_summary(self, results, found, not_found, errors,
                        rate, elapsed, cancelled):
        lines = []
        lines.append("═" * 60)
        lines.append(f"  ИТОГИ ОБРАБОТКИ "
                     f"{'(ПРЕРВАНО)' if cancelled else ''}")
        lines.append("═" * 60)
        lines.append("")
        lines.append(f"  Всего файлов:      {len(results)}")
        lines.append(f"  ✓ Найдено:         {found}")
        lines.append(f"  ✗ Не найдено:      {not_found}")
        lines.append(f"  ⚠ Ошибок:          {errors}")
        lines.append(f"  Эффективность:     {rate:.1f}%")
        lines.append(f"  Общее время:       {self._fmt_time(elapsed)}")
        lines.append(f"  Среднее на файл:   "
                     f"{self._fmt_time(elapsed / max(1, len(results)))}")
        lines.append("")
        lines.append("═" * 60)

        mp_counts = {}
        for r in results:
            mp = r.get('Маркетплейс', '-') or '-'
            mp_counts[mp] = mp_counts.get(mp, 0) + 1
        if mp_counts:
            lines.append("")
            lines.append("  Распределение по маркетплейсам:")
            lines.append("─" * 60)
            for mp, cnt in sorted(mp_counts.items(),
                                   key=lambda x: -x[1]):
                pct = cnt / max(1, len(results)) * 100
                lines.append(f"  {mp:<20} {cnt:>5}  ({pct:.0f}%)")
            lines.append("")

        missed = [r for r in results if r.get('Статус') != 'found']
        if missed:
            lines.append("")
            lines.append(f"  Файлы без результата ({len(missed)}):")
            lines.append("─" * 60)
            for r in missed[:50]:
                mark = "✗" if r['Статус'] == 'not_found' else "⚠"
                lines.append(f"  {mark} {r['Название файла']}")
            if len(missed) > 50:
                lines.append(f"  ... и ещё {len(missed) - 50}")

        if len(results) >= 10:
            lines.append("")
            lines.append("  ОТЧЁТ ПО ЭФФЕКТИВНОСТИ:")
            lines.append("─" * 60)
            lines.append(f"  Обработано:        {len(results)}")
            lines.append(f"  Найдено:           {found}  ({rate:.1f}%)")
            lines.append(f"  Среднее на файл:   "
                         f"{elapsed / max(1, len(results)):.1f} с")

        text = "\n".join(lines)
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.summary_box.configure(state="disabled")

    # ================= УТИЛИТЫ =================

    def _clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_map.clear()

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _clear_summary(self):
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.configure(state="disabled")

    def _fmt_time(self, seconds):
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds} с"
        m, s = divmod(seconds, 60)
        if m < 60:
            return f"{m} м {s} с"
        h, m = divmod(m, 60)
        return f"{h} ч {m} м"

    def on_close(self):
        if self.engine and self.engine.is_running():
            if not messagebox.askyesno("Закрыть?",
                                        "Обработка ещё идёт. Закрыть?"):
                return
            self.engine.stop()
        save_settings(self._collect_config())
        self.destroy()


def main():
    _install_excepthook()

    lic = check_license()
    if lic['status'] == 'ok':
        app = App(days_left=lic.get('days_left', 0))
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
        return

    if lic['status'] == 'expired':
        reason = (f"Срок лицензии истёк "
                  f"({lic['days_overdue']} дн. назад).\n"
                  f"Введите новый ключ.")
    else:
        reason = lic.get('reason', 'Требуется активация лицензии')

    ok, days_left = run_activation_window(reason)
    if not ok:
        try:
            sys.exit(0)
        except SystemExit:
            raise

    app = App(days_left=days_left)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()