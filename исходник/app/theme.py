"""Дизайн-токеты и оформление приложения SHIRA MVP 2.0.0 (Тихая роскошь 2026).

Современный дашборд-стиль: карточки, боковая навигация, статус-бэджи,
мягкие тени, generous whitespace, типографическая иерархия.
Только view-слой: цвета, шрифты, отступы, стили ttk, вспомогательные контейнеры.
Не трогает бизнес-логику.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Цветовая палитра — «Тихая роскошь 2026»
# База: slate/indigo. Акцент: глубокий синий. Эмоции: надёжность, тишина, точность.
# WCAG AA контраст соблюден для всех пар текст/фон.
# ---------------------------------------------------------------------------
PALETTES: Dict[str, Dict[str, str]] = {
    'light': {
        # Фоновые поверхности
        'canvas': '#f3f4f6',        # общий фон приложения
        'surface': '#ffffff',       # карточки, панели
        'surface_alt': '#f8fafc',   # вторичная поверхность
        # Текст
        'ink': '#0f172a',           # основной текст
        'muted': '#64748b',         # вспомогательный текст
        'muted_soft': '#94a3b8',    # заглушки, подсказки
        # Разделители и границы
        'border': '#e2e8f0',        # мягкая граница
        'border_soft': '#f1f5f9',   # почти невидимая граница
        'border_focus': '#2563eb',  # граница при фокусе
        # Акцент
        'accent': '#2563eb',
        'accent_hover': '#1d4ed8',
        'accent_pressed': '#1e40af',
        'accent_soft': '#eef2ff',
        'accent_text': '#1e3a8a',
        # Семантические цвета (мягкие фоновые бэджи + тёмный текст для читаемости)
        'success': '#15803d',
        'success_soft': '#f0fdf4',
        'success_text': '#14532d',
        'warning': '#b45309',
        'warning_soft': '#fffbeb',
        'warning_text': '#78350f',
        'error': '#b91c1c',
        'error_soft': '#fef2f2',
        'error_text': '#7f1d1d',
        'info': '#0ea5e9',
        'info_soft': '#f0f9ff',
        'info_text': '#0c4a6e',
        # Кнопки — заливка с белым текстом (WCAG AA ≥ 4.5:1)
        'accent_btn': '#1e4ed8',
        'accent_btn_hover': '#1d4ed8',
        'accent_btn_pressed': '#1e3a8a',
        'success_btn': '#0e6b38',
        'success_btn_hover': '#0a4d24',
        'success_btn_pressed': '#0b3d20',
        'danger_btn': '#b91c1c',
        'danger_btn_hover': '#8f1818',
        'danger_btn_pressed': '#7f1d1d',
        # Нейтральные кнопки (тёмный текст на светлом фоне)
        'neutral_bg': '#f1f5f9',
        'neutral_hover': '#e2e8f0',
        'neutral_pressed': '#cbd5e1',
        'neutral_text': '#334155',
    },
    'dark': {
        'canvas': '#0f172a',
        'surface': '#1e293b',
        'surface_alt': '#0f172a',
        'ink': '#f8fafc',
        'muted': '#94a3b8',
        'muted_soft': '#64748b',
        'border': '#334155',
        'border_soft': '#1e293b',
        'border_focus': '#3b82f6',
        'accent': '#3b82f6',
        'accent_hover': '#2563eb',
        'accent_pressed': '#1d4ed8',
        'accent_soft': '#1e1b4b',
        'accent_text': '#93c5fd',
        'success': '#22c55e',
        'success_soft': '#064e3b',
        'success_text': '#4ade80',
        'warning': '#f59e0b',
        'warning_soft': '#1c2a16',
        'warning_text': '#fbbf24',
        'error': '#ef4444',
        'error_soft': '#7f1d1d',
        'error_text': '#fca5a5',
        'info': '#06b6d4',
        'info_soft': '#0c4a6e',
        'info_text': '#22d3ee',
        'accent_btn': '#1e4ed8',
        'accent_btn_hover': '#1d4ed8',
        'accent_btn_pressed': '#1e3a8a',
        'success_btn': '#0e6b38',
        'success_btn_hover': '#0a4d24',
        'success_btn_pressed': '#0b3d20',
        'danger_btn': '#b91c1c',
        'danger_btn_hover': '#8f1818',
        'danger_btn_pressed': '#7f1d1d',
        'neutral_bg': '#334155',
        'neutral_hover': '#475569',
        'neutral_pressed': '#64748b',
        'neutral_text': '#e2e8f0',
    },
}

THEME_LABELS = {'light': 'Светлая', 'dark': 'Тёмная', 'auto': 'Авто'}

# ---------------------------------------------------------------------------
# Типографика — иерархия заголовков, цифры моноширинные для сканирования
# ---------------------------------------------------------------------------
FONTS = {
    'display': ('Segoe UI', 20, 'bold'),      # large page titles
    'heading': ('Segoe UI', 13, 'bold'),      # section titles
    'subheading': ('Segoe UI', 11, 'bold'),   # card titles
    'ui': ('Segoe UI', 10),                   # body text
    'ui_medium': ('Segoe UI', 10, 'bold'),    # emphasized body
    'small': ('Segoe UI', 9),                 # captions, labels
    'small_bold': ('Segoe UI', 9, 'bold'),
    'caption': ('Segoe UI', 8),               # tiny meta text
    'mono': ('Consolas', 9),                  # numbers, paths, IDs
    'mono_bold': ('Consolas', 9, 'bold'),
    'badge': ('Segoe UI', 9, 'bold'),         # status pills
}

# 4/8px сетка
SPACE = {'1': 4, '2': 8, '3': 12, '4': 16, '5': 20, '6': 24, '8': 32, '12': 48, '16': 64}
RADIUS = {'sm': 6, 'md': 10, 'lg': 14}

# Состояния задач -> семантические цвета для фоновых плашек и текста
STATE_THEME = {
    'pending':   ('pending',   '#0f172a', '#f1f5f9', '#334155'),
    'running':   ('running',   '#2563eb', '#eef2ff', '#1e3a8a'),
    'done':      ('done',      '#15803d', '#f0fdf4', '#14532d'),
    'review':    ('review',    '#b45309', '#fffbeb', '#78350f'),
    'not_found': ('not_found', '#475569', '#f8fafc', '#475569'),
    'error':     ('error',     '#b91c1c', '#fef2f2', '#7f1d1d'),
    'cancelled': ('cancelled', '#64748b', '#f8fafc', '#64748b'),
    'partial':   ('partial',   '#b45309', '#fffbeb', '#78350f'),
    'accepted':  ('accepted',  '#0ea5e9', '#f0f9ff', '#0c4a6e'),
}

DEFAULT_THEME = 'light'


def resolve_theme(mode: str) -> str:
    return mode if mode in PALETTES else DEFAULT_THEME


def palette_for(mode: str) -> Dict[str, str]:
    return PALETTES[resolve_theme(mode)]


# ---------------------------------------------------------------------------
# Применение оформления к ttk-стилям
# ---------------------------------------------------------------------------
def apply_theme(root: tk.Tk | tk.Toplevel, mode: str = DEFAULT_THEME) -> Dict[str, str]:
    pal = palette_for(mode)
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass

    F = FONTS
    S = SPACE

    # Корневое окно
    try:
        root.configure(bg=pal['canvas'])
    except Exception:
        pass

    # Базовые фреймы
    style.configure('TFrame', background=pal['canvas'])
    style.configure('Card.TFrame', background=pal['surface'], relief='flat', borderwidth=0)

    #.LabelFrame — карточки с заголовком
    style.configure('TLabelframe', background=pal['surface'], bordercolor=pal['border'],
                    relief='solid', borderwidth=1, lightcolor=pal['surface'], darkcolor=pal['surface'])
    style.configure('TLabelframe.Label', background=pal['surface'], foreground=pal['muted'],
                    font=F['small_bold'], padding=(0, 0, 0, 6))

    # Метки
    style.configure('TLabel', background=pal['canvas'], foreground=pal['ink'], font=F['ui'])
    style.configure('Surface.TLabel', background=pal['surface'], foreground=pal['ink'], font=F['ui'])
    style.configure('Muted.TLabel', background=pal['canvas'], foreground=pal['muted'], font=F['small'])
    style.configure('SurfaceMuted.TLabel', background=pal['surface'], foreground=pal['muted'], font=F['small'])
    style.configure('Heading.TLabel', background=pal['canvas'], foreground=pal['ink'], font=F['heading'])
    style.configure('SurfaceHeading.TLabel', background=pal['surface'], foreground=pal['ink'], font=F['subheading'])
    style.configure('Display.TLabel', background=pal['canvas'], foreground=pal['ink'], font=F['display'])

    # Кнопки
    style.configure('TButton', background=pal['neutral_bg'], foreground=pal['neutral_text'],
                    font=F['ui'], bordercolor=pal['border'], borderwidth=1, focuscolor=pal['border_focus'],
                    padding=(12, 8))
    style.map('TButton',
              background=[('active', pal['neutral_hover']), ('pressed', pal['neutral_pressed'])],
              foreground=[('active', pal['neutral_text']), ('pressed', pal['neutral_text'])])

    style.configure('Accent.TButton', background=pal['accent_btn'], foreground='#ffffff',
                    font=F['ui_medium'], bordercolor=pal['accent_btn_pressed'], borderwidth=0, focuscolor=pal['accent'],
                    padding=(14, 10))
    style.map('Accent.TButton',
              background=[('active', pal['accent_btn_hover']), ('pressed', pal['accent_btn_pressed']), ('disabled', '#94a3b8')],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('disabled', '#cbd5e1')])

    style.configure('Success.TButton', background=pal['success_btn'], foreground='#ffffff',
                    font=F['ui_medium'], bordercolor=pal['success_btn_pressed'], borderwidth=0, focuscolor=pal['success'],
                    padding=(12, 8))
    style.map('Success.TButton',
              background=[('active', pal['success_btn_hover']), ('pressed', pal['success_btn_pressed'])],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])

    style.configure('Danger.TButton', background=pal['danger_btn'], foreground='#ffffff',
                    font=F['ui_medium'], bordercolor=pal['danger_btn_pressed'], borderwidth=0, focuscolor=pal['error'],
                    padding=(12, 8))
    style.map('Danger.TButton',
              background=[('active', pal['danger_btn_hover']), ('pressed', pal['danger_btn_pressed'])],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])

    style.configure('Ghost.TButton', background=pal['canvas'], foreground=pal['muted'],
                    font=F['ui'], bordercolor=pal['border'], borderwidth=1, focuscolor=pal['border_focus'],
                    padding=(12, 8))
    style.map('Ghost.TButton',
              background=[('active', pal['neutral_hover']), ('pressed', pal['neutral_pressed'])],
              foreground=[('active', pal['ink']), ('pressed', pal['ink'])])

    # Поля ввода
    style.configure('TEntry', fieldbackground=pal['surface'], foreground=pal['ink'],
                    bordercolor=pal['border'], insertcolor=pal['accent'], font=F['ui'], padding=6)
    style.map('TEntry', bordercolor=[('focus', pal['border_focus']), ('invalid', pal['error'])])

    style.configure('TCombobox', fieldbackground=pal['surface'], foreground=pal['ink'],
                    bordercolor=pal['border'], insertcolor=pal['ink'], font=F['ui'], padding=5)
    style.map('TCombobox', bordercolor=[('focus', pal['border_focus']), ('readonly', pal['border'])])

    # Таблица задач — чистая, с мягкими границами, без тяжелого хрома
    style.configure('Treeview', background=pal['surface'], fieldbackground=pal['surface'],
                    foreground=pal['ink'], bordercolor=pal['border'], borderwidth=1,
                    rowheight=40, font=F['ui'])
    style.map('Treeview',
              background=[('selected', pal['accent_soft']), ('focus', pal['accent_soft'])],
              foreground=[('selected', pal['accent_text']), ('focus', pal['accent_text'])])
    style.configure('Treeview.Heading', background=pal['surface_alt'], foreground=pal['muted'],
                    font=F['small_bold'], bordercolor=pal['border'], borderwidth=0, relief='flat')
    style.map('Treeview.Heading', background=[('active', pal['border_soft'])])

    # Переключатели / флажки
    style.configure('TRadiobutton', background=pal['canvas'], foreground=pal['ink'], font=F['ui'])
    style.configure('TCheckbutton', background=pal['canvas'], foreground=pal['ink'], font=F['ui'])

    # Прогресс-бар — тонкий, акцентный
    style.configure('TProgressbar', troughcolor=pal['border_soft'], bordercolor=pal['border_soft'],
                    background=pal['accent'], lightcolor=pal['accent'], darkcolor=pal['accent'],
                    thickness=6)

    return {'palette': pal, 'fonts': F, 'space': SPACE, 'radius': RADIUS}


# ---------------------------------------------------------------------------
# Вспомогательные контейнеры — карточки, разделы, бэджи
# ---------------------------------------------------------------------------
def make_card(parent, **kwargs) -> tk.Frame:
    """Карточка с мягкой границей и фоном surface."""
    card = tk.Frame(parent, bg=PALETTES['light']['surface'], highlightbackground=PALETTES['light']['border'],
                    highlightthickness=1, bd=0, **kwargs)
    return card


def make_section(parent, title: str | None = None) -> Tuple[tk.Frame, tk.Frame]:
    """Раздел с опциональным заголовком. Возвращает (контейнер, тело)."""
    container = tk.Frame(parent, bg=PALETTES['light']['canvas'])
    if title:
        head = tk.Frame(container, bg=PALETTES['light']['canvas'])
        head.pack(fill='x', pady=(0, SPACE['2']))
        tk.Label(head, text=title, bg=PALETTES['light']['canvas'], fg=PALETTES['light']['muted'],
                 font=FONTS['caption']).pack(anchor='w')
    body = tk.Frame(container, bg=PALETTES['light']['canvas'])
    body.pack(fill='both', expand=True)
    return container, body


def status_badge(parent, state: str, palette: Dict[str, str]) -> tk.Label:
    """Статус-бэдж (плодка) для строки таблицы."""
    _key, fg, bg, _text_fg = STATE_THEME.get(state, STATE_THEME['pending'])
    # В тёмной теме используем мягкий фон, в светлой — тоже мягкий
    label = tk.Label(parent, text=state.upper(), bg=bg, fg=fg, font=FONTS['badge'], padx=8, pady=2)
    return label


def stat_card(parent, value: str, label: str, palette: Dict[str, str], accent: str = 'accent') -> tk.Frame:
    """Статистическая карточка дашборда."""
    card = tk.Frame(parent, bg=palette['surface'], highlightbackground=palette['border'],
                    highlightthickness=1, bd=0, padx=SPACE['4'], pady=SPACE['3'])
    tk.Label(card, text=value, bg=palette['surface'], fg=palette['ink'], font=FONTS['display']).pack(anchor='w')
    tk.Label(card, text=label, bg=palette['surface'], fg=palette['muted'], font=FONTS['caption']).pack(anchor='w', pady=(SPACE['1'], 0))
    return card


def divider(parent) -> tk.Frame:
    """Тонкий разделитель."""
    return tk.Frame(parent, bg=PALETTES['light']['border_soft'], height=1)


def apply_palette_to_widget(widget, palette: Dict[str, str], kind: str = 'surface'):
    """Применить цвета палитры к произвольному tk-визиджу (Text, Listbox, Canvas)."""
    bg_key = {'surface': 'surface', 'surface_alt': 'surface_alt', 'canvas': 'canvas'}.get(kind, 'surface')
    widget.configure(bg=palette[bg_key], fg=palette['ink'], insertbackground=palette['ink'],
                     highlightthickness=0, borderwidth=0)

