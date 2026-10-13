"""Крыша: полуфермы, фермы, конёк, прогоны, тент на резинках.

Двускатная, конёк вдоль X. NY = 1 — малые полуфермы (пролёт 3,2 м),
NY = 2 — большие (пролёт 6,3 м, бабка, опора на среднюю линию стоек).
"""
import math
import numpy as np
from build123d import Location

from .dims import T, D, PLY, PLY_G, POST, OPEN, PITCH, ZP, WC, BH, TAN, COS, SIN, PURLIN, RIDGE_B
from .geom import P, box, cyl, prism_x, place, WOOD, WOOD2, PLYC, FRAME
from .tally import CUT, HW, bar, bolt


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


def roof(NX, NY, SX, SY, blk):
    """Фермы, конёк, прогоны, тент и резинки дома NX × NY. blk(имя, детали) — учёт блоков."""
    house = []
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
    return house, zr + 50
