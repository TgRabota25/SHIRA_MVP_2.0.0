"""Группировка фотографий по товарам (разделителям) и безопасные операции с файлами.

Режим «Фото» — отдельный от видеорежимов: фотографии не являются «коротким видео
длительностью ноль». Логика группировки и файловых операций тестируется без GUI и OCR.

Алгоритм группировки:
  1. Фото сортируются по естественному порядку имён (2 перед 10).
  2. Фото-разделитель открывает новую группу и входит в неё.
  3. Обычные фото между разделителями попадают в группу открывшего их разделителя.
  4. Фото после последнего разделителя продолжают последнюю группу.
  5. Фото до первого разделителя — в парковку.
  6. Если разделителей нет — весь набор в парковку.
  7. Фото, неясно подходящее под несколько шаблонов разделителей, не объединяет
     пачки молча: уходит в парковку с пометкой на проверку.

Копирование/перенос:
  * исходники не изменяются при копировании;
  * при переносе источник удаляется только после проверенной копии (сверка SHA-256);
  * каждая операция регистрируется в фото-реестре (photo-v2.sqlite3) для продолжения
    после сбоя: выполнённые операции пропускаются, неудачные повторяются.
"""

import hashlib
import os
import re
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from config import data_dir

DEFAULT_SEPARATOR_RULES = [
    {'name': 'Разделитель товара A', 'kind': 'A', 'regex': r'(?i)^\s*a\s*$', 'source': 'text'},
    {'name': 'Разделитель товара B', 'kind': 'B', 'regex': r'(?i)^\s*b\s*$', 'source': 'text'},
]

WINDOWS_RESERVED = {
    'CON','PRN','AUX','NUL','COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9',
    'LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9',
}
INVALID_NAME_CHARS = '<>:"/\\|?*'

OP_COPY = 'copy'
OP_MOVE = 'move'


def natural_key(path):
    """Естественная сортировка имён: фото2 перед фото10."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', Path(path).name)]


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def np_from_file(path):
    import numpy as np
    return np.fromfile(str(path), dtype=np.uint8)


def sanitize_stem(stem):
    for ch in INVALID_NAME_CHARS:
        stem = stem.replace(ch, '_')
    stem = stem.strip('. ')
    if not stem:
        stem = 'фото'
    if stem.upper() in WINDOWS_RESERVED:
        stem = stem + '_'
    return stem


def unique_destination(folder, name, source):
    """Путь назначения без коллизий (включая регистронезависимые).
    Если файл с таким же содержимым уже есть — возвращается существующий путь."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    source = Path(source)
    stem = sanitize_stem(Path(name).stem)
    suffix = Path(name).suffix

    def candidate_at(index):
        stem_part = stem if index == 0 else f'{stem} ({index})'
        return folder / (sanitize_stem(stem_part) + suffix)

    candidate = candidate_at(0)
    if not candidate.exists():
        return candidate
    try:
        if sha256_file(candidate) == sha256_file(source):
            return candidate
    except OSError:
        pass
    for index in range(1, 1000):
        candidate = candidate_at(index)
        if not candidate.exists():
            return candidate
        try:
            if sha256_file(candidate) == sha256_file(source):
                return candidate
        except OSError:
            pass
    raise OSError('Не удалось найти свободное имя для ' + name)


def folder_name_for(kind):
    if kind == 'park':
        return 'Парковка'
    return f'Товар {kind}'


@dataclass
class Group:
    kind: str          # 'A', 'B' или 'park'
    separator: Path | None
    items: list = field(default_factory=list)
    reason: str = ''

    @property
    def label(self):
        return folder_name_for(self.kind)

    @property
    def all_items(self):
        items = list(self.items)
        if self.separator is not None:
            items = [self.separator] + items
        return items


def split_groups(paths, classifications):
    """Разбить отсортированные пути на группы по разделителям.

    classifications: {path: 'A'|'B'|None|'ambiguous'}.
    Возвращает (группы, парковку_с_причинами).
    """
    groups = []
    park = []
    current = None
    for path in sorted(paths, key=natural_key):
        kind = classifications.get(path)
        if kind in ('A', 'B'):
            if current is not None:
                groups.append(current)
            current = Group(kind=kind, separator=Path(path), items=[])
        elif kind == 'ambiguous':
            if current is not None:
                groups.append(current)
                current = None
            park.append((Path(path), 'Неясный разделитель — пачки не объединяются молча'))
        else:
            if current is not None:
                current.items.append(Path(path))
            else:
                park.append((Path(path), 'До первого разделителя'))
    if current is not None:
        groups.append(current)
    return groups, park


class PhotoRegistry:
    """Реестр операций над фото: продолжение после сбоя без дублей и потерь."""
    def __init__(self, path=None):
        self.path = Path(path or data_dir() / 'photo-v2.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS photo_ops(
             id INTEGER PRIMARY KEY,session TEXT NOT NULL,group_label TEXT NOT NULL,
             group_kind TEXT NOT NULL,src TEXT NOT NULL,dst TEXT NOT NULL,op TEXT NOT NULL,
             state TEXT NOT NULL,sha256 TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',
             attempts INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL,updated REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_photo_ops_state ON photo_ops(state,created);
            CREATE TABLE IF NOT EXISTS photo_sessions(
             id INTEGER PRIMARY KEY,started REAL NOT NULL,finished REAL,
             op TEXT NOT NULL,dest TEXT NOT NULL,groups_count INTEGER NOT NULL DEFAULT 0,
             files_count INTEGER NOT NULL DEFAULT 0);
            ''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def start_session(self, op, dest, groups_count, files_count):
        with self._db() as db:
            cur = db.execute(
                'INSERT INTO photo_sessions(started,op,dest,groups_count,files_count) '
                'VALUES(?,?,?,?,?)', (time.time(), op, str(dest), groups_count, files_count))
            return cur.lastrowid

    def finish_session(self, session_id):
        with self._db() as db:
            db.execute('UPDATE photo_sessions SET finished=? WHERE id=?', (time.time(), session_id))

    def plan_items(self, session_id):
        """Список операций для сессии: (src, dst, group_label, group_kind, op)."""
        raise NotImplementedError  # операции регистрируются через register_ops

    def register_ops(self, session_id, rows):
        """rows: итератор кортежей (group_label, group_kind, src, dst, op)."""
        now = time.time()
        with self._db() as db:
            for group_label, group_kind, src, dst, op in rows:
                db.execute(
                    'INSERT INTO photo_ops(session,group_label,group_kind,src,dst,op,state,created,updated) '
                    'VALUES(?,?,?,?,?,?,?,?,?)',
                    (session_id, group_label, group_kind, str(src), str(dst), op, 'pending', now, now))

    def pending_ops(self, session_id):
        with self._db() as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM photo_ops WHERE session=? AND state IN (\'pending\',\'failed\') '
                'ORDER BY id', (session_id,))]

    def mark_done(self, op_id, sha256):
        with self._db() as db:
            db.execute('UPDATE photo_ops SET state=\'done\',sha256=?,error=\'\',attempts=attempts,updated=? WHERE id=?',
                       (sha256, time.time(), op_id))

    def mark_failed(self, op_id, error):
        with self._db() as db:
            db.execute('UPDATE photo_ops SET state=\'failed\',error=?,attempts=attempts+1,updated=? WHERE id=?',
                       (str(error)[:2000], time.time(), op_id))

    def counts(self, session_id):
        with self._db() as db:
            return dict(db.execute(
                'SELECT state,count(*) FROM photo_ops WHERE session=? GROUP BY state', (session_id,)))


def classify_photos(paths, cfg, rules=None, progress=None):
    """Классифицировать каждое фото: 'A'|'B'|None|'ambiguous'.

    Разделение по распознанному тексту/QR через recognition.recognize_frame.
    progress(callable, fraction) вызывается после каждого файла.
    """
    import cv2
    from recognition import recognize_frame

    if rules is None:
        rules = DEFAULT_SEPARATOR_RULES
    compiled = []
    for rule in rules:
        try:
            compiled.append((rule, re.compile(rule['regex'])))
        except re.error:
            continue

    result = {}
    total = len(paths)
    for index, path in enumerate(paths):
        kind = None
        matched = []
        try:
            frame = cv2.imdecode(np_from_file(path), cv2.IMREAD_COLOR)
            if frame is None:
                result[path] = None
                if progress: progress((index + 1) / total)
                continue
            findings = recognize_frame(frame, cfg, do_ocr=True)
            for rule, rx in compiled:
                for h in findings:
                    if rx.search(h.get('raw', '')) or rx.search(h.get('number', '')):
                        matched.append(rule['kind'])
            matched = set(matched)
            if len(matched) == 1:
                kind = matched.pop()
            elif len(matched) > 1:
                kind = 'ambiguous'
        except Exception:
            kind = None
        result[path] = kind
        if progress:
            progress((index + 1) / total)
    return result

def execute_plan(session_id, groups, park, dest_root, op, registry, progress=None):
    """Выполнить план копирования/переноса с проверкой и возможностью продолжения."""
    dest_root = Path(dest_root)
    total_files = sum(len(g.all_items) for g in groups) + len(park)
    rows = []
    for group in groups:
        folder = dest_root / group.label
        for item in group.all_items:
            rows.append((group.label, group.kind, item, unique_destination(folder, item.name, item), op))
    for item, reason in park:
        folder = dest_root / 'Парковка'
        rows.append(('Парковка', 'park', item, unique_destination(folder, item.name, item), op))
    registry.register_ops(session_id, rows)

    done = failed = 0
    for row in registry.pending_ops(session_id):
        src = Path(row['src']); dst = Path(row['dst']); op = row['op']
        try:
            if not src.is_file():
                raise FileNotFoundError(str(src))
            if op == OP_COPY:
                shutil.copy2(src, dst)
            elif op == OP_MOVE:
                shutil.copy2(src, dst)
                if not sha256_file(dst) == sha256_file(src):
                    raise OSError('Контрольная сумма после копирования не совпала')
                src.unlink()
            else:
                raise ValueError('Неизвестная операция ' + op)
            registry.mark_done(row['id'], sha256_file(dst))
            done += 1
        except Exception as exc:
            registry.mark_failed(row['id'], exc)
            failed += 1
        if progress:
            progress(done, failed, total_files)
    return done, failed