"""Каркас: стойка, лежень, обвязка, колья, болты пролёта к каркасу.

Лежень, обвязка и болты пролёта строятся в координатах ребра (см. house.edge_loc):
s — вдоль ребра от грани левой стойки, o — внутрь от наружной грани.
"""
from build123d import Location, Plane, mirror

from .dims import (PW, H, T, D, POST, OPEN, PITCH, LEZ, BEAM, BL, Z0, ZB, ZP, GAP, WC,
                   BH, SPAN_O, ANG_O, TOP_O, Z_ANG, Z_SPAN, ANG, ANG_FIX)
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


def mirror_s(q):
    """Отражение детали по s: у правой стойки ребра s -> OPEN - s."""
    m = P(mirror(q.solid, Plane.YZ).moved(Location((OPEN, 0, 0))), q.name, q.mat, q.color)
    if hasattr(q, 'axis'):
        m.axis = tuple((OPEN - p[0], p[1], p[2]) for p in q.axis)
    return m


def angle(kind, z0, o_bolt, z_bolt, right):
    # z_bolt — высоты отверстий под болт сквозь стойку
    """Уголок г/к 63×63×6, отрезок 40 мм, у грани стойки; right — у правой стойки ребра (зеркально).
    Одна полка — на грани стойки (болт на площадке сквозь стойку), другая — на брусе: прикручена к нему
    насквозь болтом М10×80 с гайкой в мастерской и больше не снимается.
    низ — полка лежит на лежне, болт снизу (головка утоплена в лежень);
    верх — полка на внутренней грани обвязки, болт снаружи насквозь."""
    a, t, w = ANG
    HW['Уголок г/к 63×63×6, отрезок 40 мм'] += 1
    if kind == 'низ':
        u = box(0, t, 57, 57 + w, z0, z0 + a) + box(0, a, 57, 57 + w, z0, z0 + t)
        u = u - cyl(BH, (ANG_FIX, o_bolt, z0 - 1), (ANG_FIX, o_bolt, z0 + t + 1))
        fix = bolt((ANG_FIX, o_bolt, 10), (0, 0, 1), 80, 'гайка')
    else:
        u = box(0, t, BEAM[0], BEAM[0] + a, z0, z0 + w) + box(0, a, BEAM[0], BEAM[0] + t, z0, z0 + w)
        u = u - cyl(BH, (ANG_FIX, BEAM[0] - 1, z0 + w / 2), (ANG_FIX, BEAM[0] + t + 1, z0 + w / 2))
        fix = bolt((ANG_FIX, 0, z0 + w / 2), (0, 1, 0), 80, 'гайка')
    for z in z_bolt:                                     # у лежня — оба отверстия: все лежни одинаковые
        u = u - cyl(BH, (-1, o_bolt, z), (t + 1, o_bolt, z))
    parts = [P(u, 'уголок_63х63х6х40', 'сталь', (90, 90, 100)), fix]
    if right:
        parts = [mirror_s(q) for q in parts]
    return parts


def lezhen():
    """Лежень между стойками (один на все рёбра); s=0 — грань левой стойки."""
    lb = box(2, 2 + BL, 0, 100, 0, LEZ)
    parts = []
    for s in (500, OPEN - 500):
        lb = lb - cyl(14, (s, ANG_O, -1), (s, ANG_O, LEZ + 1))
    for s in (ANG_FIX, OPEN - ANG_FIX):                      # болты уголков: снизу, головка утоплена
        lb = lb - cyl(BH, (s, ANG_O, -1), (s, ANG_O, LEZ + 1)) - cyl(24, (s, ANG_O, -1), (s, ANG_O, 10))
    for right in (False, True):
        parts += angle('низ', LEZ, ANG_O, (Z_ANG['x'][0], Z_ANG['y'][0]), right)
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
    for s in (ANG_FIX, OPEN - ANG_FIX):                      # болты уголков: насквозь поперёк
        bb = bb - cyl(BH, (s, -1, Z_ANG['x'][1]), (s, BEAM[0] + 1, Z_ANG['x'][1]))
    for right in (False, True):
        parts += angle('верх', Z_ANG['x'][1] - 20, TOP_O, (Z_ANG['x'][1],), right)
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
