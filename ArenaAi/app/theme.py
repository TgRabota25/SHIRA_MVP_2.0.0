"""Дизайн-токеты и оформление приложения SHIRA MVP 2.0.0 (Тихая роскошь 2026).

Только view-слой: цвета, шрифты, отступы, радиусы, стили ttk.
Не трогает бизнес-логику, имена классов/методов/атрибутов виджетов не меняются.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict

# ---------------------------------------------------------------------------
# Цветовые палитры (светлая / тёмная). Авто resolving -> светлая (складское
# освещение часто яркое; тёмная — для смен и ночи, выбирается вручную).
# ---------------------------------------------------------------------------
PALETTES: Dict[str, Dict[str, str]] = {
    'light': {
        'ink': '#0f172a',
        'muted': '#475569',
        'surface': '#ffffff',
        'surface_alt': '#f8fafc',
        'border': '#e2e8f0',
        'border_hover': '#cbd5e1',
        'accent': '#2563eb',
        'accent_hover': '#1d4ed8',
        'accent_pressed': '#1e40af',
        'accent_soft': '#eef2ff',
        'success': '#15803d',
        'success_soft': '#f0fdf4',
        'warning': '#b45309',
        'warning_soft': '#fffbeb',
        'error': '#b91c1c',
        'error_soft': '#fef2f2',
        'info': '#0ea5e9',
        'info_soft': '#f0f9ff',
        # Заливка заполненных кнопок с белым текстом: WCAG AA 4.5:1 к белому
        # и ≥ 3:1 к поверхности обеих тем (расчитано по относительной яркости).
        'accent_btn': '#1e4ed8',
        'accent_btn_hover': '#1d4ed8',
        'accent_btn_pressed': '#1e3a8a',
        'success_btn': '#0e6b38',
        'success_btn_hover': '#0a4d24',
        'success_btn_pressed': '#0b3d20',
        'danger_btn': '#b91c1c',
        'danger_btn_hover': '#8f1818',
        'danger_btn_pressed': '#7f1d1d',
    },
    'dark': {
        'ink': '#f8fafc',
        'muted': '#94a3b8',
        'surface': '#0f172a',
        'surface_alt': '#1e293b',
        'border': '#334155',
        'border_hover': '#475569',
        'accent': '#3b82f6',
        'accent_hover': '#2563eb',
        'accent_pressed': '#1d4ed8',
        'accent_soft': '#1e1b4b',
        'success': '#22c55e',
        'success_soft': '#064e3b',
        'warning': '#f59e0b',
        'warning_soft': '#1c2a16',
        'error': '#ef4444',
        'error_soft': '#7f1d1d',
        'info': '#06b6d4',
        'info_soft': '#0c4a6e',
        # Кнопки — одинаковая заливка в обеих темах (цвет не несет смысла без текста).
        'accent_btn': '#1e4ed8',
        'accent_btn_hover': '#1d4ed8',
        'accent_btn_pressed': '#1e3a8a',
        'success_btn': '#0e6b38',
        'success_btn_hover': '#0a4d24',
        'success_btn_pressed': '#0b3d20',
        'danger_btn': '#b91c1c',
        'danger_btn_hover': '#8f1818',
        'danger_btn_pressed': '#7f1d1d',
    },
}

THEME_LABELS = {'light': 'Светлая', 'dark': 'Тёмная', 'auto': 'Авто'}

# ---------------------------------------------------------------------------
# Типографика (гротеск с кириллицей; цифры/идентификаторы — моноширина)
# ---------------------------------------------------------------------------
FONTS = {
    'ui': ('Segoe UI', 10),
    'ui_bold': ('Segoe UI', 10, 'bold'),
    'ui_large': ('Segoe UI', 11),
    'ui_heading': ('Segoe UI', 13, 'bold'),
    'mono': ('Consolas', 9),
    'mono_bold': ('Consolas', 9, 'bold'),
    'small': ('Segoe UI', 9),
    'small_bold': ('Segoe UI', 9, 'bold'),
}

# 4/8px сетка
SPACE = {'1': 4, '2': 8, '3': 12, '4': 16, '5': 20, '6': 24, '8': 32}
RADIUS = {'sm': 4, 'md': 6, 'lg': 8}

# Состояния задач -> семантические цвета (мягкие фоновые плашки, WCAG AA)
STATE_COLORS = {
    'pending': ('#0f172a', '#f1f5f9'),      # ink, bg (light)
    'running': ('#2563eb', '#eef2ff'),
    'done': ('#15803d', '#f0fdf4'),
    'review': ('#b45309', '#fffbeb'),
    'not_found': ('#475569', '#f8fafc'),
    'error': ('#b91c1c', '#fef2f2'),
    'cancelled': ('#64748b', '#f8fafc'),
    'partial': ('#b45309', '#fffbeb'),
    'accepted': ('#0ea5e9', '#f0f9ff'),
}

DEFAULT_THEME = 'light'


def resolve_theme(mode: str) -> str:
    """Режимы: light / dark / auto. auto -> light (без чтения реестра ОС)."""
    if mode in PALETTES:
        return mode
    return DEFAULT_THEME


def palette_for(mode: str) -> Dict[str, str]:
    return PALETTES[resolve_theme(mode)]


# ---------------------------------------------------------------------------
# Применение оформления к ttk-стилям и корневому окну
# ---------------------------------------------------------------------------
def apply_theme(root: tk.Tk | tk.Toplevel, mode: str = DEFAULT_THEME) -> Dict[str, str]:
    """Настроить ttk.Style под выбранную тему. Вернуть активную палитру.

    Безопасно вызывать многократно. Имена стилей (TButton, Accent.TButton,
    Success.TButton, Danger.TButton, Treeview, Treeview.Heading) не меняются,
    чтобы тесты и интеграции не сломались.
    """
    pal = palette_for(mode)
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass

    F = FONTS

    # Базовые поверхности
    style.configure('TFrame', background=pal['surface_alt'])
    style.configure('TLabelframe', background=pal['surface_alt'], bordercolor=pal['border'], relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=pal['surface_alt'], foreground=pal['muted'], font=F['small_bold'])

    # Метки
    style.configure('TLabel', background=pal['surface_alt'], foreground=pal['ink'], font=F['ui'])
    style.configure('Small.TLabel', background=pal['surface_alt'], foreground=pal['muted'], font=F['small'])
    style.configure('Heading.TLabel', background=pal['surface_alt'], foreground=pal['ink'], font=F['ui_heading'])

    # Кнопки
    style.configure('TButton', background=pal['surface'], foreground=pal['ink'],
                    font=F['ui'], bordercolor=pal['border'], borderwidth=1, focuscolor=pal['accent'],
                    padding=(12, 6))
    style.map('TButton',
              background=[('active', pal['surface_alt']), ('pressed', pal['border'])],
              foreground=[('active', pal['ink']), ('pressed', pal['ink'])])

    style.configure('Accent.TButton', background=pal['accent_btn'], foreground='#ffffff',
                    font=F['ui_bold'], bordercolor=pal['accent_btn_pressed'], borderwidth=1, focuscolor=pal['accent'],
                    padding=(14, 7))
    style.map('Accent.TButton',
              background=[('active', pal['accent_btn_hover']), ('pressed', pal['accent_btn_pressed']), ('disabled', '#94a3b8')],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('disabled', '#cbd5e1')])

    style.configure('Success.TButton', background=pal['success_btn'], foreground='#ffffff',
                    font=F['ui_bold'], bordercolor=pal['success_btn_pressed'], borderwidth=1, focuscolor=pal['success'],
                    padding=(12, 6))
    style.map('Success.TButton',
              background=[('active', pal['success_btn_hover']), ('pressed', pal['success_btn_pressed']), ('disabled', '#94a3b8')],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('disabled', '#cbd5e1')])

    style.configure('Danger.TButton', background=pal['danger_btn'], foreground='#ffffff',
                    font=F['ui_bold'], bordercolor=pal['danger_btn_pressed'], borderwidth=1, focuscolor=pal['error'],
                    padding=(12, 6))
    style.map('Danger.TButton',
              background=[('active', pal['danger_btn_hover']), ('pressed', pal['danger_btn_pressed']), ('disabled', '#94a3b8')],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('disabled', '#cbd5e1')])

    # Поля ввода и выпадающие списки
    style.configure('TEntry', fieldbackground=pal['surface'], foreground=pal['ink'],
                    bordercolor=pal['border'], insertcolor=pal['ink'], font=F['ui'], padding=5)
    style.map('TEntry', bordercolor=[('focus', pal['accent']), ('invalid', pal['error'])])

    style.configure('TCombobox', fieldbackground=pal['surface'], foreground=pal['ink'],
                    bordercolor=pal['border'], insertcolor=pal['ink'], font=F['ui'], padding=4)
    style.map('TCombobox', bordercolor=[('focus', pal['accent']), ('readonly', pal['border'])])

    # Таблица задач — первоклассная
    style.configure('Treeview', background=pal['surface'], fieldbackground=pal['surface'],
                    foreground=pal['ink'], bordercolor=pal['border'], borderwidth=1,
                    rowheight=30, font=F['ui'])
    style.map('Treeview', background=[('selected', pal['accent_soft'])], foreground=[('selected', pal['ink'])])
    style.configure('Treeview.Heading', background=pal['surface_alt'], foreground=pal['muted'],
                    font=F['small_bold'], bordercolor=pal['border'], borderwidth=1, relief='flat')
    style.map('Treeview.Heading', background=[('active', pal['border_hover'])])

    # Радиокнопки / флажки
    style.configure('TRadiobutton', background=pal['surface_alt'], foreground=pal['ink'], font=F['ui'])
    style.configure('TCheckbutton', background=pal['surface_alt'], foreground=pal['ink'], font=F['ui'])

    # Прогресс-бар
    style.configure('TProgressbar', troughcolor=pal['border'], bordercolor=pal['border'],
                    background=pal['accent'], lightcolor=pal['accent'], darkcolor=pal['accent'])

    # Корневое окно
    try:
        root.configure(bg=pal['surface_alt'])
    except Exception:
        pass

    # Цвета состояний задач для текущей темы (мягкие фоновые плашки)
    state_bg: Dict[str, str] = {}
    for state, (_ink, _bg_light) in STATE_COLORS.items():
        state_bg[state] = pal.get(state + '_soft', _bg_light) if (state + '_soft') in pal else _bg_light

    return {'palette': pal, 'state_bg': state_bg, 'fonts': F, 'space': SPACE, 'radius': RADIUS}


def state_tag_colors(mode: str = DEFAULT_THEME) -> Dict[str, str]:
    """Цвета фоновых плашек для тегов строк таблицы задач."""
    pal = PALETTES[resolve_theme(mode)]
    return {
        'pending': pal['surface'],
        'running': pal['accent_soft'],
        'done': pal['success_soft'],
        'review': pal['warning_soft'],
        'not_found': pal['surface_alt'],
        'error': pal['error_soft'],
        'cancelled': pal['surface_alt'],
        'partial': pal['warning_soft'],
        'accepted': pal['info_soft'],
    }
