import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'app' / 'icon.png'
THRESH = 38


def strip_white(im):
    im = im.convert('RGBA')
    w, h = im.size
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        r, g, b, a = im.getpixel(corner)
        if a > 0 and min(r, g, b) > 200:
            ImageDraw.floodfill(im, corner, (255, 255, 255, 0), thresh=THRESH)
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if 0 < a and min(r, g, b) > 235:
                near = any(
                    0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] == 0
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                )
                if near:
                    px[x, y] = (r, g, b, 0)
    return im


def square(im, size):
    box = im.getbbox()
    if box:
        im = im.crop(box)
    side = max(im.size)
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


if __name__ == '__main__':
    base = strip_white(Image.open(SRC))
    big = square(base, 512)
    big.save(ROOT / 'app' / 'icon.png')
    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    square(base, 256).save(ROOT / 'app' / 'icon.ico', format='ICO', sizes=sizes)
    print('OK: app/icon.png (512, RGBA) and app/icon.ico', [s[0] for s in sizes])
