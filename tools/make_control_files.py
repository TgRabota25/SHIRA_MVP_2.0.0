"""Генерация синтетических контрольных файлов для проверок SHIRA MVP.

ВНИМАНИЕ: это ИСКУССТВЕННЫЕ фикстуры, а не реальные заказы.
Они нужны, чтобы автоматические тесты могли запускаться без зависимостей
от внешних материалов. Точность на реальных съёмках имитацией не证明.

Генерируются:
- control_text.png — надпись трека 81604409-0321-5 (проверка OCR).
- control_qr.png — QR-код ii12345678901 (проверка QR).
- control_qr_near_text.png — служебный QR без трека + трек рядом (QR-якорный OCR).
- control_rotated_label.png — та же этикетка, поворот на 90°.
- control_multi_label.avi — 6 сек видео: интервал 0-3 с QR ii12345678901,
  интервал 3-6 с QR ii99999999999 (проверка длинного режима и интервалов).
- control_9h_sparse.avi — искусственный контейнер длительностью 9 ч
  (один кадр в час), только для проверки таймкодов.
"""

import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import zxingcpp

OUT = Path(__file__).resolve().parents[1] / 'examples'


def font(size=40):
    for candidate in [
        'arial.ttf', 'segoeui.ttf', 'DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/Windows/Fonts/arial.ttf',
    ]:
        p = Path(candidate)
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def write_png(path, pil_image):
    pil_image.save(path, format='PNG')


def control_text():
    im = Image.new('RGB', (900, 300), 'white')
    d = ImageDraw.Draw(im)
    f = font(56)
    text = 'Трек: 81604409-0321-5'
    bbox = d.textbbox((0, 0), text, font=f)
    d.text(((900 - (bbox[2] - bbox[0])) / 2, (300 - (bbox[3] - bbox[1])) / 2), text, font=f, fill='black')
    write_png(OUT / 'control_text.png', im)


def qr_image(content, size_px=460):
    b = zxingcpp.create_barcode(content, zxingcpp.QRCode)
    img = zxingcpp.write_barcode_to_image(b, scale=max(1, int(round(size_px / 116))))
    arr = np.array(img)
    pil = Image.fromarray(arr).convert('L').convert('RGB')
    return pil.resize((size_px, size_px), Image.LANCZOS)


def control_qr(content):
    write_png(OUT / 'control_qr.png', qr_image(content, 460))


def control_qr_near_text():
    # Служебный QR без трека.
    qr = qr_image('SERV-0001', 300)
    canvas = Image.new('RGB', (1000, 500), 'white')
    d = ImageDraw.Draw(canvas)
    canvas.paste(qr, (40, 100))
    f = font(40)
    d.text((380, 170), 'Трек: 81604409-0321-5', font=f, fill='black')
    write_png(OUT / 'control_qr_near_text.png', canvas)


def control_rotated_label():
    src = Image.open(OUT / 'control_text.png').convert('RGB')
    im = src.rotate(-90, expand=True, resample=Image.BICUBIC)
    write_png(OUT / 'control_rotated_label.png', im)


def qr_frame(content, size=(320, 240)):
    qr = qr_image(content, 120)
    canvas = Image.new('RGB', size, 'white')
    canvas.paste(qr, ((size[0] - qr.width) // 2, (size[1] - qr.height) // 2))
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)


def white_frame(size=(160, 120)):
    return np.full((size[1], size[0], 3), 255, dtype=np.uint8)


def control_multi_label():
    fps = 25.0
    seconds = 6
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(str(OUT / 'control_multi_label.avi'), fourcc, fps, (320, 240))
    total = int(round(seconds * fps))
    for i in range(total):
        content = 'ii12345678901' if i < total // 2 else 'ii99999999999'
        out.write(qr_frame(content))
    out.release()


def control_9h_sparse():
    """Искусственный 9-часовой контейнер: один кадр в час, 32400 кадров @ 1 fps.
    duration = 32400 с. Реальные ключевые кадры позволяют OpenCV делать seek на
    любые таймкоды без 9-часовых данных на диске."""
    path = OUT / 'control_9h_sparse.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(str(path), fourcc, 1.0, (160, 120))
    assert out.isOpened(), 'не удалось открыть VideoWriter'
    for frame_no in range(32400):  # 9 часов × 3600 секунд, 1 кадр/с
        frame = white_frame((160, 120))
        if frame_no % 3600 == 0:
            frame[10:20, 10:20] = 0  # метка часа
        out.write(frame)
    out.release()
    cap = cv2.VideoCapture(str(path))
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT); fpsr = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if count <= 0 or fpsr <= 0 or abs(count / fpsr - 32400) > 1:
        raise RuntimeError(f'9h контейнер не удался: count={count} fps={fpsr}')
    print('wrote', path, int(count), 'frames,', count / fpsr, 'seconds')


def main():
    os.makedirs(OUT, exist_ok=True)
    control_text()
    control_qr('ii12345678901')
    control_qr_near_text()
    control_rotated_label()
    control_multi_label()
    control_9h_sparse()
    print('контрольные файлы созданы в', OUT)


if __name__ == '__main__':
    main()
