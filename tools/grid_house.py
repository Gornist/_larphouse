"""Модульная система домов: сетка NX × NY ячеек 3,1 м.

Одинаковые детали для любого размера:
  угловые/промежуточные стойки 100×100 (без поворота, отверстия симметричны),
  лежни и верхние обвязки 50×100×2996 на уголках, пролёты 2991×2400 (3 щита).
Крыша — двускатная, конёк вдоль X:
  NY = 1 — малые полуфермы (пролёт 3,2 м), NY = 2 — большие (пролёт 6,3 м,
  опора на среднюю линию стоек).

Запуск:  python tools/grid_house.py <имя> <NX> <NY> <out_dir>
Раскладка пролётов задаётся в CONFIGS.
"""
import collections, math, os, re, sys
import numpy as np
from build123d import Compound, Location

sys.path.insert(0, os.path.dirname(__file__))
import v5_house as b
from v5_house import (P, box, cyl, prism_x, bar, bolt, futorka, steel, place, compound,
                      CUT, HW, PW, H, T, D, PLY, PLY_G, SD, POST, OPEN, LEZ, BEAM, Z0, ZB, ZP,
                      GAP, WC, BH, WOOD, WOOD2, PLYC, FRAME, TAN, COS, SIN)
from step_io import save_step

PITCH = POST + OPEN          # 3100 — шаг сетки
SPAN_O = D / 2 + PLY         # 28 — ось болтов пролёта от наружной грани
ANG_O = 77                   # ось болта уголка лежня
TOP_O = 75                   # ось болта уголка обвязки
BL = OPEN - 4

# высоты болтов (от земли), чтобы отверстия разных направлений не пересекались
Z_ANG = {'x': (80, ZB + 25), 'y': (115, ZB + 75)}                 # уголки: низ, верх
Z_SPAN = {('x', 'L'): (650, 1850), ('x', 'R'): (750, 1950),        # пролёт — стойка
          ('y', 'L'): (450, 1250), ('y', 'R'): (550, 1350)}
b.END_Z = tuple(sorted(z - Z0 for v in Z_SPAN.values() for z in v))  # отверстия в крайних щитах


# ------------------------------------------------------------------ стойка
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


# ------------------------------------------------------------------ лежень, обвязка (в координатах ребра)
def angle(kind, z0, o_bolt, z_bolt, right):
    """Уголок 90×90×40 у грани стойки; right — у правой стойки ребра (зеркально)."""
    HW['Уголок крепёжный усиленный KUU 90×90×40'] += 1
    if kind == 'низ':
        u = box(0, 3, 57, 97, z0, z0 + 90) + box(0, 90, 57, 97, z0, z0 + 3)
    else:
        u = box(0, 3, BEAM[0], BEAM[0] + 90, z0, z0 + 40) + box(0, 90, BEAM[0], BEAM[0] + 3, z0, z0 + 40)
    u = u - cyl(BH, (-1, o_bolt, z_bolt), (4, o_bolt, z_bolt))
    if right:
        from build123d import Plane, mirror
        u = mirror(u, Plane.YZ).moved(Location((OPEN, 0, 0)))
    return P(u, 'уголок_90х90х40', 'сталь', (90, 90, 100))


def lezhen(d):
    """Лежень между стойками; s=0 — грань левой стойки, o — от наружной грани ребра."""
    lb = box(2, 2 + BL, 0, 100, 0, LEZ)
    parts = []
    for s in (500, OPEN - 500):
        lb = lb - cyl(14, (s, ANG_O, -1), (s, ANG_O, LEZ + 1))
    for right in (False, True):
        parts.append(angle('низ', LEZ, ANG_O, Z_ANG[d][0], right))
    CUT[('50×100', BL)] += 1
    return [P(lb, f'лежень_50х100х{BL}', 'дерево', FRAME)] + parts


def stakes():
    out = []
    for s in (500, OPEN - 500):
        out.append(steel(cyl(12, (s, ANG_O, LEZ - 1000), (s, ANG_O, LEZ)), 'арматура_12х1000'))
        HW['Арматура Ø12 (кол 1 м)'] += 1
    return out


def beam(d, eave_mid=True):
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
            zf = (z0, z0 + 25) if face < 0 else (z0 - 25, z0)
            t = cyl(14, (s_, o, zf[0]), (s_, o, zf[1])) - cyl(10.5, (s_, o, zf[0] - 1), (s_, o, zf[1] + 1))
            parts.append(P(t, 'футорка_М10', 'сталь', (150, 150, 60)))
            HW['Гайка врезная (футорка) М10'] += 1
    for right in (False, True):
        parts.append(angle('верх', Z_ANG['x'][1] - 20, TOP_O, Z_ANG['x'][1], right))
    CUT[('50×100', BL)] += 1
    parts = [P(bb, f'обвязка_50х100х{BL}', 'дерево', FRAME)] + parts
    if d == 'y':
        flip = Location((OPEN / 2, 0, zc)) * Location((0, 0, 0), (0, 180, 0)) * Location((-OPEN / 2, 0, -zc))
        parts = place(parts, flip)
    return parts


def span(kind):
    mid = {'окно': 'окно', 'дверь': 'дверь', 'глухой': 'глухой'}[kind]
    return b.span(mid)


def span_bolts(d):
    """Болты пролёта к стойкам (в координатах ребра): слева — через левую стойку, справа — через правую."""
    out = [bolt((0, SPAN_O, z), (1, 0, 0), 150, 'барашек') for z in Z_SPAN[(d, 'L')]]
    out += [bolt((PITCH + POST, SPAN_O, z), (-1, 0, 0), 150, 'барашек') for z in Z_SPAN[(d, 'R')]]
    out += [bolt((POST + GAP + s, SPAN_O, Z0 + H - T), (0, 0, 1), 80, 'футорка') for s in (PW / 2, 2.5 * PW)]
    return out


# ------------------------------------------------------------------ полуфермы
class Roof:
    def __init__(self, span_half, chord_l, tail_u, purlins, struts):
        self.SH, self.CL, self.TU, self.PU, self.ST = span_half, chord_l, tail_u, purlins, struts

    def L1(self, u):
        return D + (self.CL - u) * TAN

    def L2(self, u):
        return self.L1(u) + D / COS

    @property
    def HK(self):
        return self.L2(D)

    @property
    def PE(self):
        """Карнизный прогон — у конца стропила; под него заворачивают край тента."""
        return self.TU - 25 * COS                    # наружная кромка прогона — у торца стропила

    @property
    def PALL(self):
        return tuple(self.PU) + (self.PE,)


PURLIN = (25, 50)            # прогон 25×50 плашмя: 25 по нормали к скату, 50 вдоль ската
RIDGE_B = (25, -25)          # болты конька: от оси конька по Y (сквозь стойки обеих полуферм)


def purlin_sides(kind):
    """С каких сторон стропила опоры прогонов (+1 — X > T). У фронтонных — не со стороны обшивки;
    у средних — с обеих: над средней фермой бывает стык прогонов, болт нужен каждому куску."""
    return {'фронтон_0': (1,), 'фронтон_25': (-1,), 'средняя': (1, -1)}[kind]


def purlin_xb(side):
    """Ось болта опоры по X в координатах полуфермы."""
    return T + D / 2 if side > 0 else -D / 2


def half_truss(r, kind):
    """Полуферма: X — толщина 0..25, Y = -u (u от конька), Z от низа затяжки."""
    p, L1, L2, HK = [], r.L1, r.L2, r.HK
    chord = prism_x([(0, 0), (r.CL, 0), (r.CL, D), (0, D)], 0, T)
    for hu in (r.SH - POST / 2, r.SH - WC):              # пята на стойке / на обвязке
        chord = chord - cyl(BH, (T / 2, -hu, -1), (T / 2, -hu, D + 1))
    p.append(bar(f'затяжка_25х50х{r.CL}', '25×50', r.CL, chord, WOOD))
    pst = prism_x([(0, D), (D, D), (D, HK), (0, HK)], 0, T)
    pst = pst - cyl(BH, (T / 2, 1, (D + HK) / 2), (T / 2, -D - 1, (D + HK) / 2))
    ridge_hole = cyl(BH, (-PLY_G - 2, -RIDGE_B[0], HK - 25), (T + PLY_G + 2, -RIDGE_B[0], HK - 25))
    pst = pst - ridge_hole
    p.append(bar(f'стойка_фермы_25х50х{HK - D:.0f}', '25×50', HK - D, pst, WOOD2))
    raf = (r.TU - D) / COS
    p.append(bar(f'стропило_25х50х{raf:.0f}', '25×50', raf,
                 prism_x([(D, L1(D)), (r.TU, L1(r.TU)), (r.TU, L2(r.TU)), (D, L2(D))], 0, T), (205, 160, 110)))

    def hit(u0, z0):
        s = (D + r.CL * TAN - z0 - u0 * TAN) / (1 + TAN)
        return (u0 + s, z0 + s)
    a, c = (D + D * math.sqrt(2), D), (D, D + D * math.sqrt(2))
    br = math.dist(a, hit(*a))
    p.append(bar(f'подкос_25х50х{br:.0f}', '25×50', br, prism_x([(D, D), a, hit(*a), hit(*c), c], 0, T), (165, 115, 70)))
    gus = {'вершина': [(0, HK), (D, HK), (250, L2(250)), (250, L2(250) - 250), (0, HK - 250)],
           'пята': [(r.CL - 250, 0), (r.CL, 0), (r.CL, L2(r.CL)), (r.CL - 250, L2(r.CL - 250))],
           'низ_подкоса': [(0, 0), (220, 0), (220, 220), (0, 220)],
           'верх_подкоса': [(hit(*a)[0] - 150, L1(hit(*a)[0] - 150) - 160), (hit(*a)[0] + 60, L1(hit(*a)[0] + 60) - 160),
                            (hit(*a)[0] + 60, L2(hit(*a)[0] + 60)), (hit(*a)[0] - 150, L2(hit(*a)[0] - 150))]}
    for su in r.ST:                                       # вертикальные стойки-бабки
        h = L1(su + T) - D
        p.append(bar(f'бабка_25х50х{h:.0f}', '25×50', h,
                     prism_x([(su, D), (su + T, D), (su + T, L1(su + T)), (su, L1(su))], 0, T), (165, 115, 70)))
        gus[f'бабка_низ_{su}'] = [(su - 90, 0), (su + T + 90, 0), (su + T + 90, D + 90), (su - 90, D + 90)]
        gus[f'бабка_верх_{su}'] = [(su - 90, L1(su - 90) - 90), (su + T + 90, L1(su + T + 90) - 90),
                                   (su + T + 90, L2(su + T + 90)), (su - 90, L2(su - 90))]
    # опоры прогонов: брусок 25×50×100 плашмя сбоку стропила, верх заподлицо со стропилом;
    # прогон ложится на стропило и опору, болт М10×80 сквозь прогон и опору, барашек снизу
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for side in purlin_sides(kind):
        xs_ = (T, T + D) if side > 0 else (-D, 0)
        xb = purlin_xb(side)
        for u0 in r.PALL:
            C = np.array([u0, L2(u0)])
            Cb = C - (25 * t_ if u0 == r.PE else 0)       # у карнизного — сдвинута внутрь, в торец стропила
            q = [Cb - 50 * t_, Cb + 50 * t_, Cb + 50 * t_ - T * n_, Cb - 50 * t_ - T * n_]
            blk_ = prism_x([tuple(x) for x in q], *xs_)
            h0, h1 = C + 5 * n_, C - (T + 5) * n_
            blk_ = blk_ - cyl(BH, (xb, -h0[0], h0[1]), (xb, -h1[0], h1[1]))
            p.append(bar('опора_прогона_25х50х100', '25×50', 100, blk_, WOOD2))
    sides = {'средняя': [(-PLY_G, 0), (T, T + PLY_G)], 'фронтон_0': [(T, T + PLY_G)], 'фронтон_25': [(-PLY_G, 0)]}[kind]
    for x0, x1 in sides:
        for g, pts in gus.items():
            gs = prism_x(pts, x0, x1)
            if g == 'вершина':
                gs = gs - ridge_hole
            p.append(P(gs, f'косынка_фанера_{PLY_G}', 'фанера', (240, 220, 175)))
    if kind != 'средняя':
        x0, x1 = (-PLY, 0) if kind == 'фронтон_0' else (T, T + PLY)
        e = r.SH + PLY
        sh = prism_x([(0, 0), (e, 0), (e, L2(e)), (D, HK), (0, HK)], x0, x1) - ridge_hole
        p.append(P(sh, f'обшивка_фронтона_ФСФ_{PLY}', 'фанера', PLYC))
    return p


ROOFS = {1: Roof(1600, 1700, 1980, (650, 1320), ()),
         2: Roof(3150, 3250, 3530, (620, 1400, 2100, 2800), (1900,))}   # 620: опора прогона мимо косынки подкоса


# ------------------------------------------------------------------ дом
CONFIGS = {
    # стороны: S, N — вдоль X (по ячейкам слева направо), W, E — вдоль Y (снизу вверх)
    '3х3': dict(NX=1, NY=1, S=['окно'], N=['окно'], W=['дверь'], E=['окно']),
    '6х6': dict(NX=2, NY=2, S=['окно', 'окно'], N=['окно', 'окно'], W=['дверь', 'глухой'], E=['окно', 'глухой']),
    '3х6': dict(NX=2, NY=1, S=['окно', 'окно'], N=['глухой', 'окно'], W=['дверь'], E=['окно']),
    '3х9': dict(NX=3, NY=1, S=['окно', 'окно', 'окно'], N=['глухой', 'окно', 'глухой'], W=['дверь'], E=['окно']),
}


def edge_loc(d, i, j, sigma):
    """Система координат ребра: s вдоль ребра (0..PITCH+POST, стойки по краям), o — внутрь от наружной грани."""
    if d == 'x':
        return (Location((i * PITCH, j * PITCH, 0), (0, 0, 0)) if sigma < 0
                else Location(((i + 1) * PITCH + POST, j * PITCH + POST, 0), (0, 0, 180)))
    return (Location((i * PITCH, (j + 1) * PITCH + POST, 0), (0, 0, 270)) if sigma < 0
            else Location((i * PITCH + POST, j * PITCH, 0), (0, 0, 90)))


def build(cfg):
    CUT.clear(), HW.clear()
    NX, NY = cfg['NX'], cfg['NY']
    SX, SY = NX * PITCH + POST, NY * PITCH + POST
    house, blocks = [], {}

    def blk(name, parts):
        blocks.setdefault(name, parts)
        return parts

    # стойки
    for i in range(NX + 1):
        for j in range(NY + 1):
            house.append(('каркас', f'стойка_{i}{j}', place(blk('стойка', post()), Location((i * PITCH, j * PITCH, 0)))))
    # рёбра
    edges = []
    for j in range(NY + 1):
        for i in range(NX):
            per = j in (0, NY)
            kind = (cfg['S'][i] if j == 0 else cfg['N'][NX - 1 - i]) if per else None
            edges.append(('x', i, j, 1 if (j == NY and NY > 0) else -1, per, kind))
    for i in range(NX + 1):
        for j in range(NY):
            per = i in (0, NX)
            kind = (cfg['W'][NY - 1 - j] if i == 0 else cfg['E'][j]) if per else None
            edges.append(('y', i, j, 1 if i == NX else -1, per, kind))
    ang_bolts = set()
    for d, i, j, sg, per, kind in edges:
        loc = edge_loc(d, i, j, sg)
        nm = f'{d}{i}{j}'
        house.append(('основание', f'лежень_{nm}', place(blk('лежень', lezhen(d)), loc * Location((POST, 0, 0)))))
        if per:
            house.append(('основание', f'колья_{nm}', place(stakes(), loc * Location((POST, 0, 0)))))
        eave_mid = d == 'x'
        house.append(('каркас', f'обвязка_{nm}', place(blk('обвязка', beam(d, eave_mid)), loc * Location((POST, 0, 0)))))
        if kind:
            house.append(('пролёты', f'пролёт_{kind}_{nm}', place(blk(f'пролёт_{kind}', span(kind)), loc * Location((POST + GAP, PLY, Z0)))))
            house.append(('пролёты', f'болты_пролёта_{nm}', place(span_bolts(d), loc)))
        # болты уголков: по одному сквозному на узел/направление/высоту
        for end_s in (0, PITCH):
            for o, z in ((ANG_O, Z_ANG[d][0]), (TOP_O, Z_ANG[d][1])):
                g = loc * Location((end_s + POST / 2, o, z))
                key = (d, round(g.position.X), round(g.position.Y), round(g.position.Z))
                if key in ang_bolts:
                    continue
                ang_bolts.add(key)
                head = Location((end_s - 5 if end_s == 0 else end_s + POST + 5, o, z))
                house.append(('основание' if o == ANG_O else 'каркас', f'болт_уголка_{"низ" if o == ANG_O else "верх"}_{nm}_{end_s}',
                              place([bolt((0, 0, 0), (1, 0, 0) if end_s == 0 else (-1, 0, 0), 130, 'барашек')], loc * head)))
    # крыша
    r = ROOFS[NY]
    YR = SY / 2
    xs = sorted({i * PITCH + POST / 2 for i in range(NX + 1)} | {i * PITCH + POST + OPEN / 2 for i in range(NX)})
    grid_x = {i * PITCH + POST / 2 for i in range(NX + 1)}
    for k, xc in enumerate(xs):
        x0 = xc - T / 2
        first, last = k == 0, k == len(xs) - 1
        kinds = ('фронтон_0', 'фронтон_25') if first else ('фронтон_25', 'фронтон_0') if last else ('средняя', 'средняя')
        tag = 'М' if NY == 1 else 'Б'
        south = blk(f'полуферма_{tag}_{kinds[0]}', half_truss(r, kinds[0]))
        north = blk(f'полуферма_{tag}_{kinds[1]}', half_truss(r, kinds[1]))
        tr = place(south, Location((x0, YR, ZP))) + place(north, Location((x0 + T, YR, ZP), (0, 0, 180)))
        tr.append(bolt((xc, YR - D, ZP + (D + r.HK) / 2), (0, 1, 0), 130, 'барашек'))
        hu = r.SH - (POST / 2 if xc in grid_x else WC)
        for yy in (YR - hu, YR + hu):
            tr.append(bolt((xc, yy, ZP + D), (0, 0, -1), 80, 'футорка'))
        house.append(('крыша', f'ферма_{k + 1}', tr))
    zr = ZP + r.HK
    cuts_x = [-150] + sorted(x for x in grid_x if POST < x < SX - POST) + [SX + 150]
    n_ = np.array([SIN, COS])
    t_ = np.array([COS, -SIN])
    side_of = {}                                          # x фермы -> (опора южной полуфермы, северной), мировые X
    for k, xc in enumerate(xs):
        x0 = xc - T / 2
        first, last = k == 0, k == len(xs) - 1
        kinds = ('фронтон_0', 'фронтон_25') if first else ('фронтон_25', 'фронтон_0') if last else ('средняя', 'средняя')
        side_of[xc] = ([x0 + purlin_xb(sd) for sd in purlin_sides(kinds[0])],
                       [x0 + T - purlin_xb(sd) for sd in purlin_sides(kinds[1])])
    for a, c in zip(cuts_x[:-1], cuts_x[1:]):
        rb = box(a, c, YR - D, YR + D, zr, zr + 50)
        rp, bolts_ = [], []
        for xc in xs:
            xl = xc - T / 2 - PLY_G - 1 - T
            for xa in (xl, xc + T / 2 + PLY_G + 1):
                if not (a <= xa and xa + T <= c):
                    continue
                bb = box(xa, xa + T, YR - D, YR + D, zr - 50, zr)
                for dy in RIDGE_B:
                    bb = bb - cyl(BH, (xa - 1, YR - dy, zr - 25), (xa + T + 1, YR - dy, zr - 25))
                rp.append(bar('бобышка_конька_25х50х100', '25×50', 100, bb, WOOD2))
            if a <= xl < c:                               # сквозь обе бобышки и стойки полуферм
                for dy in RIDGE_B:
                    bolts_.append(bolt((xl - 5, YR - dy, zr - 25), (1, 0, 0), 130, 'барашек'))
        rp.insert(0, P(rb, f'конёк_50х100х{c - a:.0f}', 'дерево', FRAME))
        CUT[('50×100', round(c - a))] += 1
        house.append(('крыша', 'конёк', rp + bolts_))
    # прогоны плашмя, на каждом пересечении со стропилом — болт М10×80 в опору
    for side in (1, -1):
        y_of = lambda u, s=side: YR - s * u
        for u0 in r.PALL:
            du = PURLIN[1] / 2 * COS
            A, B2 = np.array([u0 - du, r.L2(u0 - du)]), np.array([u0 + du, r.L2(u0 + du)])
            q = [A, B2, B2 + PURLIN[0] * n_, A + PURLIN[0] * n_]
            top = np.array([u0, r.L2(u0)]) + PURLIN[0] * n_
            for a, c in zip(cuts_x[:-1], cuts_x[1:]):
                pr = prism_x([tuple(x) for x in q], a, c, y_of).moved(Location((0, 0, ZP)))
                bolts_ = []
                for xc in xs:
                    xb = [x for x in side_of[xc][0 if side > 0 else 1] if a < x < c]
                    if not xb:
                        continue
                    p0 = np.array([xb[0], y_of(top[0] + 5 * n_[0]), ZP + top[1] + 5 * n_[1]])
                    d = np.array([0, side * n_[0], -n_[1]])
                    pr = pr - cyl(BH, p0, p0 + d * (PURLIN[0] + 10))
                    bolts_.append(bolt(tuple(p0 + d * 5), d, 80, 'барашек'))
                CUT[('25×50', round(c - a))] += 1
                nm = 'прогон_карнизный' if u0 == r.PE else 'прогон'
                house.append(('крыша', 'прогон', [P(pr, f'{nm}_25х50х{c - a:.0f}', 'дерево', (185, 140, 90))] + bolts_))
    # тент: через конёк по прогонам, край завёрнут под карнизный прогон; люверсы — резинками
    TP = 1                                                # толщина тента в модели
    lift = PURLIN[0] / COS + 9                            # над стропилом: прогон + головки болтов
    tz = lambda u: r.L2(u) + lift
    du = PURLIN[1] / 2 * COS
    H0 = r.HK + 50 + 1                                    # по верху конька
    eb = np.array([r.PE + du, r.L2(r.PE + du)])           # наружная нижняя кромка карнизного прогона
    lt = eb + (TP + 1) * t_ + lift * COS * n_             # где край тента загибается вниз
    u1 = r.PU[0] - du
    prof = [(0, H0 + TP), (D, H0 + TP), (u1, tz(u1) + TP), (lt[0] + TP * COS, tz(lt[0]) + TP),
            tuple(eb + (2 * TP + 1) * t_), tuple(eb + (TP + 1) * t_), tuple(lt), (u1, tz(u1)), (D, H0), (0, H0)]
    ties = []

    def ring(y_of, u0, x, outer=0, k=2, th=4, w=8):
        """Резинка через люверс вокруг прогона в точке x (outer — на сколько выступает завёрнутый край)."""
        c = np.array([u0, r.L2(u0)])
        hw, hn = PURLIN[1] / 2, lift * COS + TP
        rect = lambda e: [tuple(c + a * t_ + b_ * n_) for a, b_ in
                          ((-hw - e, -e), (hw + outer + e, -e), (hw + outer + e, hn + e), (-hw - e, hn + e))]
        o = prism_x(rect(k + th), x - w / 2, x + w / 2, y_of) - prism_x(rect(k), x - w / 2 - 1, x + w / 2 + 1, y_of)
        return P(o.moved(Location((0, 0, ZP))), 'резинка_с_шариком', 'сталь', (30, 30, 35))

    for side in (1, -1):
        y_of = lambda u, s=side: YR - s * u
        house.append(('крыша', 'тент', [P(prism_x(prof, -175, SX + 175, y_of).moved(Location((0, 0, ZP))),
                                          'тент', 'фанера', (70, 110, 90))]))
        # по карнизу — через ~0,5 м, в стороне от ферм; на фронтонах — вокруг концов прогонов
        n_e = max(3, round((SX + 260) / 500) + 1)
        for x in np.linspace(-130, SX + 130, n_e):
            if min(abs(x - xc) for xc in xs) < 130:
                x += 150 if x < SX / 2 else -150
            ties.append(ring(y_of, r.PE, x, outer=2 * TP + 1))
        for u0 in r.PU:
            for x in (-130, SX + 130):
                ties.append(ring(y_of, u0, x))
    for x in (-130, SX + 130):                            # вокруг концов конька
        o = box(x - 4, x + 4, YR - D - 6, YR + D + 6, zr - 6, ZP + H0 + TP + 6) - \
            box(x - 5, x + 5, YR - D - 2, YR + D + 2, zr - 2, ZP + H0 + TP + 2)
        ties.append(P(o, 'резинка_с_шариком', 'сталь', (30, 30, 35)))
    house.append(('крыша', 'резинки', ties))
    tw, tl = (SX + 350) / 1000, 2 * (lt[0] + 60) / COS / 1000
    HW[f'Тент тарпаулин ≥ {math.ceil(tw)}×{math.ceil(tl)} м'] += 1
    HW['Люверс 10 мм (поставить в тент)'] += len(ties)
    HW['Резинка с шариком 20 см'] += len(ties)
    return blocks, house, (SX, SY, zr + 50)


# ------------------------------------------------------------------ смета
PRICE_LUMBER = {   # средние цены строймагов РФ, ₽ за штуку (≈ — оценка)
    '25×50': {3000: 250, 4000: 333},
    '50×100': {3000: 598, 4000: 637, 6000: 955},
    '100×100': {3000: 1180, 6000: 2360},
}
PRICE = {'Болт М10×80': 28, 'Болт М10×130': 57, 'Болт М10×150': 54, 'Гайка М10': 6.6,
         'Гайка-барашек М10': 17, 'Шайба М10 увеличенная': 4.6, 'Гайка врезная (футорка) М10': 35,
         'Уголок крепёжный усиленный KUU 90×90×40': 46, 'Арматура Ø12 (кол 1 м)': 80,
         'Люверс 10 мм (поставить в тент)': 6, 'Резинка с шариком 20 см': 20, 'Петля карточная 100 мм': 160,
         'Ручка-скоба дверная': 140, 'Шпингалет накладной': 93}
FSF3, FK9, TENT_M2, CONSUM_3x3 = 370, 885, 96.5, 5940


def pack(items, stock, kerf=4):
    bars = []
    for L in sorted(items, reverse=True):
        for bar_ in bars:
            if bar_[0] >= L + kerf:
                bar_[0] -= L + kerf
                break
        else:
            S = min(x for x in stock if x >= L)
            bars.append([S - L - kerf, S])
    return collections.Counter(x[1] for x in bars)


def lumber_buy():
    out = {}
    for sec, prices in PRICE_LUMBER.items():
        items = [ln for (sc, ln), n in CUT.items() if sc == sec for _ in range(n)]
        if not items:
            continue
        best = None
        stocks = sorted(prices)
        for k in range(1, len(stocks) + 1):
            for combo in [stocks[:k], stocks[-k:]]:
                if max(items) > max(combo):
                    continue
                c = pack(items, combo)
                cost = sum(prices[L] * n for L, n in c.items())
                if best is None or cost < best[0]:
                    best = (cost, c)
        out[sec] = best
    return out


def bom(name, cfg, blocks, house, dims, out):
    hw = collections.Counter()
    for k, n in HW.items():
        key = (k.replace(' (DIN 933, оцинк.)', '').replace(' увеличенная (DIN 9021)', ' увеличенная'))
        hw[key] += n
    area = lambda pred: sum(q.solid.volume for g_, b_, parts in house for q in parts if pred(q)) 
    gable_m2 = area(lambda q: 'фронтона' in q.name) / PLY / 1e6
    gus_m2 = area(lambda q: q.name.startswith('косынка')) / PLY_G / 1e6
    n_spans = sum(1 for g_, b_, _ in house if b_.startswith('пролёт_'))
    n_doors = sum(1 for g_, b_, _ in house if b_.startswith('пролёт_дверь'))
    sheets3 = 3 * n_spans + n_doors + math.ceil(gable_m2 * 1.3 / 2.977)
    sheets9 = max(1, math.ceil(gus_m2 * 1.4 / 2.326))
    buy = lumber_buy()
    lum_m = sum(ln * n for (sc, ln), n in CUT.items()) / 1000
    consum = CONSUM_3x3 * lum_m / 175
    tent_name = next(k for k in hw if k.startswith('Тент'))
    tw, tl = [float(x) for x in tent_name.split('≥ ')[1].split(' м')[0].split('×')]
    L = [f'# Дом {name} — спецификация и смета', '',
         f'Габарит каркаса {dims[0] / 1000:.1f} × {dims[1] / 1000:.1f} м, высота до конька {dims[2] / 1000:.2f} м. '
         'Сгенерировано `tools/grid_house.py`. Цены — средние по строймагам РФ, октябрь 2026 '
         '(см. `step/5/СТОИМОСТЬ.md`), ≈ — оценка.', '',
         '## Блоки', '', '| Блок | Шт. |', '|---|---|']
    cnt = collections.Counter()
    for g_, b_, _ in house:
        k = b_.rsplit('_', 1)[0] if b_[:5] in ('стойк', 'лежен', 'обвяз', 'ферма') else b_
        k = 'пролёт ' + b_.split('_')[1] if b_.startswith('пролёт_') else k
        if k.startswith(('стойка', 'лежень', 'обвязка', 'пролёт', 'ферма', 'конёк', 'прогон')):
            cnt[k] += 1
    for k, n in cnt.items():
        L.append(f'| {k} | {n} |')
    L += ['', '## Смета', '', '| Позиция | Кол-во | Цена, ₽ | Сумма, ₽ |', '|---|---|---|---|']
    total = collections.Counter()
    for sec, (cost, c) in buy.items():
        for ln, n in sorted(c.items()):
            pr = PRICE_LUMBER[sec][ln]
            L.append(f'| Брус/брусок {sec}×{ln} | {n} шт | {"≈ " if (sec, ln) in (("25×50", 3000), ("25×50", 4000), ("50×100", 4000)) else ""}{pr} | {pr * n:,.0f} |')
            total['Пиломатериалы'] += pr * n
    L.append(f'| Фанера ФСФ 3 мм 1220×2440 | {sheets3} листов | ≈ {FSF3} | {FSF3 * sheets3:,.0f} |')
    L.append(f'| Фанера ФК 9 мм 1525×1525 (косынки) | {sheets9} | {FK9} | {FK9 * sheets9:,.0f} |')
    total['Фанера'] += FSF3 * sheets3 + FK9 * sheets9
    for k, n in sorted(hw.items()):
        if k.startswith('Тент'):
            pr = TENT_M2 * tw * tl
            L.append(f'| {k} | 1 | ≈ {pr:,.0f} | {pr:,.0f} |')
            total['Прочее'] += pr
            continue
        pr = PRICE.get(k)
        if pr is None:
            continue
        q = math.ceil(n * 1.1) if k.startswith(('Болт', 'Гайка', 'Шайба')) else n
        unit = 'м' if 'Арматура' in k else 'шт'
        L.append(f'| {k} | {q} {unit} | {pr} | {pr * q:,.0f} |')
        total['Крепёж' if k.startswith(('Болт', 'Гайка', 'Шайба', 'Уголок')) else 'Прочее'] += pr * q
    L.append(f'| Саморезы, клей D3, антисептик | | ≈ | {consum:,.0f} |')
    total['Прочее'] += consum
    s = sum(total.values())
    L += ['', '| Группа | ₽ |', '|---|---|'] + [f'| {k} | {v:,.0f} |' for k, v in total.items()]
    L += [f'| **Итого** | **≈ {s:,.0f}** |', f'| С запасом 10 % | ≈ {s * 1.1:,.0f} |', '',
          'Метизы — с запасом 10 %. Пиломатериал — в магазинных длинах, раскрой из модели с пропилом 4 мм.', '']
    L += ['## Раскрой', '', '| Сечение | Длина, мм | Шт. |', '|---|---|---|']
    for (sc, ln), n in sorted(CUT.items(), key=lambda t: (t[0][0], -t[0][1])):
        L.append(f'| {sc} | {ln} | {n} |')
    total_mass = sum(q.mass() for g_, b_, parts in house for q in parts if q.name != 'тент')
    L += ['', f'Масса без тента ≈ {total_mass:.0f} кг.', '']
    txt = '\n'.join(L)
    txt = re.sub(r'(?<=\d),(?=\d{3})', ' ', txt)       # 12,345 -> 12 345
    open(f'{out}/СПЕЦИФИКАЦИЯ_И_СМЕТА.md', 'w').write(txt)
    return s, total_mass


LETTER = {'окно': 'О', 'глухой': 'Г', 'дверь': 'Д'}


def ascii_plan(cfg):
    """План сверху: ■ стойки, буквы — пролёты (О окно, Г глухой, Д дверь), · — открытый проём."""
    NX, NY, w = cfg['NX'], cfg['NY'], 12
    rows = []
    for j in range(NY, -1, -1):
        line = ''
        for i in range(NX):
            k = cfg['S'][i] if j == 0 else cfg['N'][NX - 1 - i] if j == NY else None
            mid = LETTER[k] if k else '·'
            line += '■' + '─' * (w // 2 - 1) + mid + '─' * (w // 2 - 1)
        rows.append(line + '■')
        if j > 0:
            for r_ in range(3):
                line = ''
                for i in range(NX + 1):
                    k = cfg['W'][NY - j] if i == 0 else cfg['E'][j - 1] if i == NX else None
                    ch = (LETTER[k] if k else '·') if r_ == 1 else '│'
                    line += ch + (' ' * (w - 1) if i < NX else '')
                rows.append(line)
    return '\n'.join(rows)


T_MIN = dict(setup=10, post=3, lez=3, beam=4, span=6, truss_m=5, truss_b=8, ridge_bay=4, roof_bolt=0.5, tent_bay=6, tie=0.3)


def assembly(name, cfg, house, dims, out):
    NX, NY = cfg['NX'], cfg['NY']
    cnt = collections.Counter()
    bolts = collections.Counter()
    for gr, b_, parts in house:
        for k in ('стойка', 'лежень', 'обвязка', 'ферма', 'конёк', 'прогон'):
            if b_.startswith(k):
                cnt[k] += 1
        if b_.startswith('пролёт_'):
            cnt['пролёт ' + b_.split('_')[1]] += 1
            continue                                   # болты внутри пролёта — мастерская
        for q in parts:
            if q.name.startswith('болт'):
                bolts[(gr if not b_.startswith('ферма') else 'крыша', q.name.split('_')[1])] += 1
    x_beams = NX * (NY + 1)
    y_beams = (NX + 1) * NY
    trusses = cnt['ферма']
    big = NY == 2
    t = collections.OrderedDict()
    t['Раскладка, разметка'] = T_MIN['setup']
    t['Лежни'] = T_MIN['lez'] * cnt['лежень']
    t['Стойки (+ колья)'] = T_MIN['post'] * cnt['стойка'] + 5
    t['Верхняя обвязка'] = T_MIN['beam'] * cnt['обвязка']
    t['Пролёты'] = T_MIN['span'] * sum(v for k, v in cnt.items() if k.startswith('пролёт'))
    t['Фермы'] = (T_MIN['truss_b'] if big else T_MIN['truss_m']) * trusses
    roof_bolts = sum(1 for _, b_, parts in house if b_ in ('конёк', 'прогон') for q in parts if q.name.startswith('болт'))
    ties = sum(len(parts) for _, b_, parts in house if b_ == 'резинки')
    t['Конёк, прогоны'] = T_MIN['ridge_bay'] * NX + round(T_MIN['roof_bolt'] * roof_bolts)
    t['Тент, резинки'] = T_MIN['tent_bay'] * NX + 3 + round(T_MIN['tie'] * ties)
    total = sum(t.values())
    spans = ', '.join(f'{v} × «{k.split()[1]}»' for k, v in cnt.items() if k.startswith('пролёт'))
    L = [f'# Сборка дома {name}', '',
         f'![Дом {name}](img/дом.png)', '',
         f'Каркас {dims[0] / 1000:.1f} × {dims[1] / 1000:.1f} м, высота до конька {dims[2] / 1000:.2f} м. '
         f'Сетка {NX} × {NY} клеток. Общие правила и описание каждой детали — '
         '[../МОНТАЖ.md](../МОНТАЖ.md) и [../ДЕТАЛИ.md](../ДЕТАЛИ.md). '
         'Что купить и сколько стоит — [СПЕЦИФИКАЦИЯ_И_СМЕТА.md](СПЕЦИФИКАЦИЯ_И_СМЕТА.md).', '',
         '## План', '', 'Вид сверху, север — сверху, конёк — вдоль длинной стороны (слева направо). '
         '■ — стойка; О — пролёт с окном, Г — глухой, Д — с дверью, · — открытый проём.', '',
         '```', ascii_plan(cfg), '```', '',
         '## Комплект', '', '| Что | Шт. |', '|---|---|',
         f'| Стойки | {cnt["стойка"]} |', f'| Лежни | {cnt["лежень"]} |',
         f'| Верхние обвязки | {cnt["обвязка"]} (вдоль конька — {x_beams}, поперёк — {y_beams}, перевёрнутые) |',
         f'| Пролёты | {spans} |',
         f'| Фермы ({"большие" if big else "малые"}) | {trusses}: 2 фронтонные (А+Б), {trusses - 2} средних |',
         f'| Конёк / прогоны | {cnt["конёк"]} / {cnt["прогон"]} куск. |',
         '', '## Порядок', '']
    steps = [
        ('шаг1_каркас', f'**Лежни и стойки.** Разложить {cnt["лежень"]} лежней по плану (уголками внутрь клеток), '
                        f'выровнять подкладками. Ставить стойки от угла: каждая — между концами лежней, болты '
                        f'М10×130 сквозь стойку в уголки ({bolts[("основание", "М10х130")]} шт.). Диагонали каждой клетки равны (≈ 4525). Колья — в лежни по периметру.'),
        (None, f'**Верхняя обвязка.** {x_beams} обвязок вдоль конька — уголками вниз; {y_beams} поперёк — '
               f'перевернуть (уголками вверх). Болт М10×130 сквозь стойку на каждый конец ({bolts[("каркас", "М10х130")]} шт.; в середине стены и в '
               'центре один болт держит два уголка).'),
        ('шаг2_пролёты', f'**Пролёты** ({spans}) — по плану: на лежень между стойками, 4 болта М10×150 сквозь '
                         'стойки (барашки изнутри) + 2 болта М10×80 изнутри снизу в футорки обвязки.'),
        ('шаг3_фермы', f'**Фермы** ({trusses} шт.): пары полуферм на земле, болт М10×130 с барашком. Крайние — над '
                       'торцами (фанерой наружу), остальные через 1,55 м. Пяты — болтами М10×80 в футорки: на линиях '
                       'стоек — в верх стоек, между ними — в середину обвязок.' + (
                           ' Большие фермы поднимать втроём; средняя линия стоек держит их под коньком.' if big else '')),
        ('шаг4_крыша', f'**Конёк** ({cnt["конёк"]} куск.) на верх ферм — бобышками по бокам; на каждой ферме '
                       f'2 болта М10×130 сквозь бобышки и стойки полуферм. **Прогоны** ({cnt["прогон"]} куск., '
                       f'нижние — карнизные) — плашмя поперёк стропил, на каждом пересечении болт М10×80 сверху '
                       f'сквозь прогон в опору стропила, барашек снизу ({roof_bolts - 2 * trusses} шт.). '
                       f'**Тент** через конёк, край завернуть под карнизный прогон; через люверсы — резинки с шариком '
                       f'вокруг карнизного прогона и концов прогонов и конька ({ties} шт.).'),
    ]
    for i, (img, txt) in enumerate(steps, 1):
        L.append(f'{i}. {txt}')
        if img:
            L += ['', f'   ![]({"img/" + img}.png)', '']
    L += ['', '## Болты на площадке', '', '| Болт | Где | Шт. |', '|---|---|---|']
    where = {'основание': 'уголки лежней (низ стоек)', 'каркас': 'уголки обвязок (верх стоек)', 'пролёты': 'пролёты к стойкам и обвязке', 'крыша': 'фермы, конёк, прогоны'}
    for (gr, k), n in sorted(bolts.items()):
        L.append(f'| {k.replace("х", "×")} | {where.get(gr, gr)} | {n} |')
    L += [f'| | **всего** | **{sum(bolts.values())}** |', '',
          '## Время (2 человека, оценка)', '', '| Этап | Мин |', '|---|---|']
    L += [f'| {k} | {v} |' for k, v in t.items()]
    L += [f'| **Итого** | **≈ {total} ({total / 60:.1f} ч)** |', '',
          'Время — оценка по нормам на операцию, вживую не проверено. Втроём — примерно на треть быстрее.', '',
          '## Разборка', '', 'Обратный порядок: резинки, тент → прогоны, конёк → фермы (разобрать на полуфермы) → '
          'пролёты → обвязка → стойки → колья, лежни.', '']
    open(f'{out}/СБОРКА.md', 'w').write('\n'.join(L))
    return total


def export(name, out):
    cfg = CONFIGS[name]
    blocks, house, dims = build(cfg)
    os.makedirs(out, exist_ok=True)
    groups = collections.OrderedDict()
    for g_, b_, parts in house:
        groups.setdefault(g_, []).append(compound(parts, b_))
    top = Compound(children=[Compound(children=v, label=k) for k, v in groups.items()])
    top.label = f'дом_{name}'
    save_step(top, f'{out}/дом_{name}.step')
    cost, mass = bom(name, cfg, blocks, house, dims, out)
    minutes = assembly(name, cfg, house, dims, out)
    return blocks, house, dims, cost, mass, minutes


if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    blocks, house, dims, cost, mass, minutes = export(name, out)
    print(name, [round(x) for x in dims], f'{cost:,.0f} ₽', f'{mass:.0f} кг', f'{minutes} мин')
    if len(sys.argv) > 3:          # блоки — один раз для системы
        os.makedirs(sys.argv[3], exist_ok=True)
        for k, parts in blocks.items():
            save_step(compound(parts, k), f'{sys.argv[3]}/{k}.step')
