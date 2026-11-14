#!/usr/bin/env python3
"""Generate the reel styles that Edits cannot draw, as full-canvas transparent overlays (1080x1920, 30 fps), written
as a .mov with alpha that Edits imports like any other insert. Style catalog: references/styles.md.

Usage:
  PY reelstyles.py <out.mov> --style adesivo --text "texto adesivo" --dur 2.0 [--x 0.5 --y 0.42] [--rot -4]
                   [--scale 1.0] [--size 150] [--codec prores|hevc]
  PY reelstyles.py <out.png> --style rabisco --text "saiba mais" --dur 2.0 --preview-t 1.2   (still for QA)

Styles: recorte-papel, adesivo, manchete, rabisco (word + hand scribble), parede-caracteres (full-canvas background,
put it on the `behind` layer), moldura-camera (focus brackets + REC + timecode in --text).
Place the file in <project>/media/styles/ (Edits only imports from under ~/Movies). Output starts at the overlay's
own t=0; the EDL's `at` is where it appears in the timeline.
"""
import math
import os
import random
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layerkit  # noqa: E402
import skillenv  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

W, H, FPS = 1080, 1920, 30
PAPER, INK, BUTTER, WHITE = (245, 240, 230, 255), (17, 17, 17, 255), (250, 230, 122, 255), (255, 255, 255, 255)
HEAVY = ['/System/Library/Fonts/Supplemental/Arial Black.ttf', '/Library/Fonts/Arial Black.ttf',
         '/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf']
MONO = ['/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Supplemental/Courier New.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf']
DEFAULT_SIZE = {'recorte-papel': 150, 'adesivo': 120, 'manchete': 150, 'rabisco': 130, 'parede-caracteres': 30,
                'moldura-camera': 44}
STYLES = tuple(DEFAULT_SIZE)


def font(candidates, size):
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit(f'No font found for {candidates[0]}. Install Arial Black or edit HEAVY/MONO in reelstyles.py.')


def ease_out_back(p):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2


def envelope(t, dur, pop_in=0.18, fade=0.15):
    """-> (scale, alpha) for a pop-in with overshoot at the start and a short fade at the end."""
    p = min(1.0, max(0.0, t / pop_in))
    scale = 1.3 - 0.3 * ease_out_back(p)
    alpha = min(1.0, max(0.0, (dur - t) / fade))
    return scale, alpha


def scale_alpha(img, scale, alpha):
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    if alpha < 1:
        a = img.getchannel('A').point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    return img


def place(canvas, img, x, y):
    """alpha-composite img with its top-left at (x, y), clipped to the canvas."""
    x, y = int(round(x)), int(round(y))
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    img = img.crop((sx, sy, min(img.width, W - dx + sx), min(img.height, H - dy + sy)))
    if img.width > 0 and img.height > 0:
        canvas.alpha_composite(img, (dx, dy))


def shadow_of(img, blur=18, off=(0, 16), strength=0.45):
    """img with a soft drop shadow. The blur runs on a canvas padded past the shadow, so it never gets clipped."""
    pad = blur * 3
    out = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel('A').point(lambda v: int(v * strength))
    sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 255), (pad + off[0], pad + off[1], pad + off[0] + img.width, pad + off[1] + img.height), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(img, (pad, pad))
    return out


def text_box(txt, fnt, pad_x, pad_y):
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, t, r, b = probe.textbbox((0, 0), txt, font=fnt)
    w, h = r - l + 2 * pad_x, b - t + 2 * pad_y
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    return img, (l, t, pad_x, pad_y)


def draw_text(img, txt, fnt, color, offset):
    l, t, pad_x, pad_y = offset
    ImageDraw.Draw(img).text((pad_x - l, pad_y - t), txt, font=fnt, fill=color)


def fit_size(txt, size, pad_x, max_w=int(W * 0.86)):
    """Shrink the font until the text plus padding fits the canvas width (a long line must never be cut off)."""
    while size > 40:
        tb, _ = text_box(txt, font(HEAVY, size), pad_x, 0)
        if tb.width <= max_w:
            break
        size -= 6
    return size


def paper_card(txt, size, fill, ink, rot, radius=22, pad=(46, 30)):
    size = fit_size(txt, size, pad[0])
    fnt = font(HEAVY, size)
    tb, off = text_box(txt, fnt, *pad)
    card = Image.new('RGBA', tb.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=radius, fill=fill)
    draw_text(card, txt, fnt, ink, off)
    return card.rotate(rot, resample=Image.BICUBIC, expand=True)


def frame_recorte(t, dur, a):
    s, al = envelope(t, dur)
    card = paper_card(a['text'], a['size'], PAPER, INK, a['rot'])
    return scale_alpha(shadow_of(card), s, al)


def frame_adesivo(t, dur, a):
    s, al = envelope(t, dur)
    card = paper_card(a['text'], a['size'], BUTTER, INK, a['rot'], radius=14, pad=(40, 26))
    tape = Image.new('RGBA', (150, 46), (0, 0, 0, 0))
    ImageDraw.Draw(tape).rectangle((0, 0, 149, 45), fill=(255, 255, 255, 150))
    tape = tape.rotate(-30, expand=True, resample=Image.BICUBIC)
    card.alpha_composite(tape, (-12, -10))
    card.alpha_composite(tape.rotate(60, expand=True), (card.width - 90, card.height - 40))
    return scale_alpha(shadow_of(card, blur=10, strength=0.35), s, al)


def frame_manchete(t, dur, a):
    s, al = envelope(t, dur, pop_in=0.12)
    size = fit_size(a['text'].upper(), a['size'], 40)
    fnt = font(HEAVY, size)
    tb, off = text_box(a['text'].upper(), fnt, 40, 24)
    card = Image.new('RGBA', (tb.width + 16, tb.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(card).rectangle((0, 0, card.width - 1, card.height - 1), fill=INK)
    inner = Image.new('RGBA', (card.width - 16, card.height - 16), WHITE)
    card.alpha_composite(inner, (8, 8))
    draw_text(card, a['text'].upper(), fnt, INK, (off[0] - 8, off[1] - 8, off[2], off[3]))
    return scale_alpha(shadow_of(card.rotate(a['rot'], resample=Image.BICUBIC, expand=True), strength=0.35), s, al)


def frame_rabisco(t, dur, a):
    size = fit_size(a['text'], a['size'], 60, max_w=int(W * 0.78))
    fnt = font(HEAVY, size)
    tb, off = text_box(a['text'], fnt, 0, 0)
    bw, bh = tb.width, tb.height
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    cx, cy = a['x'] * W, a['y'] * H
    rx, ry = bw / 2 + 60, bh / 2 + 46
    rng = random.Random(7)
    pts = []
    steps = 90
    for i in range(steps + 9):   # one turn plus an overlap, wobbled a little like a hand
        th = 2 * math.pi * i / steps - 0.6
        wob = 1 + 0.03 * rng.uniform(-1, 1)
        pts.append((cx + rx * wob * math.cos(th), cy + ry * wob * math.sin(th)))
    p = min(1.0, t / max(0.2, dur * 0.45))
    n = max(2, int(len(pts) * ease_out_back(p) if p < 1 else len(pts)))
    n = min(n, len(pts))
    d = ImageDraw.Draw(layer)
    d.line(pts[:n], fill=BUTTER, width=16, joint='curve')
    s, al = envelope(t, dur, pop_in=0.2)
    word = Image.new('RGBA', tb.size, (0, 0, 0, 0))
    draw_text(word, a['text'], fnt, WHITE, off)
    word = scale_alpha(shadow_of(word), s, 1.0)
    place(layer, word, cx - word.width / 2, cy - word.height / 2)
    return scale_alpha(layer, 1.0, al)


def frame_parede(t, dur, a):
    fnt = font(MONO, a['size'])
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = a['size'] + 6
    pool = '01<>/{}#%&*+=ABCDEF'
    cols = W // step + 1
    rows = H // step + 2
    for c in range(cols):
        rng = random.Random(c * 991 + 17)
        speed = 90 + rng.uniform(0, 160)           # px per second
        offset = rng.uniform(0, H)
        y0 = (offset + speed * t) % (H + step * 6) - step * 6
        for r in range(rows + 6):
            y = y0 + r * step
            if y > H or y < -step:
                continue
            ch = pool[(c * 31 + r * 17 + int(t * 6)) % len(pool)]
            fade = 1 - abs((y / H) - 0.5) * 0.5
            d.text((c * step, y), ch, font=fnt, fill=(250, 230, 122, int(70 * fade)))
    s, al = envelope(t, dur, pop_in=0.4, fade=0.3)
    return scale_alpha(layer, 1.0, al * min(1.0, 0.9 + 0.1 * s))


def frame_moldura(t, dur, a):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    inset, leg, wdt = 70, 110, 7
    col = (255, 255, 255, 235)
    for x, y, sx, sy in [(inset, inset, 1, 1), (W - inset, inset, -1, 1), (inset, H - inset, 1, -1),
                         (W - inset, H - inset, -1, -1)]:
        d.line([(x, y), (x + sx * leg, y)], fill=col, width=wdt)
        d.line([(x, y), (x, y + sy * leg)], fill=col, width=wdt)
    blink_on = int(t * 2) % 2 == 0
    if blink_on:
        d.ellipse((inset + 10, inset + 90, inset + 40, inset + 120), fill=(255, 59, 48, 255))
    fnt = font(MONO, a['size'])
    d.text((inset + 60, inset + 92), 'REC', font=fnt, fill=(255, 255, 255, 240))
    d.text((W - inset - 60, H - inset - 60), a['text'], font=fnt, fill=(255, 255, 255, 240), anchor='rs')
    s, al = envelope(t, dur, pop_in=0.1, fade=0.1)
    return scale_alpha(layer, 1.0, al)


FRAMES = {'recorte-papel': frame_recorte, 'adesivo': frame_adesivo, 'manchete': frame_manchete,
          'rabisco': frame_rabisco, 'parede-caracteres': frame_parede, 'moldura-camera': frame_moldura}
CENTRED = {'recorte-papel', 'adesivo', 'manchete', 'rabisco'}


def compose(style, t, dur, a):
    """One full-canvas RGBA frame of `style` at time t. Cards go where x, y put them; backgrounds ignore them."""
    frame = FRAMES[style](t, dur, a)
    if style in CENTRED:
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        if style == 'rabisco':
            return frame
        place(canvas, frame, a['x'] * W - frame.width / 2, a['y'] * H - frame.height / 2)
        return canvas
    return frame


def main():
    skillenv.utf8_stdio()
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    out = skillenv.path_arg(a[0])
    opt = {'text': '', 'dur': 2.0, 'x': 0.5, 'y': 0.42, 'rot': 0.0, 'scale': 1.0, 'size': None, 'codec': 'prores',
           'style': None, 'preview-t': None}
    i = 1
    while i < len(a):
        k = a[i].lstrip('-')
        if k not in opt:
            sys.exit(f'unknown option {a[i]}')
        opt[k] = a[i + 1]
        i += 2
    style = opt['style']
    if style not in STYLES:
        sys.exit(f'--style must be one of {", ".join(STYLES)}')
    args = {'text': opt['text'], 'x': float(opt['x']), 'y': float(opt['y']), 'rot': float(opt['rot']),
            'size': int(opt['size'] or DEFAULT_SIZE[style])}
    dur = float(opt['dur'])
    if opt['preview-t'] is not None:
        frame = compose(style, float(opt['preview-t']), dur, args)
        frame.save(out)
        print(f'{out} (still at {opt["preview-t"]} s)')
        return
    layerkit.check_codec(opt['codec'])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    n = int(round(dur * FPS))
    tmp = out + '.part.mov'
    cmd = [skillenv.tool('ffmpeg'), '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', *layerkit.alpha_args(opt['codec']), '-r', str(FPS), tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(compose(style, f / FPS, dur, args).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        sys.exit('ffmpeg failed while writing the overlay')
    os.replace(tmp, out)
    print(f'{out}  {style}  {n} frames @ {FPS} fps  alpha {layerkit.has_alpha(out)}')


if __name__ == '__main__':
    main()
