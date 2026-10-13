"""Картинки: простой растровый рендер (painter's algorithm), без OpenGL."""
import os
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont


def _font(*paths):
    return next((p for p in paths if os.path.exists(p)), paths[-1])


FONT_B = _font('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
FONT = _font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf')
GREY = (205, 205, 205)
_tess = {}       # id(тела) -> (тело, треугольники); тело держим, иначе его id достанется другому


def tris(solid):
    key = id(solid)
    if key not in _tess or _tess[key][0] is not solid:
        out = []
        for f in solid.faces():
            vs, ts = f.tessellate(0.8)
            P = np.array([[p.X, p.Y, p.Z] for p in vs])
            out += [P[list(t)] for t in ts]
        res = []
        while out:                       # мелкие треугольники — корректная сортировка по глубине
            t = out.pop()
            e = [np.linalg.norm(t[i] - t[(i + 1) % 3]) for i in range(3)]
            if max(e) > 400:
                m = [(t[i] + t[(i + 1) % 3]) / 2 for i in range(3)]
                out += [np.array([t[0], m[0], m[2]]), np.array([m[0], t[1], m[1]]),
                        np.array([m[2], m[1], t[2]]), np.array(m)]
            else:
                res.append(t)
        _tess[key] = (solid, np.array(res) if res else np.zeros((0, 3, 3)))
    return _tess[key][1]


def render(items, out, az=-35, el=28, size=1000, title='', notes=(), labels=()):
    """items: [(solid, rgb, alpha)], labels: [(xyz, text)]."""
    a, e = np.radians(az), np.radians(el)
    d = np.array([np.cos(e) * np.sin(a), -np.cos(e) * np.cos(a), np.sin(e)])
    r = np.array([np.cos(a), np.sin(a), 0])
    u = np.cross(d, r)
    light = np.array([0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)
    polys = []
    for solid, col, alpha in items:
        T = tris(solid)
        if not len(T):
            continue
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        sh = 0.5 + 0.5 * np.abs(n @ light)
        X, Y, Z = T @ r, T @ u, T @ d
        for k in range(len(T)):
            polys.append((Z[k].mean(), np.c_[X[k], Y[k]], tuple(int(c * sh[k]) for c in col) + (alpha,)))
    allp = np.vstack([p for _, p, _ in polys])
    mn, mx = allp.min(0), allp.max(0)
    top = 60 if title else 20
    bottom = 20 + 26 * len(notes)
    s = min((size - 40) / (mx[0] - mn[0]), (size * 0.9) / (mx[1] - mn[1]))
    Hh = int((mx[1] - mn[1]) * s + top + bottom + 20)
    img = Image.new('RGB', (size, Hh), 'white')
    dr = ImageDraw.Draw(img, 'RGBA')
    P = lambda p: (20 + (p[0] - mn[0]) * s, top + 10 + (mx[1] - p[1]) * s)
    for _, p, col in sorted(polys, key=lambda t: t[0]):
        dr.polygon([P(x) for x in p], fill=col)
    f = ImageFont.truetype(FONT_B, 18)
    for xyz, text in labels:
        xyz = np.array(xyz)
        x, y = P((xyz @ r, xyz @ u))
        w = dr.textlength(text, font=f)
        dr.rounded_rectangle([x - w / 2 - 7, y - 13, x + w / 2 + 7, y + 13], 7, fill=(255, 255, 255, 235), outline=(40, 40, 40))
        dr.text((x - w / 2, y - 11), text, fill='black', font=f)
    if title:
        dr.text((20, 15), title, fill='black', font=ImageFont.truetype(FONT_B, 26))
    fn = ImageFont.truetype(FONT, 19)
    for i, t in enumerate(notes):
        dr.text((20, Hh - bottom + 4 + 26 * i), t, fill=(60, 60, 60), font=fn)
    box = ImageChops.difference(img, Image.new('RGB', img.size, 'white')).getbbox()
    img.crop((max(0, box[0] - 15), 0, min(img.width, box[2] + 15), img.height)).save(out)


def items_of(parts, grey=False, sheath_alpha=255, hide=()):
    out = []
    for q in parts:
        if any(h in q.name for h in hide):
            continue
        alpha = sheath_alpha if ('обшивка' in q.name or q.name == 'тент') else 255
        out.append((q.solid, GREY if grey else q.color, alpha))
    return out
