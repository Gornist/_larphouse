"""Каркас: стойка, лежень, обвязка, колья, болты пролёта к каркасу.

Лежень, обвязка и болты пролёта строятся в координатах ребра (см. house.edge_loc):
s — вдоль ребра от грани левой стойки, o — внутрь от наружной грани.
"""
from build123d import Location, Plane, mirror

from .dims import (PW, H, T, D, POST, OPEN, PITCH, LEZ, BEAM, BL, Z0, ZB, ZP, GAP, WC,
                   BH, SPAN_O, ANG_O, TOP_O, Z_ANG, Z_SPAN)
from .geom import P, box, cyl, place, FRAME
from .tally import CUT, HW, bar, bolt, futorka, steel


def post():
    """Стойка 100×100 (одинаковая для угла, стены и центра). x, y — от западной и южной граней."""
    L = ZP
    p = box(0, POST, 0, POST, 0, L)
    holes = []
    for d, (zb, zt) in Z_ANG.items():
        for off, z in ((ANG_O, zb), (POST - ANG_O, zb), (TOP_O, zt), (POST - TOP_O, zt)):
            holes.append((d, off, z))
    for (d, _), zs in Z_SPAN.items():
        for z in zs:
            for off in (SPAN_O, POST - SPAN_O):
                holes.append((d, off, z))
    for d, off, z in holes:
        p = p - (cyl(BH, (-1, off, z), (POST + 1, off, z)) if d == 'x' else cyl(BH, (off, -1, z), (off, POST + 1, z)))
    p = p - cyl(14, (POST / 2, POST / 2, L - 36), (POST / 2, POST / 2, L + 1))
    return [bar(f'стойка_100х100х{L}', '100×100', L, p, FRAME), futorka(POST / 2, POST / 2, L)]


def angle(kind, z0, o_bolt, z_bolt, right):
    """Уголок 90×90×40 у грани стойки; right — у правой стойки ребра (зеркально)."""
    HW['Уголок крепёжный усиленный KUU 90×90×40'] += 1
    if kind == 'низ':
        u = box(0, 3, 57, 97, z0, z0 + 90) + box(0, 90, 57, 97, z0, z0 + 3)
    else:
        u = box(0, 3, BEAM[0], BEAM[0] + 90, z0, z0 + 40) + box(0, 90, BEAM[0], BEAM[0] + 3, z0, z0 + 40)
    u = u - cyl(BH, (-1, o_bolt, z_bolt), (4, o_bolt, z_bolt))
    if right:
        u = mirror(u, Plane.YZ).moved(Location((OPEN, 0, 0)))
    return P(u, 'уголок_90х90х40', 'сталь', (90, 90, 100))


def lezhen(d):
    """Лежень между стойками; s=0 — грань левой стойки."""
    lb = box(2, 2 + BL, 0, 100, 0, LEZ)
    parts = []
    for s in (500, OPEN - 500):
        lb = lb - cyl(14, (s, ANG_O, -1), (s, ANG_O, LEZ + 1))
    for right in (False, True):
        parts.append(angle('низ', LEZ, ANG_O, Z_ANG[d][0], right))
    CUT[('50×100', BL)] += 1
    return [P(lb, f'лежень_50х100х{BL}', 'дерево', FRAME)] + parts


def stakes():
    """Колья из арматуры сквозь лежень в землю (только по периметру)."""
    out = []
    for s in (500, OPEN - 500):
        out.append(steel(cyl(12, (s, ANG_O, LEZ - 1000), (s, ANG_O, LEZ)), 'арматура_12х1000'))
        HW['Арматура Ø12 (кол 1 м)'] += 1
    return out


def beam(d):
    """Верхняя обвязка между стойками, на ребро. Одна деталь на все рёбра:
    футорки и сверху, и снизу; для рёбер вдоль Y её переворачивают
    (поворот 180° вокруг поперечной оси) — уголки оказываются на высоте Y."""
    zc = (ZB + ZP) / 2
    bb = box(2, 2 + BL, 0, BEAM[0], ZB, ZP)
    parts = []
    for s_, o in ((GAP + PW / 2, SPAN_O), (OPEN / 2, WC), (GAP + 2.5 * PW, SPAN_O)):
        for face in (-1, 1):                       # низ: болты пролёта, верх: пята фермы
            z0 = ZB if face < 0 else ZP
            bb = bb - cyl(14, (s_, o, z0 + face), (s_, o, z0 - face * 46))
            parts.append(futorka(s_, o, z0 + 25 if face < 0 else z0))
    for right in (False, True):
        parts.append(angle('верх', Z_ANG['x'][1] - 20, TOP_O, Z_ANG['x'][1], right))
    CUT[('50×100', BL)] += 1
    parts = [P(bb, f'обвязка_50х100х{BL}', 'дерево', FRAME)] + parts
    if d == 'y':
        flip = Location((OPEN / 2, 0, zc)) * Location((0, 0, 0), (0, 180, 0)) * Location((-OPEN / 2, 0, -zc))
        parts = place(parts, flip)
    return parts


def span_bolts(d):
    """Болты пролёта к стойкам: слева — через левую стойку, справа — через правую; и 2 снизу в обвязку."""
    out = [bolt((0, SPAN_O, z), (1, 0, 0), 150, 'барашек') for z in Z_SPAN[(d, 'L')]]
    out += [bolt((PITCH + POST, SPAN_O, z), (-1, 0, 0), 150, 'барашек') for z in Z_SPAN[(d, 'R')]]
    out += [bolt((POST + GAP + s, SPAN_O, Z0 + H - T), (0, 0, 1), 80, 'футорка') for s in (PW / 2, 2.5 * PW)]
    return out
