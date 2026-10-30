"""
scanner_core.py — Ядро сканера этикеток.
"""
import cv2
import pytesseract
import easyocr
import pandas as pd
import numpy as np
import os
import sys
import re
import time
import json
import uuid
import hashlib
import sqlite3
import threading
import multiprocessing
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Empty as QueueEmpty
from datetime import datetime

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    HAS_PYZBAR = True
except Exception:
    pyzbar_decode = None
    HAS_PYZBAR = False




class DatabaseError(RuntimeError):
    """Понятная ошибка доступа к локальной базе SHIRA."""


def _atomic_write_json(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    tmp = path + f".tmp-{os.getpid()}-{threading.get_ident()}"
    backup = path + ".bak"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.isfile(path):
            shutil.copy2(path, backup)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _source_key(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path or '')))


def _file_identity(filepath, block_size=1024 * 1024):
    path = os.path.realpath(os.path.abspath(filepath))
    st = os.stat(path)
    size = int(st.st_size)
    mtime_ns = int(st.st_mtime_ns)
    digest = hashlib.sha256()
    digest.update(str(size).encode('ascii'))
    with open(path, 'rb') as f:
        digest.update(f.read(block_size))
        if size > block_size:
            f.seek(max(0, size - block_size))
            digest.update(f.read(block_size))
    fingerprint = digest.hexdigest()
    source = _source_key(os.path.dirname(path))
    name_lower = os.path.basename(path).lower().strip()
    file_id = hashlib.sha256(
        f"{source}|{name_lower}|{size}|{mtime_ns}|{fingerprint}".encode('utf-8')
    ).hexdigest()
    return {
        'file_id': file_id, 'size': size, 'mtime_ns': mtime_ns,
        'fingerprint': fingerprint, 'source_key': source,
    }


def _safe_spreadsheet_text(value):
    if not isinstance(value, str):
        return value
    probe = value.lstrip(' \t\r\n\x00\x0b\x0c')
    if probe.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _easyocr_worker_main(request_q, response_q, model_dir):
    try:
        reader = easyocr.Reader(
            ['ru', 'en'], gpu=False, verbose=False,
            model_storage_directory=model_dir, download_enabled=False)
        response_q.put(('ready', None))
    except BaseException as exc:
        response_q.put(('init_error', f'{type(exc).__name__}: {exc}'))
        return
    while True:
        item = request_q.get()
        if item is None:
            return
        job_id, image = item
        try:
            result = reader.readtext(
                image, detail=1, paragraph=False, canvas_size=1600,
                mag_ratio=1.0, text_threshold=0.5, low_text=0.3,
                link_threshold=0.4)
            response_q.put(('result', job_id, result))
        except BaseException as exc:
            response_q.put(
                ('error', job_id, f'{type(exc).__name__}: {exc}'))


class EasyOCRWorker:
    def __init__(self, model_dir, stop_event, startup_timeout=120):
        self.model_dir = model_dir
        self.stop_event = stop_event
        self.startup_timeout = startup_timeout
        self._ctx = multiprocessing.get_context('spawn')
        self._process = None
        self._requests = None
        self._responses = None
        self._lock = threading.Lock()
        self._job_id = 0

    def _stop_process(self):
        process = self._process
        if process is not None and process.is_alive():
            try:
                self._requests.put_nowait(None)
                process.join(1.0)
            except Exception:
                pass
            if process.is_alive():
                process.terminate()
                process.join(3.0)
            if process.is_alive() and hasattr(process, 'kill'):
                process.kill()
                process.join(1.0)
        for q in (self._requests, self._responses):
            try:
                if q is not None:
                    q.close()
                    q.join_thread()
            except Exception:
                pass
        self._process = self._requests = self._responses = None

    def close(self):
        with self._lock:
            self._stop_process()

    def cancel(self):
        process = self._process
        if process is not None and process.is_alive():
            try:
                process.terminate()
            except Exception:
                pass

    def _start(self):
        self._stop_process()
        self._requests = self._ctx.Queue(maxsize=1)
        self._responses = self._ctx.Queue(maxsize=2)
        self._process = self._ctx.Process(
            target=_easyocr_worker_main,
            args=(self._requests, self._responses, self.model_dir),
            daemon=True)
        self._process.start()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                self._stop_process()
                raise RuntimeError('EasyOCR остановлен пользователем')
            if not self._process.is_alive():
                self._stop_process()
                raise RuntimeError('Процесс EasyOCR завершился при запуске')
            try:
                msg = self._responses.get(timeout=0.2)
            except QueueEmpty:
                continue
            if msg[0] == 'ready':
                return
            self._stop_process()
            raise RuntimeError(msg[1] if len(msg) > 1 else 'Ошибка EasyOCR')
        self._stop_process()
        raise TimeoutError('EasyOCR не запустился за отведённое время')

    def call(self, image, timeout):
        with self._lock:
            if self._process is None or not self._process.is_alive():
                self._start()
            self._job_id += 1
            job_id = self._job_id
            self._requests.put((job_id, image), timeout=2)
            deadline = time.monotonic() + max(1, float(timeout))
            while time.monotonic() < deadline:
                if self.stop_event.is_set():
                    self._stop_process()
                    raise RuntimeError('EasyOCR остановлен пользователем')
                if not self._process.is_alive():
                    self._stop_process()
                    raise RuntimeError('Процесс EasyOCR аварийно завершился')
                try:
                    msg = self._responses.get(timeout=0.2)
                except QueueEmpty:
                    continue
                if len(msg) >= 2 and msg[1] != job_id:
                    continue
                if msg[0] == 'result':
                    return msg[2]
                raise RuntimeError(msg[2] if len(msg) > 2 else 'Ошибка EasyOCR')
            self._stop_process()
            raise TimeoutError(f'EasyOCR превысил тайм-аут {timeout} с')


# ================= ПУТИ =================

def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def _default_data_dir():
    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(
            os.path.join(os.path.dirname(sys.executable), 'data_dir.txt'))
    candidates.append(os.path.join(os.path.abspath("."), 'data_dir.txt'))

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    line = f.readline().strip()
                    if line:
                        return line
            except Exception:
                pass

    if os.name == 'nt':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.path.expanduser('~')
    return os.path.join(base, 'SHIRA')


def _ensure_dir(path):
    if not path:
        return path
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def _resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    p = os.path.join(base, rel)
    if os.path.exists(p):
        return p
    alt = os.path.join(_app_dir(), rel)
    if os.path.exists(alt):
        return alt
    return p


def _abs_user_path(path, data_dir=None):
    if not path:
        return path
    if os.path.isabs(path):
        return path
    base = data_dir or _default_data_dir()
    return os.path.join(base, path)


def check_free_space(path, required_gb=2.0):
    try:
        target = path or _default_data_dir()
        while target and not os.path.isdir(target):
            parent = os.path.dirname(target)
            if parent == target:
                break
            target = parent
        if not target or not os.path.isdir(target):
            return True, 0.0
        total, used, free = shutil.disk_usage(target)
        free_gb = free / (1024 ** 3)
        return free_gb >= required_gb, free_gb
    except Exception:
        return True, 0.0


# ================= АВТОНАСТРОЙКА =================

def auto_detect_config():
    try:
        import psutil
        cpu_cores = psutil.cpu_count(logical=False) or 2
        cpu_threads = psutil.cpu_count(logical=True) or cpu_cores
        ram_gb = int(round(psutil.virtual_memory().total / (1024 ** 3)))
    except Exception:
        cpu_cores = multiprocessing.cpu_count()
        cpu_threads = cpu_cores
        ram_gb = 8

    if cpu_cores <= 2 or ram_gb < 6:
        tier = 'low'
    elif cpu_cores <= 4 or ram_gb < 12:
        tier = 'mid'
    else:
        tier = 'high'

    if tier == 'low':
        return {
            'scan_seconds': 2, 'frames_count': 2,
            'worker_threads': 2, 'easyocr_concurrency': 1,
            'performance_mode': 'fast',
            '_info': {'cpu': cpu_cores, 'threads': cpu_threads,
                      'ram_gb': ram_gb, 'tier': tier,
                      'name': 'Слабый ПК'},
        }
    elif tier == 'mid':
        return {
            'scan_seconds': 2, 'frames_count': 3,
            'worker_threads': min(cpu_threads, 8),
            'easyocr_concurrency': max(1, cpu_cores // 2),
            'performance_mode': 'auto',
            '_info': {'cpu': cpu_cores, 'threads': cpu_threads,
                      'ram_gb': ram_gb, 'tier': tier,
                      'name': 'Средний ПК'},
        }
    else:
        return {
            'scan_seconds': 3, 'frames_count': 4,
            'worker_threads': min(cpu_threads, 16),
            'easyocr_concurrency': max(1, cpu_cores // 2),
            'performance_mode': 'full',
            '_info': {'cpu': cpu_cores, 'threads': cpu_threads,
                      'ram_gb': ram_gb, 'tier': tier,
                      'name': 'Мощный ПК'},
        }


def auto_performance_mode():
    cores = multiprocessing.cpu_count()
    return 'fast' if cores <= 2 else 'full'


def apply_performance_mode(cfg):
    mode = cfg.get('performance_mode', 'auto')
    if mode == 'auto':
        mode = auto_performance_mode()
    cfg['performance_mode_effective'] = mode

    if mode == 'fast':
        cfg['enabled_methods'] = {
            'QR':       True,
            'C6_easy':  False,
            'C5_easy':  False,
            'C2_clahe': True,
            'C3_adapt': True,
            'C1_otsu':  True,
            'C4_otsu':  True,
        }
        cfg['max_width'] = min(cfg.get('max_width', 1500), 1200)
        cfg['worker_threads'] = min(cfg.get('worker_threads', 4), 2)
    return cfg


# ================= ЛИЦЕНЗИРОВАНИЕ =================
LICENSE_HASHES = {
    "f952318d2e50e37e2046e730062bd381aed32e42452390d364cf8268bca247c5",
    "f3f95275f48af2279d59940e03b21aff7897a6682dc5454ea2ea895a33f423ea",
    "fdd00984e9a0de348c497e5e513291bd9580cb95263aa6822cbf76ca8ecda36d",
    "1ef90282c117fdcdef19f94ae6147ffc0bb6b608fd1e69edc6039f21bd1a54a5",
    "6baa70e7a949d397248ed28ac52413b2b9d11a5005010b1865e4a7d4611290e8",
    "07faac137b3d7cccf0a5f5a04a116ac982164daa6a68b0009de4f4ae90618d21",
    "75ffe3b1f8283092f2f35171debbe9c8689e2ea0c077e10aa1dadbfd31303d4c",
    "97bedb2af8955bb78bfd9b2cb8a4b7600e55dbbb3b3d8d2d27c589c163b5e9f7",
    "dea07cbd5929b491a5a46ca3d90c284775a083d8584b81166564f9636d42c769",
    "54c445a358f5ff662210284a06e830fe4d20dc6531911d2d97a11a943397ab1a",
    "aace6a2373e09c65afcdcf7ac9f4de53419ec989374100efcd8fd8fe5ace48aa",
    "a98fb82c1f1c94586816eca6728e1425f713533351c76721f26c0543b9dca995",
    "6b7e75fcfa5144ae456cc9f8af961675305895963d70f465dbe397a8dd770900",
    "b07e622da1d4308b4e0fcb98a1cb2b9ce7ae869bb33f6128ebf72e2b1115e94b",
    "11a30c4d87c57d8e49b1d6887d914c269196fa122a99d073fd0cc8c6ddc72730",
    "b180a45a275d6bd32db2777b0216b76f7f6def993e7e270cb01024d87f7e1ed0",
    "1ef9a1e7b60e95132cae0deb8a4cf22c5a95edfb19648296ad3af45e0407e75c",
    "fccb798da74f6b3e6a7ea9e8562b93e621485bf695d68d10f3ae4d069e718a84",
    "0945316d061c9f8a9118108e8b80854b8e2c432e916b7e347c13de26aa473939",
    "c86bab10b7fcc28bbf4bd92b9734c6fb933eff2a4f2fe593306e931ce7642e1e",
    "b91871c23ea9b92755050f77054e0aca29320dcabd162f50f473c459e865199c",
    "5c5bb3afe17c3742e4faa5edf43b0b2601548b32b5f96511786ffe7d93ed04b5",
    "4f24f39650c59322812a20b083113281a71e0a40abd9cf69e0c46a66a1676f15",
    "26e5d10ae5228ba29f9e7735c34db04789a41383f6e67bc8ef4bf987dc30c245",
}
LICENSE_PERIOD_DAYS = 30
DB_SCHEMA_VERSION = 3


def _license_file_path():
    if os.name == 'nt':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.path.expanduser('~')
    folder = os.path.join(base, 'SHIRA')
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return os.path.join(folder, 'license.json')


def _machine_id():
    parts = []
    if os.name == 'nt':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if guid:
                parts.append(f"win:{guid}")
        except Exception:
            pass
    try:
        mac = uuid.getnode()
        if not ((mac >> 40) & 1):
            parts.append(f"mac:{mac:012x}")
    except Exception:
        pass
    try:
        host = os.environ.get('COMPUTERNAME', '') or ''
        if host:
            parts.append(f"host:{host.lower()}")
    except Exception:
        pass
    if not parts:
        parts.append("fallback:no-identifiers")
    return hashlib.sha256("|".join(parts).encode('utf-8')).hexdigest()[:32]


def _sha256(text):
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()


def _load_license_file():
    path = _license_file_path()
    if not os.path.isfile(path):
        return None
    for candidate in (path, path + '.bak'):
        try:
            with open(candidate, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _save_license_file(data):
    try:
        _atomic_write_json(_license_file_path(), data)
        return True
    except (OSError, TypeError, ValueError):
        return False


def check_license():
    data = _load_license_file()
    if not data:
        return {'status': 'need', 'reason': 'Лицензия не активирована'}
    if data.get('machine_id') != _machine_id():
        return {'status': 'invalid',
                'reason': 'Лицензия привязана к другому компьютеру'}
    used = data.get('used_keys', [])
    if not used:
        return {'status': 'need', 'reason': 'Нет активных ключей'}
    last = used[-1]
    if last.get('hash', '') not in LICENSE_HASHES:
        return {'status': 'invalid', 'reason': 'Ключ недействителен'}
    try:
        dt = datetime.fromisoformat(last.get('activated_at', ''))
    except Exception:
        return {'status': 'need', 'reason': 'Повреждена дата активации'}
    days = (datetime.now() - dt).days
    if days < LICENSE_PERIOD_DAYS:
        return {'status': 'ok', 'days_left': LICENSE_PERIOD_DAYS - days}
    return {'status': 'expired', 'days_overdue': days - LICENSE_PERIOD_DAYS}


def activate_license(key):
    key = (key or '').strip()
    if not key:
        return False, "Введите ключ активации"
    key_hash = _sha256(key)
    if key_hash not in LICENSE_HASHES:
        return False, "Неверный ключ активации"
    data = _load_license_file() or {}
    machine = _machine_id()
    if data.get('machine_id') and data['machine_id'] != machine:
        return False, "Лицензия уже активирована на другом компьютере"
    used = data.get('used_keys', [])
    for entry in used:
        if entry.get('hash') == key_hash:
            return False, "Этот ключ уже был использован"
    used.append({
        'hash': key_hash,
        'activated_at': datetime.now().isoformat(timespec='seconds'),
    })
    data = {'machine_id': machine, 'used_keys': used, 'version': 1}
    if not _save_license_file(data):
        return False, "Не удалось сохранить лицензию на диск"
    return True, "Лицензия активирована"


# ================= ПАТТЕРНЫ =================
P_OZON_OLD = re.compile(r'\b\d{6}\s*\d{4}\s*[-—]\s*\d{4}\s*[-—]\s*\d{1,3}\b')
P_OZON_OLD_SOFT = re.compile(r'\b\d{6}\s+\d{4}\s+\d{4}\s+\d{1,3}\b')

P_OZON_NEW = re.compile(r'^[iI]{2}\d{11}$')
P_OZON_NEW_SOFT = re.compile(r'\b[iI]{2}\s*\d{10,12}\b')

P_YANDEX_CARGO = re.compile(r'^\d{11}-\d{1,3}$')
P_YANDEX_CARGO_SOFT = re.compile(r'\b\d{10,12}\s*[-—]\s*\d{1,3}\b')

P_YANDEX_ORDER = re.compile(r'^\d{11}$')

STRICT_PATTERNS = [P_OZON_OLD, P_YANDEX_CARGO_SOFT, P_OZON_NEW_SOFT]
SOFT_PATTERNS = [P_OZON_OLD_SOFT]

ALL_METHODS = [
    ('QR',       'QR-код',                           1, 'qr',   3),
    ('C6_easy',  'EasyOCR · зона этикетки',          2, 'easy', 30),
    ('C5_easy',  'EasyOCR · полный кадр',            3, 'easy', 30),
    ('C2_clahe', 'Tesseract · усиленный контраст',   4, 'tess', 8),
    ('C3_adapt', 'Tesseract · адаптивный контраст',  5, 'tess', 8),
    ('C1_otsu',  'Tesseract · простой контраст',     6, 'tess', 8),
    ('C4_otsu',  'Tesseract · зона этикетки',        7, 'tess', 8),
]

VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.m4v')


def default_config():
    return {
        'data_dir': _default_data_dir(),
        'video_folder': 'videos',
        'output_excel': 'ozon_numbers.xlsx',
        'scan_seconds': 2,
        'frames_count': 3,
        'max_width': 1500,
        'sharpness_min': 30,
        'worker_threads': min(multiprocessing.cpu_count() * 2, 16),
        'easyocr_concurrency': max(1, multiprocessing.cpu_count() // 2),
        'confidence_fast_exit': 0.75,
        'consensus_exit': 2,
        'tesseract_cmd': '',
        'enabled_methods': {k: True for k, *_ in ALL_METHODS},
        'save_debug': False,
        'debug_dir': 'debug',
        'db_path': 'checked_videos.db',
        'performance_mode': 'auto',
        'enable_rotation': True,
        'enable_qr_align': True,
        'enable_stacking': True,
        'resume': True,
    }


# ================= УТИЛИТЫ =================

def list_videos(folder):
    if not folder or not os.path.isdir(folder):
        return []
    return sorted([f for f in os.listdir(folder)
                   if f.lower().endswith(VIDEO_EXTS)])


def detect_marketplace(number):
    if not number:
        return '-'
    s = number.strip()

    if P_OZON_NEW.match(s):
        return 'Ozon'
    if P_OZON_NEW_SOFT.search(s):
        return 'Ozon'
    if P_YANDEX_CARGO.match(s):
        return 'Yandex Market'
    if P_YANDEX_CARGO_SOFT.search(s):
        return 'Yandex Market'
    if P_YANDEX_ORDER.match(s):
        return 'Yandex Market'
    if P_OZON_OLD.search(s) or P_OZON_OLD_SOFT.search(s):
        return 'Ozon'

    digits_only = re.sub(r'\D', '', s)
    if len(digits_only) >= 15:
        return 'Ozon'
    if 11 <= len(digits_only) <= 12:
        return 'Yandex Market'
    return 'Неизвестно'


# ================= КЭШ + ИСТОРИЯ =================

class VideoCache:
    def __init__(self, db_path, data_dir=None):
        if not os.path.isabs(db_path):
            db_path = _abs_user_path(db_path, data_dir)
        self.db_path = db_path
        _ensure_dir(os.path.dirname(db_path))
        self._lock = threading.RLock()
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self):
        try:
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY, value TEXT
                    )
                """)
                cols = [r[1] for r in conn.execute(
                    "PRAGMA table_info(checked_videos)")]
                if cols and 'file_id' not in cols:
                    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                    backup_path = f"{self.db_path}.backup-{stamp}"
                    backup = sqlite3.connect(backup_path)
                    try:
                        conn.backup(backup)
                    finally:
                        backup.close()

                    old_rows = [dict(r) for r in conn.execute(
                        "SELECT * FROM checked_videos")]
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("DROP INDEX IF EXISTS idx_checked_at")
                    conn.execute(
                        "ALTER TABLE checked_videos RENAME TO checked_videos_legacy")
                    self._create_current_table(conn)
                    for row in old_rows:
                        filename = str(row.get('filename') or '')
                        filename_lower = str(
                            row.get('filename_lower') or filename.lower().strip())
                        size = int(row.get('file_size') or 0)
                        source_folder = str(row.get('source_folder') or '')
                        source_key = _source_key(source_folder) if source_folder else ''
                        seed = (f"legacy|{source_key}|{filename_lower}|{size}|"
                                f"{row.get('checked_at') or ''}")
                        file_id = hashlib.sha256(seed.encode('utf-8')).hexdigest()
                        conn.execute("""
                            INSERT OR REPLACE INTO checked_videos
                                (file_id, source_key, filename_lower, file_size,
                                 file_mtime_ns, fingerprint, filename, number, qr,
                                 marketplace, status, elapsed, checked_at,
                                 source_folder)
                            VALUES (?, ?, ?, ?, 0, '', ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (file_id, source_key, filename_lower, size,
                              filename, row.get('number'), row.get('qr'),
                              row.get('marketplace'), row.get('status'),
                              row.get('elapsed'), row.get('checked_at'),
                              source_folder))
                    copied = conn.execute(
                        "SELECT COUNT(*) FROM checked_videos").fetchone()[0]
                    if copied != len(old_rows):
                        raise DatabaseError(
                            f'Миграция БД: ожидалось {len(old_rows)}, перенесено {copied}')
                    conn.execute("DROP TABLE checked_videos_legacy")
                else:
                    self._create_current_table(conn)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id TEXT, filename_lower TEXT NOT NULL,
                        file_size INTEGER NOT NULL, file_mtime_ns INTEGER DEFAULT 0,
                        fingerprint TEXT DEFAULT '', filename TEXT NOT NULL,
                        number TEXT, qr TEXT, marketplace TEXT, status TEXT,
                        elapsed REAL, checked_at TEXT, source_folder TEXT
                    )
                """)
                history_cols = {r[1] for r in conn.execute(
                    "PRAGMA table_info(history)")}
                for name, definition in (
                        ('file_id', 'TEXT'),
                        ('file_mtime_ns', 'INTEGER DEFAULT 0'),
                        ('fingerprint', "TEXT DEFAULT ''")):
                    if name not in history_cols:
                        conn.execute(
                            f"ALTER TABLE history ADD COLUMN {name} {definition}")
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_history_checked_at
                    ON history(checked_at DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_history_file
                    ON history(filename_lower)
                """)
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ('schema_version', str(DB_SCHEMA_VERSION)))
                conn.commit()
        except (sqlite3.Error, OSError, DatabaseError) as exc:
            raise DatabaseError(
                f"Не удалось подготовить базу '{self.db_path}': {exc}") from exc


    def _create_current_table(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checked_videos (
                file_id TEXT PRIMARY KEY,
                source_key TEXT NOT NULL,
                filename_lower TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_mtime_ns INTEGER NOT NULL,
                fingerprint TEXT NOT NULL,
                filename TEXT NOT NULL,
                number TEXT, qr TEXT, marketplace TEXT, status TEXT,
                elapsed REAL, checked_at TEXT, source_folder TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checked_at
            ON checked_videos(checked_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checked_source
            ON checked_videos(source_key, filename_lower)
        """)

    def get(self, filename, file_size):
        key = (filename.lower().strip(), int(file_size))
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM checked_videos "
                "WHERE filename_lower=? AND file_size=?",
                key).fetchone()
        return dict(row) if row else None

    def find_existing(self, folder, filenames):
        found = []
        if not filenames:
            return found
        try:
            with self._lock, self._connect() as conn:
                for name in filenames:
                    fp = os.path.join(folder, name)
                    try:
                        ident = _file_identity(fp)
                    except OSError:
                        continue
                    row = conn.execute(
                        "SELECT 1 FROM checked_videos WHERE file_id=? LIMIT 1",
                        (ident['file_id'],)).fetchone()
                    if row:
                        found.append((name, ident['size']))
            return found
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка поиска в кэше: {exc}') from exc

    def put(self, filename, file_size, number, qr, marketplace,
            status, elapsed, source_folder=None, identity=None):
        if status == 'error':
            return
        source_folder = os.path.realpath(os.path.abspath(source_folder or ''))
        filepath = os.path.join(source_folder, filename)
        identity = identity or _file_identity(filepath)
        now = datetime.now().isoformat(timespec='seconds')
        name_lower = filename.lower().strip()
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "DELETE FROM checked_videos "
                    "WHERE source_key=? AND filename_lower=?",
                    (identity['source_key'], name_lower))
                conn.execute("""
                    INSERT INTO checked_videos
                        (file_id, source_key, filename_lower, file_size,
                         file_mtime_ns, fingerprint, filename, number, qr,
                         marketplace, status, elapsed, checked_at, source_folder)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (identity['file_id'], identity['source_key'], name_lower,
                      identity['size'], identity['mtime_ns'],
                      identity['fingerprint'], filename, number, qr, marketplace,
                      status, elapsed, now, source_folder))
                conn.execute("""
                    INSERT INTO history
                        (file_id, filename_lower, file_size, file_mtime_ns,
                         fingerprint, filename, number, qr, marketplace, status,
                         elapsed, checked_at, source_folder)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (identity['file_id'], name_lower, identity['size'],
                      identity['mtime_ns'], identity['fingerprint'], filename,
                      number, qr, marketplace, status, elapsed, now, source_folder))
                conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка записи результата: {exc}') from exc

    def get_not_found(self, limit=10000):
        try:
            with self._lock, self._connect() as conn:
                rows = conn.execute("""
                    SELECT filename, file_size, status, source_folder
                    FROM checked_videos WHERE status='not_found'
                    ORDER BY checked_at DESC LIMIT ?
                """, (int(limit),)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка чтения нераспознанных записей: {exc}') from exc

    def delete(self, filename, file_size):
        name_lower = (filename or '').lower().strip()
        try:
            size = int(file_size)
        except Exception:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM checked_videos "
                "WHERE filename_lower=? AND file_size=?",
                (name_lower, size))
            conn.commit()

    def all_records(self, limit=5000):
        try:
            with self._lock, self._connect() as conn:
                rows = conn.execute("""
                    SELECT filename, file_size, number, qr, marketplace,
                           status, elapsed, checked_at, source_folder
                    FROM checked_videos ORDER BY checked_at DESC LIMIT ?
                """, (int(limit),)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка чтения базы: {exc}') from exc

    def history_records(self, filename, file_size, limit=50):
        name_lower = (filename or '').lower().strip()
        try:
            size = int(file_size)
        except (TypeError, ValueError):
            return []
        try:
            with self._lock, self._connect() as conn:
                rows = conn.execute("""
                    SELECT id, number, qr, marketplace, status,
                           elapsed, checked_at, source_folder
                    FROM history WHERE filename_lower=? AND file_size=?
                    ORDER BY checked_at DESC LIMIT ?
                """, (name_lower, size, int(limit))).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка чтения истории: {exc}') from exc

    def marketplace_stats(self):
        result = {'marketplaces': {}, 'statuses': {}}
        try:
            with self._lock, self._connect() as conn:
                for row in conn.execute(
                        "SELECT marketplace, COUNT(*) FROM checked_videos "
                        "GROUP BY marketplace"):
                    result['marketplaces'][row[0] or '-'] = row[1]
                for row in conn.execute(
                        "SELECT status, COUNT(*) FROM checked_videos "
                        "GROUP BY status"):
                    result['statuses'][row[0] or 'unknown'] = row[1]
            return result
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка статистики базы: {exc}') from exc

    def get_applied_files(self):
        try:
            with self._lock, self._connect() as conn:
                rows = conn.execute("SELECT file_id FROM checked_videos").fetchall()
            return {r[0] for r in rows}
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка чтения кэша: {exc}') from exc

    def stats(self):
        try:
            with self._lock, self._connect() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM checked_videos").fetchone()[0]
                found = conn.execute(
                    "SELECT COUNT(*) FROM checked_videos "
                    "WHERE status='found'").fetchone()[0]
            return {'total': total, 'found': found}
        except sqlite3.Error as exc:
            raise DatabaseError(f'Ошибка статистики базы: {exc}') from exc

    def clear(self):
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM checked_videos")
            conn.commit()

    def clear_history(self):
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM history")
            conn.commit()

    def export_csv(self, csv_path):
        records = self.all_records(limit=1000000)
        if not records:
            return 0
        df = pd.DataFrame(records)
        for column in df.select_dtypes(include=['object']).columns:
            df[column] = df[column].map(_safe_spreadsheet_text)
        folder = os.path.dirname(os.path.abspath(csv_path))
        os.makedirs(folder, exist_ok=True)
        tmp = csv_path + '.tmp'
        try:
            df.to_csv(tmp, index=False, encoding='utf-8-sig')
            os.replace(tmp, csv_path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        return len(records)


# ================= OCR-УТИЛИТЫ =================

def _normalize_text(text):
    text = text.replace('O', '0').replace('o', '0')
    text = text.replace('l', '1').replace('I', '1').replace('|', '1')
    text = text.replace('S', '5').replace('s', '5')
    text = text.replace('B', '8').replace('b', '6')
    text = text.replace('Z', '2').replace('z', '2')
    text = text.replace('_', '-').replace('—', '-').replace('–', '-').replace('~', '-')
    text = text.replace('\t', ' ').replace('\n', ' ')
    return re.sub(r' {2,}', ' ', text)


def _extract_all(text):
    if not text:
        return None
    clean = _normalize_text(text)

    m = P_OZON_OLD.search(clean)
    if m:
        num = re.sub(r'[^\d-]', '', m.group(0))
        if len(num) >= 12:
            return num

    m = P_OZON_NEW_SOFT.search(clean)
    if m:
        return re.sub(r'\s+', '', m.group(0))

    m = P_YANDEX_CARGO_SOFT.search(clean)
    if m:
        return re.sub(r'\s+', '', m.group(0))

    m = P_OZON_OLD_SOFT.search(clean)
    if m:
        num = re.sub(r'[^\d-]', '', m.group(0))
        if len(num) >= 15:
            return num

    return None


def _run_with_timeout(func, args=(), timeout=20):
    try:
        return True, func(*args, timeout=timeout)
    except TimeoutError:
        return False, None


def _resize_to_max(frame, max_w):
    h, w = frame.shape[:2]
    if w > max_w:
        s = max_w / w
        frame = cv2.resize(frame, (int(w * s), int(h * s)),
                           interpolation=cv2.INTER_AREA)
    return frame


def _prep_clahe(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _prep_otsu(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def _prep_adaptive(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 31, 2)


def _qr_angle_from_points(points):
    try:
        pts = np.array(points, dtype=np.float32).reshape(-1, 2)
        if len(pts) < 2:
            return 0.0
        (x1, y1), (x2, y2) = pts[0], pts[1]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90
        return float(angle)
    except Exception:
        return 0.0


def _rotate_image(image, angle):
    if abs(angle) < 0.5:
        return image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += new_w / 2 - center[0]
    M[1, 2] += new_h / 2 - center[1]
    return cv2.warpAffine(image, M, (new_w, new_h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _stack_frames(frames):
    if len(frames) < 2:
        return frames[0] if frames else None
    try:
        h_min = min(f.shape[0] for f in frames)
        w_min = min(f.shape[1] for f in frames)
        crops = [f[:h_min, :w_min].astype(np.float32) for f in frames]
        stacked = np.mean(crops, axis=0).astype(np.uint8)
        return stacked
    except Exception:
        return frames[0]


def crop_below_qr(frame, qr_points):
    if qr_points is None:
        return None
    try:
        pts = np.array(qr_points, dtype=np.float32).reshape(-1, 2)
    except Exception:
        return None
    h, w = frame.shape[:2]
    x_min = int(max(0, pts[:, 0].min()))
    x_max = int(min(w, pts[:, 0].max()))
    y_min = int(max(0, pts[:, 1].min()))
    y_max = int(min(h, pts[:, 1].max()))
    qr_h = y_max - y_min
    qr_w = x_max - x_min
    if qr_h < 20 or qr_w < 20:
        return None
    pad_x = int(qr_w * 0.20)
    x1 = max(0, x_min - pad_x)
    x2 = min(w, x_max + pad_x)
    y1 = min(h, y_max + int(qr_h * 0.05))
    y2 = min(h, y_max + int(qr_h * 1.6))
    if x2 - x1 < 40 or y2 - y1 < 20:
        return None
    return frame[y1:y2, x1:x2]


def crop_white_labels(frame):
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    total = h * w
    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < total * 0.03:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if 0.3 < cw / max(ch, 1) < 4.0:
            boxes.append((x, y, cw, ch))
    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    crops = []
    for (x, y, cw, ch) in boxes[:2]:
        pad = int(min(cw, ch) * 0.03)
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(w, x + cw + pad), min(h, y + ch + pad)
        crops.append(frame[y1:y2, x1:x2])
    return crops


# ================= ДВИЖОК =================

class ScannerEngine:
    def __init__(self, config, files=None, skip_resume=False,
                 on_log=None, on_file_done=None,
                 on_progress=None, on_finished=None):
        self.cfg = apply_performance_mode(dict(config))
        self.files_override = files
        self.skip_resume = bool(skip_resume)
        self.on_log = on_log or (lambda m: None)
        self.on_file_done = on_file_done or (lambda r: None)
        self.on_progress = on_progress or (lambda d, t, e: None)
        self.on_finished = on_finished or (lambda s: None)

        self.stop_flag = threading.Event()
        self.reader = None
        self.easyocr_worker = None
        self._executor = None
        self.easyocr_semaphore = threading.Semaphore(
            max(1, self.cfg.get('easyocr_concurrency', 1)))
        self.qr_detector = cv2.QRCodeDetector()
        self.qr_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.done_count = 0
        self.total_count = 0
        self.t_start = 0.0
        self._thread = None
        self._results = []
        self._easyocr_needed = (
            self.cfg.get('performance_mode_effective') == 'full')

        data_dir = self.cfg.get('data_dir') or _default_data_dir()
        _ensure_dir(data_dir)
        self.data_dir = data_dir

        tess_cmd = _resource_path(os.path.join("tesseract", "tesseract.exe"))
        if not os.path.isfile(tess_cmd):
            tess_cmd = os.path.join(_app_dir(), "tesseract", "tesseract.exe")
        if not os.path.isfile(tess_cmd):
            tess_cmd = self.cfg.get('tesseract_cmd') or \
                r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

        vf = self.cfg.get('video_folder', 'videos')
        if not os.path.isabs(vf):
            vf = os.path.join(data_dir, vf)
        self.cfg['video_folder'] = vf

        oe = self.cfg.get('output_excel', 'ozon_numbers.xlsx')
        if not os.path.isabs(oe):
            oe = os.path.join(data_dir, oe)
        self.cfg['output_excel'] = oe

        db = self.cfg.get('db_path', 'checked_videos.db')
        if not os.path.isabs(db):
            db = os.path.join(data_dir, db)
        self.cfg['db_path'] = db

        dd = self.cfg.get('debug_dir', 'debug')
        if not os.path.isabs(dd):
            dd = os.path.join(data_dir, dd)
        self.cfg['debug_dir'] = dd

        _ensure_dir(self.cfg['debug_dir'])
        self.cache = VideoCache(self.cfg['db_path'])

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self.stop_flag.clear()
        self.done_count = 0
        self._results = []
        self.t_start = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self.stop_flag.set()
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
        if self.easyocr_worker is not None:
            self.easyocr_worker.cancel()

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def _log(self, msg):
        try:
            self.on_log(msg)
        except Exception:
            pass

    def _run(self):
        if self._easyocr_needed:
            try:
                self._log("Загрузка нейросети EasyOCR...")
                easyocr_dir = _resource_path("easyocr_models")
                if not os.path.isdir(easyocr_dir):
                    easyocr_dir = os.path.join(_app_dir(), "easyocr_models")
                if not os.path.isdir(easyocr_dir):
                    raise RuntimeError(
                        f"Не найдена папка с моделями: {easyocr_dir}")
                self.easyocr_worker = EasyOCRWorker(
                    easyocr_dir, self.stop_flag)
                self.reader = True
                self._log("EasyOCR готов к запуску в изолированном процессе.")
            except Exception as e:
                self._log(f"EasyOCR недоступен: {e}")
                self._easyocr_needed = False
        else:
            self._log(f"Режим: "
                      f"{self.cfg.get('performance_mode_effective', 'fast')} "
                      f"(EasyOCR отключён)")

        folder = self.cfg['video_folder']
        if self.files_override is not None:
            files = sorted([f for f in self.files_override
                            if f.lower().endswith(VIDEO_EXTS)])
        else:
            files = list_videos(folder)

        if not files:
            self._log("Нет файлов для обработки.")
            if self.easyocr_worker is not None:
                self.easyocr_worker.close()
            self.on_finished({'error': None, 'results': [],
                              'elapsed': 0, 'cancelled': False})
            return

        # Возобновление очереди (только для обычного запуска)
        if self.cfg.get('resume', True) and not self.skip_resume:
            try:
                existing = self.cache.find_existing(folder, files)
                existing_names = {name.lower().strip() for name, _ in existing}
                if existing_names:
                    before = len(files)
                    files = [f for f in files
                             if f.lower().strip() not in existing_names]
                    skipped = before - len(files)
                    if skipped > 0:
                        self._log(f"Возобновление: пропущено "
                                  f"{skipped} уже проверенных")
            except DatabaseError as exc:
                self._log(f"Ошибка чтения кэша: {exc}. "
                          "Возобновление отключено для этого запуска.")
        elif self.skip_resume:
            self._log("Перепроверка: resume отключён, "
                      "сканирую все переданные файлы")

        if not files:
            self._log("Все файлы уже проверены (возобновление).")
            if self.easyocr_worker is not None:
                self.easyocr_worker.close()
            self.on_finished({'error': None, 'results': [],
                              'elapsed': 0, 'cancelled': False})
            return

        self.total_count = len(files)
        self._log(f"К обработке: {self.total_count} файл(ов)")
        self._log("")

        workers = max(1, min(self.cfg['worker_threads'], self.total_count))
        self._log(f"Запуск пула из {workers} потоков.")

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                self._executor = executor
                futures = {
                    executor.submit(self._process_video,
                                    os.path.join(folder, f), f, i): f
                    for i, f in enumerate(files)
                }
                for fut in as_completed(futures):
                    if self.stop_flag.is_set():
                        for f2 in futures:
                            f2.cancel()
                        break
                    try:
                        res = fut.result()
                    except Exception as e:
                        fname = futures[fut]
                        self._log(f"Ошибка на {fname}: {e}")
                        res = {
                            'Название файла': fname,
                            'Внутренний номер': 'Ошибка',
                            'Маркетплейс': '-',
                            'QR-код': '-',
                            'Время (с)': 0.0,
                            'Статус': 'error',
                            'Источник': 'ошибка',
                            'Дата и время создания': '-',
                        }
                    self._results.append(res)
                    with self.progress_lock:
                        self.done_count += 1
                        done = self.done_count
                    self.on_file_done(res)
                    self.on_progress(done, self.total_count,
                                     time.perf_counter() - self.t_start)
        except Exception as e:
            self._log(f"Критическая ошибка пула: {e}")

        self._executor = None
        if self.easyocr_worker is not None:
            self.easyocr_worker.close()
        self._save_excel()
        elapsed = time.perf_counter() - self.t_start
        cancelled = self.stop_flag.is_set()
        self._log("")
        self._log(f"{'ОСТАНОВЛЕНО' if cancelled else 'ГОТОВО'}. "
                  f"Обработано: {len(self._results)}/{self.total_count}. "
                  f"Время: {elapsed:.1f} с")
        self.on_finished({
            'error': None,
            'results': sorted(self._results,
                              key=lambda r: r['Название файла']),
            'elapsed': elapsed,
            'cancelled': cancelled,
        })

    def _is_in_applied(self, filename, applied, folder):
        fp = os.path.join(folder, filename)
        try:
            sz = int(os.path.getsize(fp))
        except Exception:
            return False
        return (filename.lower().strip(), sz) in applied

    def _save_excel(self):
        try:
            records = self.cache.all_records(limit=100000)
            if not records:
                return

            rows = []
            for rec in records:
                checked_at = rec.get('checked_at', '') or ''
                date_str = '-'
                if checked_at:
                    try:
                        dt = datetime.fromisoformat(checked_at)
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        date_str = checked_at

                rows.append({
                    'Название файла': rec.get('filename', ''),
                    'Внутренний номер': rec.get('number') or 'Не найдено',
                    'Маркетплейс': rec.get('marketplace') or '-',
                    'QR-код': rec.get('qr') or '-',
                    'Время (с)': rec.get('elapsed') or 0.0,
                    'Статус': rec.get('status') or 'not_found',
                    'Дата проверки': date_str,
                })

            df = pd.DataFrame(rows)
            for column in df.select_dtypes(include=['object']).columns:
                df[column] = df[column].map(_safe_spreadsheet_text)
            output_path = self.cfg['output_excel']
            _ensure_dir(os.path.dirname(output_path))
            tmp_path = output_path + '.tmp.xlsx'
            try:
                df.to_excel(tmp_path, index=False)
                os.replace(tmp_path, output_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            self._log(f"Результаты сохранены ({len(rows)} записей): "
                      f"{output_path}")
        except Exception as e:
            self._log(f"Не удалось сохранить Excel: {e}")

    def _process_video(self, filepath, filename, thread_id):
        prefix = f"[{thread_id:>2}]"
        t_start = time.perf_counter()

        try:
            identity_before = _file_identity(filepath)
            file_size = identity_before['size']
        except OSError as exc:
            self._log(f"{prefix}   файл недоступен: {exc}")
            return self._make_result(filename, filepath, 0,
                                     None, '-', 0.0, 'error',
                                     'файл недоступен')

        self._log(f"{prefix} ▶ {filename}")

        try:
            frames = self._pick_sharp_frames(filepath)
        except Exception as e:
            self._log(f"{prefix}   ошибка отбора кадров: {e}")
            frames = []

        if not frames:
            self._log(f"{prefix}   ✗ не удалось прочитать видео")
            return self._make_result(filename, filepath, file_size,
                                     None, '-', 0.0, 'error', 'нет кадров')

        self._log(f"{prefix}   кадров к анализу: {len(frames)}")

        cap = cv2.VideoCapture(filepath)
        all_findings = []
        all_qr = []
        strict_counter = Counter()
        collected_frames = []

        for idx, fi in enumerate(frames):
            if self.stop_flag.is_set():
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ret, frame = cap.read()
            if not ret:
                continue
            frame = _resize_to_max(frame, self.cfg['max_width'])
            collected_frames.append(frame)

            try:
                qr_content, findings = self._fast_pass(frame, prefix)
                if qr_content:
                    all_qr.append(qr_content)
                if findings:
                    all_findings.extend(findings)
                    for f in findings:
                        if f[0] == 'strict':
                            strict_counter[f[1]] += 1
                    if strict_counter:
                        break
                if not strict_counter and not findings:
                    findings2 = self._full_pass(frame, prefix)
                    if findings2:
                        all_findings.extend(findings2)
                        for f in findings2:
                            if f[0] == 'strict':
                                strict_counter[f[1]] += 1
                        if strict_counter:
                            break
            except Exception as e:
                self._log(f"{prefix}   ошибка кадра {fi}: {e}")

        # Fallback 1: ротация
        if (not strict_counter) and self.cfg.get('enable_rotation', True) \
                and collected_frames:
            self._log(f"{prefix}   ротация кадров...")
            for angle in (90, -90, 180):
                for idx, fi in enumerate(frames):
                    if self.stop_flag.is_set() or strict_counter:
                        break
                    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    frame = _resize_to_max(frame, self.cfg['max_width'])
                    rotated = _rotate_image(frame, angle)
                    try:
                        qr_content, findings = self._fast_pass(
                            rotated, prefix)
                        if qr_content and qr_content not in all_qr:
                            all_qr.append(qr_content)
                        if findings:
                            all_findings.extend(findings)
                            for f in findings:
                                if f[0] == 'strict':
                                    strict_counter[f[1]] += 1
                            if strict_counter:
                                break
                    except Exception:
                        continue

        # Fallback 2: стек
        if (not strict_counter) and self.cfg.get('enable_stacking', True) \
                and len(collected_frames) >= 2:
            self._log(f"{prefix}   стек {len(collected_frames)} кадров...")
            try:
                stacked = _stack_frames(collected_frames[:4])
                if stacked is not None:
                    qr_content, findings = self._fast_pass(stacked, prefix)
                    if qr_content and qr_content not in all_qr:
                        all_qr.append(qr_content)
                    if findings:
                        all_findings.extend(findings)
                        for f in findings:
                            if f[0] == 'strict':
                                strict_counter[f[1]] += 1
                    if not strict_counter:
                        findings2 = self._full_pass(stacked, prefix)
                        if findings2:
                            all_findings.extend(findings2)
                            for f in findings2:
                                if f[0] == 'strict':
                                    strict_counter[f[1]] += 1
            except Exception as e:
                self._log(f"{prefix}   стек упал: {e}")

        cap.release()

        best_number, reason = self._select_best(all_findings)
        elapsed = time.perf_counter() - t_start
        qr_final = Counter(all_qr).most_common(1)[0][0] if all_qr else '-'

        if best_number:
            self._log(f"{prefix}   ✓ {best_number} ({reason}, "
                      f"{elapsed:.1f} с)")
            status = 'found'
        else:
            self._log(f"{prefix}   ✗ не найдено ({elapsed:.1f} с)")
            status = 'not_found'

        result = self._make_result(filename, filepath, file_size,
                                   best_number, qr_final, elapsed,
                                   status, 'проверено')

        if status in ('found', 'not_found'):
            try:
                identity_after = _file_identity(filepath)
                if identity_after['file_id'] != identity_before['file_id']:
                    self._log(f"{prefix}   файл изменился во время проверки; "
                              "результат не добавлен в кэш")
                else:
                    source_folder = os.path.dirname(os.path.abspath(filepath))
                    self.cache.put(
                        filename, file_size,
                        result['Внутренний номер'], result['QR-код'],
                        result['Маркетплейс'], status, elapsed,
                        source_folder=source_folder,
                        identity=identity_after)
            except (OSError, DatabaseError) as e:
                self._log(f"{prefix}   ошибка кэша: {e}")

        return result

    def _extract_number_from_qr(self, qr_data):
        if not qr_data:
            return None
        text = str(qr_data).strip()

        if P_OZON_NEW.match(text):
            return text
        if P_YANDEX_CARGO.match(text):
            return text
        if P_YANDEX_ORDER.match(text):
            return text
        return None

    def _decode_qr_any(self, frame):
        try:
            with self.qr_lock:
                data, points, _ = self.qr_detector.detectAndDecode(frame)
            if data:
                return data, points
        except Exception:
            pass

        if HAS_PYZBAR:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                decoded = pyzbar_decode(gray)
                if decoded:
                    item = decoded[0]
                    data = item.data.decode('utf-8', errors='ignore')
                    rect = item.rect
                    x, y, w, h = rect.left, rect.top, rect.width, rect.height
                    points = [[[x, y], [x+w, y], [x+w, y+h], [x, y+h]]]
                    return data, points
            except Exception:
                pass

        return None, None

    def _fast_pass(self, frame, prefix):
        findings = []
        qr_content = None

        qr_data, qr_points = self._decode_qr_any(frame)

        if qr_data and qr_points is not None \
                and self.cfg.get('enable_qr_align', True):
            angle = _qr_angle_from_points(qr_points)
            if abs(angle) > 3:
                self._log(f"{prefix}   QR наклон {angle:.1f}° — выравниваю")
                frame = _rotate_image(frame, -angle)
                qr_data, qr_points = self._decode_qr_any(frame)

        if qr_data:
            qr_content = qr_data
            self._log(f"{prefix}   🔲 QR: {qr_data}")

            qr_number = self._extract_number_from_qr(qr_data)
            if qr_number:
                mp = detect_marketplace(qr_number)
                self._log(f"{prefix}   ✓ Номер из QR: "
                          f"{qr_number} [{mp}]")
                return qr_content, [('strict', qr_number, 1.0, 'QR')]
            else:
                self._log(f"{prefix}   QR не совпал с форматами — OCR")

        crops = []
        if qr_points is not None:
            c = crop_below_qr(frame, qr_points)
            if c is not None and c.size > 0:
                crops.append(('под_QR', c))

        try:
            whites = crop_white_labels(frame)
            for i, wc in enumerate(whites[:1]):
                crops.append((f'белая_зона_{i+1}', wc))
        except Exception:
            pass

        for tag, crop in crops:
            for prep_name, prep_func, psm in [
                ('otsu', _prep_otsu, 6),
                ('clahe', _prep_clahe, 6),
                ('adapt', _prep_adaptive, 11),
            ]:
                try:
                    img = prep_func(crop)
                    txt = self._tess_call(img, psm, timeout=8)
                    if not txt:
                        continue
                    num = _extract_all(txt)
                    if num:
                        mp = detect_marketplace(num)
                        self._log(f"{prefix}   ✓ "
                                  f"Tesseract[{tag}/{prep_name}]: "
                                  f"{num} [{mp}]")
                        findings.append(('strict', num, 1.0,
                                         f'C_fast_{tag}_{prep_name}'))
                        return qr_content, findings
                except Exception:
                    continue

        return qr_content, findings

    def _full_pass(self, frame, prefix):
        findings = []
        enabled = self.cfg['enabled_methods']

        for key, name, _, m_type, timeout in ALL_METHODS:
            if m_type != 'tess':
                continue
            if not enabled.get(key, True):
                continue
            try:
                if key == 'C1_otsu':
                    img, psm = _prep_otsu(frame), 6
                elif key == 'C2_clahe':
                    img, psm = _prep_clahe(frame), 6
                elif key == 'C3_adapt':
                    img, psm = _prep_adaptive(frame), 11
                else:
                    img, psm = _prep_otsu(frame), 6
                txt = self._tess_call(img, psm, timeout=timeout)
                if not txt:
                    continue
                num = _extract_all(txt)
                if num:
                    mp = detect_marketplace(num)
                    self._log(f"{prefix}   ✓ {name}: {num} [{mp}]")
                    return [('strict', num, 1.0, key)]
            except Exception:
                continue

        if self._easyocr_needed and self.reader is not None:
            for key, name, _, m_type, timeout in ALL_METHODS:
                if m_type != 'easy':
                    continue
                if not enabled.get(key, True):
                    continue
                try:
                    txt, conf = self._easyocr_call(frame, timeout=timeout)
                    if not txt:
                        continue
                    num = _extract_all(txt)
                    if num:
                        self._log(f"{prefix}   ✓ {name}: "
                                  f"{num} ({conf:.0%})")
                        return [('strict', num, conf, key)]
                except Exception:
                    continue

        return findings

    def _make_result(self, filename, filepath, file_size, number, qr,
                     elapsed, status, source):
        return {
            'Название файла': filename,
            'Внутренний номер': number if number else 'Не найдено',
            'Маркетплейс': detect_marketplace(number) if number else '-',
            'QR-код': qr,
            'Время (с)': round(elapsed, 2),
            'Статус': status,
            'Источник': source,
            'Дата и время создания': self._safe_ctime(filepath),
        }

    def _safe_ctime(self, filepath):
        try:
            return datetime.fromtimestamp(
                os.path.getctime(filepath)
            ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return '-'

    def _tess_call(self, img, psm, timeout=8):
        try:
            return pytesseract.image_to_string(
                img, lang='rus+eng', config=f'--psm {psm} --oem 3',
                timeout=max(1, float(timeout)))
        except RuntimeError as exc:
            if 'timeout' in str(exc).lower():
                raise TimeoutError(str(exc)) from exc
            return ""
        except Exception:
            return ""

    def _easyocr_call(self, img, timeout=30):
        if self.easyocr_worker is None:
            return "", 0.0
        res = self.easyocr_worker.call(img, timeout)
        if not res:
            return "", 0.0
        texts, confs = [], []
        for item in res:
            if len(item) >= 3:
                texts.append(item[1])
                confs.append(float(item[2]))
        return " ".join(texts), (sum(confs) / len(confs) if confs else 0.0)

    def _select_best(self, all_findings):
        if not all_findings:
            return None, 'нет находок'
        strict = [f for f in all_findings if f[0] == 'strict']
        if not strict:
            return None, 'нет находок'
        cnt = Counter(f[1] for f in strict)
        top, n = cnt.most_common(1)[0]
        return top, f'СТРОГИЙ ({n})'

    def _pick_sharp_frames(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        end = min(total, int(fps * self.cfg['scan_seconds']))
        step = max(1, int(fps * 0.15))
        candidates = []
        for i in range(0, end, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
            candidates.append((sharp, i))
        cap.release()
        candidates.sort(reverse=True)
        count = self.cfg['frames_count']
        top = [i for s, i in candidates[:count]
               if s > self.cfg['sharpness_min']]
        if not top and candidates:
            top = [candidates[0][1]]
        return sorted(top)