"""Иллюстрации версии 5: блоки и шаги монтажа.

Запуск:  python tools/v5_draw.py step/5/img
"""
import os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
from build123d import Location

sys.path.insert(0, os.path.dirname(__file__))
import v5_house as v

FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
GREY = (205, 205, 205)
_tess = {}


def tris(solid):
    key = id(solid)
    if key not in _tess:
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
        _tess[key] = np.array(res) if res else np.zeros((0, 3, 3))
    return _tess[key]


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


def main(out):
    os.makedirs(out, exist_ok=True)
    blocks, house = v.build()

    # ---- блоки
    red = '● красное — замки/штыри'
    for k, t in [('глухой', 'Глухой ×4'), ('угловой', 'Угловой ×4'),
                 ('окно', 'Окно ×3'), ('дверь', 'Дверь ×1')]:
        pp = blocks[f'щит_{k}']
        render(items_of(pp), f'{out}/щит_{k}_снаружи.png', az=-20, el=12, size=700, title=t + ', снаружи')
        render(items_of(pp), f'{out}/щит_{k}_изнутри.png', az=160, el=12, size=700, title=t + ', изнутри')
    for k, t in [('средняя', 'Полуферма средняя ×2'), ('фронтон_0', 'Полуферма фронтонная «А» ×2'),
                 ('фронтон_25', 'Полуферма фронтонная «Б» ×2')]:
        render(items_of(blocks[f'полуферма_{k}']), f'{out}/полуферма_{k}.png', az=-90, el=0, size=1000, title=t + ' — вид сбоку')
        render(items_of(blocks[f'полуферма_{k}']), f'{out}/полуферма_{k}_изо.png', az=-60, el=25, size=800, title=t)
    for k in ('карнизная', 'фронтонная'):
        render(items_of(blocks[f'обвязка_{k}']), f'{out}/обвязка_{k}.png', az=-15, el=35, size=1000,
               title=f'Обвязка {k} 50×50×3050 ×2')

    # ---- шаги монтажа
    groups = [(g, b, parts) for g, b, parts in house]
    def sel(pred):
        return [q for g, b, parts in groups if pred(g, b) for q in parts]
    base = sel(lambda g, b: g == 'основание')
    walls = {w: sel(lambda g, b, w=w: g == f'стена_{w}' and not b.startswith('обвязка')) for w in 'ABCD'}
    plates = sel(lambda g, b: g.startswith('стена') and b.startswith('обвязка'))
    trusses = sel(lambda g, b: g == 'крыша' and b.startswith('ферма'))
    ridge = sel(lambda g, b: b in ('конёк', 'прогон'))
    tent = sel(lambda g, b: b == 'тент')
    hide = ('анкер',)
    steps = [
        ('шаг1_основание', 'Шаг 1. Основание: 4 лежня + анкеры', [], base, ['Углы вполдерева на штыри, выровнять подкладками, диагонали равны.']),
        ('шаг2_стена_A', 'Шаг 2. Первая стена: 3 щита', base, walls['A'], ['Щиты на штыри лежня, стыки — 2 замка, угловой щит справа.']),
        ('шаг3_стены', 'Шаг 3. Остальные стены по кругу', base + walls['A'], walls['B'] + walls['C'] + walls['D'], ['Каждая стена упирается в стойку предыдущей: 2 замка на угол.']),
        ('шаг4_обвязки', 'Шаг 4. Обвязки на штыри щитов', base + sum(walls.values(), []), plates, ['Угол обвязок — 1 замок.']),
        ('шаг5_фермы', 'Шаг 5. Фермы: пары полуферм на земле → наверх', base + sum(walls.values(), []) + plates, trusses,
         ['Стойки полуферм стянуть болтом с барашком. Пяты — на штыри, R-шплинты.']),
        ('шаг6_конёк', 'Шаг 6. Конёк и 4 прогона', base + sum(walls.values(), []) + plates + trusses, ridge, ['Конёк — на штыри стоек ферм, прогоны — в лапки.']),
        ('шаг7_тент', 'Шаг 7. Тент и растяжки', base + sum(walls.values(), []) + plates + trusses + ridge, tent, ['Тент — через конёк, к люверсам/лежням; 4 растяжки.']),
    ]
    for fn, title, old, new, notes in steps:
        it = items_of(old, grey=True, sheath_alpha=255, hide=hide) + items_of(new, sheath_alpha=200 if 'тент' in fn else 255)
        render(it, f'{out}/{fn}.png', az=-35, el=28, size=1000, title=title, notes=notes)
    allp = base + sum(walls.values(), []) + plates + trusses + ridge + tent
    render(items_of(allp, hide=hide), f'{out}/дом.png', az=-35, el=22, size=1100, title='Дом v5 в сборе')
    render(items_of(allp, hide=hide + ('тент',)), f'{out}/дом_без_тента.png', az=145, el=30, size=1100,
           title='Без тента (вид с обратной стороны)')
    fr = items_of(base + plates + trusses + ridge, hide=hide) + items_of(sum(walls.values(), []), hide=hide + ('обшивка', 'полотно'))
    render(fr, f'{out}/дом_каркас.png', az=-35, el=28, size=1100, title='Каркас без обшивки и тента')


if __name__ == '__main__':
    main(sys.argv[1])
