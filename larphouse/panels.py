"""Щиты 997×2400 и пролёты из трёх щитов (мастерская, неразборные)."""
from build123d import Location

from .dims import PW, H, T, D, PLY, BH, BOLT_Z, END_Z
from .geom import P, box, cyl, place, WOOD2, PLYC
from .tally import HW, bar, bolt, steel

KINDS = ('глухой', 'окно', 'дверь')


def panel(kind):
    """Щит: X = s вдоль, Y = n (0 — наружная грань рамы, обшивка n<0), Z вверх."""
    parts = []
    left, right = box(0, T, 0, D, 0, H), box(PW - T, PW, 0, D, 0, H)
    zs = BOLT_Z + (END_Z if kind == 'глухой' else ())
    for z in zs:
        left = left - cyl(BH, (-1, D / 2, z), (T + 1, D / 2, z))
        right = right - cyl(BH, (PW - T - 1, D / 2, z), (PW + 1, D / 2, z))
    parts += [bar('стойка_щита_25х50х2400', '25×50', H, left),
              bar('стойка_щита_25х50х2400', '25×50', H, right)]
    cross = PW - 2 * T
    top = box(T, PW - T, 0, D, H - T, H)
    if kind == 'глухой':
        top = top - cyl(BH, (PW / 2, D / 2, H - T - 1), (PW / 2, D / 2, H + 1))
    parts.append(bar(f'перемычка_25х50х{cross}', '25×50', cross, box(T, PW - T, 0, D, 0, T), WOOD2))
    parts.append(bar(f'перемычка_25х50х{cross}', '25×50', cross, top, WOOD2))
    cut = None
    if kind == 'окно':
        for z0 in (1187.5, 2187.5):
            parts.append(bar(f'перемычка_25х50х{cross}', '25×50', cross, box(T, PW - T, 0, D, z0, z0 + T), WOOD2))
        cut = (T, PW - T, 1212.5, 2187.5)
    if kind == 'дверь':
        for s0 in (73.5, 898.5):
            parts.append(bar('стойка_двери_25х50х2050', '25×50', 2050, box(s0, s0 + T, 0, D, T, 2075), WOOD2))
        parts.append(bar(f'перемычка_25х50х{cross}', '25×50', cross, box(T, PW - T, 0, D, 2075, 2100), WOOD2))
        cut = (98.5, 898.5, T, 2075)
        parts += door_leaf(98.5, 898.5)
    sh = box(0, PW, -PLY, 0, 0, H)
    if cut:
        sh = sh - box(cut[0], cut[1], -PLY - 1, 1, cut[2], cut[3])
    parts.append(P(sh, f'обшивка_фанера_{PLY}мм_{PW}х{H}', 'фанера', PLYC))
    return parts


def door_leaf(a, b):
    s0, s1, z0, z1 = a + 5, b - 5, 30, 2070
    p = []
    for s in (s0, s1 - 50):
        p.append(bar(f'полотно_стойка_25х50х{z1 - z0}', '25×50', z1 - z0, box(s, s + 50, 0, T, z0, z1), (200, 150, 95)))
    for z in (z0, (z0 + z1) / 2 - 25, z1 - 50):
        p.append(bar(f'полотно_перемычка_25х50х{s1 - s0 - 100}', '25×50', s1 - s0 - 100,
                     box(s0 + 50, s1 - 50, 0, T, z, z + 50), (200, 150, 95)))
    p.append(P(box(s0, s1, -PLY, 0, z0, z1), f'полотно_фанера_{s1 - s0:.0f}х{z1 - z0}', 'фанера', (225, 200, 150)))
    for z in (300, 1700):
        p.append(steel(box(s0 - 5, s0 + 25, T, T + 3, z, z + 100), 'петля_100', (60, 60, 60)))
    p.append(steel(box(s1 - 45, s1 - 25, T, T + 40, 1000, 1150), 'ручка', (60, 60, 60)))
    HW['Петля карточная 100 мм'] += 2
    HW['Ручка-скоба дверная'] += 1
    HW['Шпингалет накладной'] += 1
    return p


def span(mid):
    """Пролёт: глухой + mid + глухой, на стыках по 3 болта М10×80 с гайкой."""
    parts = []
    for i, k in enumerate(('глухой', mid, 'глухой')):
        parts += place(panel(k), Location((i * PW, 0, 0)))
    for i in (1, 2):
        for z in BOLT_Z:
            parts.append(bolt((i * PW - T, D / 2, z), (1, 0, 0), 80, 'гайка'))
    return parts
