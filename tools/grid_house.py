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
from sw2step import save_step

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


def beam(d, eave_mid):
    """Верхняя обвязка между стойками, на ребро."""
    bb = box(2, 2 + BL, 0, BEAM[0], ZB, ZP)
    parts = []
    for s in (GAP + PW / 2, GAP + 2.5 * PW):
        bb = bb - cyl(14, (s, SPAN_O, ZB - 1), (s, SPAN_O, ZB + 46))
        t = cyl(14, (s, SPAN_O, ZB), (s, SPAN_O, ZB + 25)) - cyl(10.5, (s, SPAN_O, ZB - 1), (s, SPAN_O, ZB + 26))
        parts.append(P(t, 'футорка_М10', 'сталь', (150, 150, 60)))
        HW['Гайка врезная (футорка) М10'] += 1
    # футорка сверху посередине — под пяту промежуточной фермы (сверлится во всех обвязках)
    bb = bb - cyl(14, (OPEN / 2, WC, ZP - 36), (OPEN / 2, WC, ZP + 1))
    parts.append(futorka(OPEN / 2, WC, ZP))
    for right in (False, True):
        parts.append(angle('верх', Z_ANG[d][1] - 20, TOP_O, Z_ANG[d][1], right))
    CUT[('50×100', BL)] += 1
    return [P(bb, f'обвязка_50х100х{BL}', 'дерево', FRAME)] + parts


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


def half_truss(r, kind):
    """Полуферма: X — толщина 0..25, Y = -u (u от конька), Z от низа затяжки."""
    p, L1, L2, HK = [], r.L1, r.L2, r.HK
    chord = prism_x([(0, 0), (r.CL, 0), (r.CL, D), (0, D)], 0, T)
    for hu in (r.SH - POST / 2, r.SH - WC):              # пята на стойке / на обвязке
        chord = chord - cyl(BH, (T / 2, -hu, -1), (T / 2, -hu, D + 1))
    p.append(bar(f'затяжка_25х50х{r.CL}', '25×50', r.CL, chord, WOOD))
    pst = prism_x([(0, D), (D, D), (D, HK), (0, HK)], 0, T)
    pst = pst - cyl(BH, (T / 2, 1, (D + HK) / 2), (T / 2, -D - 1, (D + HK) / 2))
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
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for u0 in r.PU:
        B = np.array([u0 + 12.5 * COS, L2(u0 + 12.5 * COS)])
        q = [B, B + 25 * t_, B + 25 * t_ + 30 * n_, B + 30 * n_]
        p.append(bar('лапка_прогона_25х25х30', '25×25', 30, prism_x([tuple(x) for x in q], 0, T), WOOD2, cut=False))
    CUT[('25×50', 50)] += len(r.PU)
    sides = {'средняя': [(-PLY_G, 0), (T, T + PLY_G)], 'фронтон_0': [(T, T + PLY_G)], 'фронтон_25': [(-PLY_G, 0)]}[kind]
    for x0, x1 in sides:
        for g, pts in gus.items():
            p.append(P(prism_x(pts, x0, x1), f'косынка_фанера_{PLY_G}', 'фанера', (240, 220, 175)))
    if kind != 'средняя':
        x0, x1 = (-PLY, 0) if kind == 'фронтон_0' else (T, T + PLY)
        e = r.SH + PLY
        p.append(P(prism_x([(0, 0), (e, 0), (e, L2(e)), (D, HK), (0, HK)], x0, x1), f'обшивка_фронтона_ФСФ_{PLY}', 'фанера', PLYC))
    return p


ROOFS = {1: Roof(1600, 1700, 1980, (650, 1320), ()),
         2: Roof(3150, 3250, 3530, (700, 1400, 2100, 2800), (1900,))}


# ------------------------------------------------------------------ дом
CONFIGS = {
    # стороны: S, N — вдоль X (по ячейкам слева направо), W, E — вдоль Y (снизу вверх)
    '3х3': dict(NX=1, NY=1, S=['окно'], N=['окно'], W=['дверь'], E=['окно']),
    '6х6': dict(NX=2, NY=2, S=['окно', 'окно'], N=['окно', 'окно'], W=['дверь', 'глухой'], E=['окно', 'глухой']),
    '3х6': dict(NX=2, NY=1, S=['окно', 'окно'], N=['глухой', 'окно'], W=['дверь'], E=['окно']),
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
                house.append(('каркас', f'болт_уголка_{nm}_{end_s}',
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
    for a, c in zip(cuts_x[:-1], cuts_x[1:]):
        rp = [P(box(a, c, YR - D, YR + D, zr, zr + 50), f'конёк_50х100х{c - a:.0f}', 'дерево', FRAME)]
        for xc in xs:
            for xa in (xc - T / 2 - PLY_G - 1 - T, xc + T / 2 + PLY_G + 1):
                if a <= xa and xa + T <= c:
                    rp.append(bar('бобышка_конька_25х50х100', '25×50', 100, box(xa, xa + T, YR - D, YR + D, zr - 50, zr), WOOD2))
        CUT[('50×100', round(c - a))] += 1
        house.append(('крыша', 'конёк', rp))
    n_ = np.array([SIN, COS])
    for side in (1, -1):
        for u0 in r.PU:
            du = 12.5 * COS
            A, B2 = np.array([u0 - du, r.L2(u0 - du)]), np.array([u0 + du, r.L2(u0 + du)])
            q = [A, B2, B2 + 50 * n_, A + 50 * n_]
            for a, c in zip(cuts_x[:-1], cuts_x[1:]):
                pr = prism_x([tuple(x) for x in q], a, c, lambda u, s=side: YR - s * u).moved(Location((0, 0, ZP)))
                CUT[('25×50', round(c - a))] += 1
                house.append(('крыша', 'прогон', [P(pr, f'прогон_25х50х{c - a:.0f}', 'дерево', (185, 140, 90))]))
        top = lambda u: r.L2(u) + 50 / COS + 1
        q = [(0, top(0)), (r.TU + 50, top(r.TU + 50)), (r.TU + 50, top(r.TU + 50) + 1), (0, top(0) + 1)]
        tent = prism_x(q, -175, SX + 175, lambda u, s=side: YR - s * u).moved(Location((0, 0, ZP)))
        house.append(('крыша', 'тент', [P(tent, 'тент', 'фанера', (70, 110, 90))]))
    tw, tl = (SX + 350) / 1000, 2 * (r.TU + 50) / COS / 1000
    HW[f'Тент тарпаулин ≥ {math.ceil(tw)}×{math.ceil(tl)} м'] += 1
    HW['Ремень стяжной с храповиком 6 м'] += 2 * max(1, NX)
    for k in ('глухой', 'окно', 'дверь'):
        pass
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
         'Ремень стяжной с храповиком 6 м': 510, 'Петля карточная 100 мм': 160,
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
    return blocks, house, dims, cost, mass


if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    blocks, house, dims, cost, mass = export(name, out)
    print(name, [round(x) for x in dims], f'{cost:,.0f} ₽', f'{mass:.0f} кг')
    if len(sys.argv) > 3:          # блоки — один раз для системы
        os.makedirs(sys.argv[3], exist_ok=True)
        for k, parts in blocks.items():
            save_step(compound(parts, k), f'{sys.argv[3]}/{k}.step')
