"""Дом 3×3, версия 5: каркас + пролёты стен + фермы.

Иерархия сборки:
  щиты 997×2400 (глухой, окно, дверь)  — мастерская, неразборные
  пролёты стен = 3 щита на болтах        — собираются заранее
  каркас: лежни, 4 угловые стойки, 4 ригеля — на площадке, на штырях
  пролёты вставляются в проёмы каркаса снаружи и запираются вертушками
  сверху: 3 фермы (по 2 полуфермы), конёк, прогоны, тент.

Система координат: X — вдоль конька, Y — поперёк, Z — вверх, мм.
Запуск:  python tools/v5_house.py step/5
"""
import collections, math, os, sys
import numpy as np
from build123d import (Box, Compound, Cylinder, Face, Location, Vector, Wire,
                       Axis, Align, extrude)

sys.path.insert(0, os.path.dirname(__file__))
from sw2step import save_step

MIN = (Align.MIN, Align.MIN, Align.MIN)

# ------------------------------------------------------------------ параметры
PW, H = 997, 2400            # щит (997 — зазор 4,5 мм на сторону в проёме 3000)
T, D = 25, 50                # брус 25×50
PLY = 3                      # фанера обшивки (ФСФ 3 мм, лист 1220×2440)
PLY_G = 9                    # фанера косынок
SD = D + PLY                 # толщина пролёта
POST = 100                   # угловая стойка 100×100
OPEN = 3000                  # проём между стойками
SIZE = OPEN + 2 * POST       # 3200 — габарит каркаса
LEZ = 50                     # лежень 50×100 плашмя (высота 50)
BEAM = (50, 100)             # ригель 50×100 на ребро
Z0 = LEZ                     # низ пролёта = верх лежня
ZB = Z0 + H + 10             # низ ригеля (зазор 10 над пролётом)
ZP = ZB + BEAM[1]            # верх ригеля = низ затяжек
SPAN_L = 3 * PW              # 2991
GAP = (OPEN - SPAN_L) / 2
WC = 25                      # ось ригеля от наружной грани (штыри пят)

ALPHA = math.radians(17.6)
TAN, COS, SIN = math.tan(ALPHA), math.cos(ALPHA), math.sin(ALPHA)
SPAN_HALF = SIZE / 2         # 1600
CHORD_L = 1700
TAIL_U = 1980                # свес ≈ 380
HEEL_U = SPAN_HALF - WC      # 1575
PURLIN_U = (650, 1320)
OVH = 150

DENS = {'дерево': 500e-9, 'фанера': 600e-9, 'сталь': 7850e-9}

CUT = collections.Counter()
HW = collections.Counter()


class P:
    def __init__(self, solid, name, mat='дерево', color=(214, 176, 128)):
        self.solid, self.name, self.mat, self.color = solid, name, mat, color

    def mass(self):
        return self.solid.volume * DENS[self.mat]


def box(x0, x1, y0, y1, z0, z1):
    return Box(x1 - x0, y1 - y0, z1 - z0, align=MIN).moved(Location((x0, y0, z0)))


def cyl(d, p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    c = Cylinder(d / 2, np.linalg.norm(v), align=(Align.CENTER, Align.CENTER, Align.MIN))
    ax = np.argmax(np.abs(v))
    if ax == 0:
        c = c.rotate(Axis.Y, 90 if v[0] > 0 else -90)
    elif ax == 1:
        c = c.rotate(Axis.X, -90 if v[1] > 0 else 90)
    elif v[2] < 0:
        c = c.rotate(Axis.X, 180)
    return c.moved(Location(tuple(p0)))


def prism_x(pts_uz, x0, x1, y_of_u=lambda u: -u):
    f = Face(Wire.make_polygon([Vector(x0, y_of_u(u), z) for u, z in pts_uz], close=True))
    return extrude(f, amount=x1 - x0, dir=(1, 0, 0))


def bar(name, sec, length, solid, color=(214, 176, 128), cut=True):
    if cut:
        CUT[(sec, round(length))] += 1
    return P(solid, name, 'дерево', color)


BH = 11                      # отверстие под болт М10


def bolt(p0, d, L, nut):
    """Болт М10×L: головка в p0, стержень по направлению d. nut: гайка | барашек | футорка."""
    p0, d = np.array(p0, float), np.array(d, float) / np.linalg.norm(d)
    HW[f'Болт М10×{L} (DIN 933, оцинк.)'] += 1
    HW['Шайба М10 увеличенная (DIN 9021)'] += 1 if nut == 'футорка' else 2
    if nut == 'барашек':
        HW['Гайка-барашек М10'] += 1
    elif nut == 'гайка':
        HW['Гайка М10'] += 1
    return P(cyl(10, p0, p0 + d * L), f'болт_М10х{L}', 'сталь', (60, 60, 60))


def futorka(x, y, z_top, depth=25):
    """Врезная гайка М10 (футорка) — трубка Ø14 в дереве, сверху вниз."""
    HW['Гайка врезная (футорка) М10'] += 1
    t = cyl(14, (x, y, z_top - depth), (x, y, z_top)) - cyl(10.5, (x, y, z_top - depth - 1), (x, y, z_top + 1))
    return P(t, 'футорка_М10', 'сталь', (150, 150, 60))


def steel(solid, name, color=(70, 70, 80)):
    return P(solid, name, 'сталь', color)


WOOD, WOOD2, PLYC = (222, 184, 135), (196, 152, 104), (236, 214, 170)
FRAME = (150, 105, 65)
BOLT_Z = (300, 1000, 1700)   # болты щит-щит в пролёте
END_Z = (600, 700, 1800, 1900)   # болты пролёт-стойка (600/1800 — левый край, 700/1900 — правый)


# ------------------------------------------------------------------ щиты
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


# ------------------------------------------------------------------ каркас
# Узел «брус к стойке»: стальной уголок 90×90×40, одна полка прикручена к брусу
# (лежню или верхней обвязке), другая — к грани стойки болтом М10×130 сквозь стойку.
# Болты левого конца стены идут по оси x стойки, правого — по y (на разной высоте).
PL = ZP                      # стойка от земли до верха обвязки
BOT_Z = (80, 115)            # болты уголков лежней: левый конец / правый
TOP_Z = (ZB + 25, ZB + 75)   # болты уголков верхней обвязки (уголки на разной высоте)
ANG_O = (57, 97)             # уголок лежня по глубине (за пролётом)
SPAN_O = SD / 2 + PLY / 2    # 29 — ось болтов пролёта


def post():
    """Угловая стойка 100×100 в своих координатах: наружные грани x=0, y=0; z=0 — земля."""
    b = box(0, POST, 0, POST, 0, PL)
    holes = [((-1, 77, BOT_Z[0]), (POST + 1, 77, BOT_Z[0])), ((77, -1, BOT_Z[1]), (77, POST + 1, BOT_Z[1])),
             ((-1, 75, TOP_Z[0]), (POST + 1, 75, TOP_Z[0])), ((75, -1, TOP_Z[1]), (75, POST + 1, TOP_Z[1]))]
    for z in (650, 1850):
        holes.append(((-1, SPAN_O, z), (POST + 1, SPAN_O, z)))
    for z in (750, 1950):
        holes.append(((SPAN_O, -1, z), (SPAN_O, POST + 1, z)))
    for p0, p1 in holes:
        b = b - cyl(BH, p0, p1)
    b = b - cyl(14, (WC, WC, PL - 36), (WC, WC, PL + 1))                  # футорка под пяту фермы
    return [bar(f'стойка_угловая_100х100х{PL}', '100×100', PL, b, FRAME), futorka(WC, WC, PL)]


def angle(s0, o0, o1, z0, kind):
    """Уголок 90×90×40 (3 мм) у грани стойки s=0. kind: 'низ' — полка на брусе сверху,
    'верх' — полка на внутренней грани обвязки."""
    HW['Уголок крепёжный усиленный 90×90×40'] += 1
    if kind == 'низ':
        u = box(0, 3, o0, o1, z0, z0 + 90) + box(0, 90, o0, o1, z0, z0 + 3)
    else:
        u = box(0, 3, BEAM[0], BEAM[0] + 90, z0, z0 + 40) + box(0, 90, BEAM[0], BEAM[0] + 3, z0, z0 + 40)
    return P(u.moved(Location((s0, 0, 0))), 'уголок_90х90х40', 'сталь', (90, 90, 100))


def mirror_s(parts, L):
    """Отразить детали вдоль s (для уголка на правом конце бруса длиной L)."""
    from build123d import Plane, mirror
    return [P(mirror(q.solid, Plane.YZ).moved(Location((L, 0, 0))), q.name, q.mat, q.color) for q in parts]


def frame_bolts():
    """Болты уголков к стойке, в координатах стойки (head — снаружи, наружу x=0 / y=0)."""
    return [bolt((0, 77, BOT_Z[0]), (1, 0, 0), 130, 'барашек'), bolt((77, 0, BOT_Z[1]), (0, 1, 0), 130, 'барашек'),
            bolt((0, 75, TOP_Z[0]), (1, 0, 0), 130, 'барашек'), bolt((75, 0, TOP_Z[1]), (0, 1, 0), 130, 'барашек')]


def span_bolts():
    """Болты пролётов к стойке (в координатах стойки): по x — 650/1850, по y — 750/1950."""
    return ([bolt((0, SPAN_O, z), (1, 0, 0), 150, 'барашек') for z in (650, 1850)] +
            [bolt((SPAN_O, 0, z), (0, 1, 0), 150, 'барашек') for z in (750, 1950)])


BL = OPEN - 4                # лежень и обвязка между стойками, зазор 2 мм


def lezhen():
    """Лежень 50×100 между стойками: s от грани левой стойки, o от наружной грани."""
    b = box(2, 2 + BL, 0, 100, 0, LEZ)
    parts = []
    for s in (500, OPEN - 500):
        b = b - cyl(14, (s, 77, -1), (s, 77, LEZ + 1))
        parts.append(steel(cyl(12, (s, 77, LEZ - 1000), (s, 77, LEZ)), 'арматура_12х1000'))
        HW['Арматура Ø12 А500С, пруток 1 м (кол)'] += 1
    for k, z in ((0, BOT_Z[0]), (1, BOT_Z[1])):
        a = [angle(0, *ANG_O, LEZ, 'низ')]
        a[0].solid = a[0].solid - cyl(BH, (-1, 77, z), (4, 77, z))
        parts += a if k == 0 else mirror_s(a, OPEN)
    CUT[('50×100', BL)] += 1
    parts.insert(0, P(b, f'лежень_50х100х{BL}', 'дерево', FRAME))
    return parts


def beam(eave):
    """Верхняя обвязка 50×100 между стойками, на ребро."""
    b = box(2, 2 + BL, 0, BEAM[0], ZB, ZP)
    parts = []
    for s in (GAP + PW / 2, GAP + 2.5 * PW):             # футорки снизу — болты пролёта
        b = b - cyl(14, (s, SPAN_O, ZB - 1), (s, SPAN_O, ZB + 46))
        t = cyl(14, (s, SPAN_O, ZB), (s, SPAN_O, ZB + 25)) - cyl(10.5, (s, SPAN_O, ZB - 1), (s, SPAN_O, ZB + 26))
        parts.append(P(t, 'футорка_М10', 'сталь', (150, 150, 60)))
        HW['Гайка врезная (футорка) М10'] += 1
    if eave:                                            # футорка сверху — пята средней фермы
        b = b - cyl(14, (OPEN / 2, WC, ZP - 36), (OPEN / 2, WC, ZP + 1))
        parts.append(futorka(OPEN / 2, WC, ZP))
    for k, z in ((0, TOP_Z[0]), (1, TOP_Z[1])):
        a = [angle(0, 0, 0, z - 20, 'верх')]
        a[0].solid = a[0].solid - cyl(BH, (-1, 75, z), (4, 75, z))
        parts += a if k == 0 else mirror_s(a, OPEN)
    CUT[('50×100', BL)] += 1
    parts.insert(0, P(b, f'обвязка_верхняя_{"карнизная" if eave else "фронтонная"}_50х100х{BL}', 'дерево', FRAME))
    return parts


# ------------------------------------------------------------------ полуфермы
def L1(u):
    return D + (CHORD_L - u) * TAN


def L2(u):
    return L1(u) + D / COS


HK = L2(D)


def half_truss(kind):
    p = []
    chord = prism_x([(0, 0), (CHORD_L, 0), (CHORD_L, D), (0, D)], 0, T)
    chord = chord - cyl(BH, (T / 2, -HEEL_U, -1), (T / 2, -HEEL_U, D + 1))
    p.append(bar(f'затяжка_25х50х{CHORD_L}', '25×50', CHORD_L, chord, WOOD))
    pst = prism_x([(0, D), (D, D), (D, HK), (0, HK)], 0, T)
    zb = (D + HK) / 2
    pst = pst - cyl(BH, (T / 2, 1, zb), (T / 2, -D - 1, zb))
    p.append(bar(f'стойка_фермы_25х50х{HK - D:.0f}', '25×50', HK - D, pst, WOOD2))
    raf_len = (TAIL_U - D) / COS
    p.append(bar(f'стропило_25х50х{raf_len:.0f}', '25×50', raf_len,
                 prism_x([(D, L1(D)), (TAIL_U, L1(TAIL_U)), (TAIL_U, L2(TAIL_U)), (D, L2(D))], 0, T), (205, 160, 110)))

    def hit(u0, z0):
        s = (D + CHORD_L * TAN - z0 - u0 * TAN) / (1 + TAN)
        return (u0 + s, z0 + s)
    a, b = (D + D * math.sqrt(2), D), (D, D + D * math.sqrt(2))
    br_len = math.dist(a, hit(*a))
    p.append(bar(f'подкос_25х50х{br_len:.0f}', '25×50', br_len, prism_x([(D, D), a, hit(*a), hit(*b), b], 0, T), (165, 115, 70)))
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for u0 in PURLIN_U:
        B = np.array([u0 + 12.5 * COS, L2(u0 + 12.5 * COS)])
        q = [B, B + 25 * t_, B + 25 * t_ + 30 * n_, B + 30 * n_]
        p.append(bar('лапка_прогона_25х25х30', '25×25', 30, prism_x([tuple(x) for x in q], 0, T), WOOD2, cut=False))
    CUT[('25×50', 50)] += len(PURLIN_U)
    gus = {
        'вершина': [(0, HK), (D, HK), (250, L2(250)), (250, L2(250) - 250), (0, HK - 250)],
        'пята': [(CHORD_L - 250, 0), (CHORD_L, 0), (CHORD_L, L2(CHORD_L)), (CHORD_L - 250, L2(CHORD_L - 250))],
        'низ_подкоса': [(0, 0), (220, 0), (220, 220), (0, 220)],
        'верх_подкоса': [(320, L1(320) - 160), (520, L1(520) - 160), (520, L2(520)), (320, L2(320))],
    }
    sides = {'средняя': [(-PLY_G, 0), (T, T + PLY_G)], 'фронтон_0': [(T, T + PLY_G)], 'фронтон_25': [(-PLY_G, 0)]}[kind]
    for x0, x1 in sides:
        for g, pts in gus.items():
            p.append(P(prism_x(pts, x0, x1), f'косынка_{g}_фанера_{PLY_G}', 'фанера', (240, 220, 175)))
    if kind != 'средняя':
        x0, x1 = (-PLY, 0) if kind == 'фронтон_0' else (T, T + PLY)
        e = SPAN_HALF + PLY
        p.append(P(prism_x([(0, 0), (e, 0), (e, L2(e)), (D, HK), (0, HK)], x0, x1), f'обшивка_фронтона_фанера_{PLY}', 'фанера', PLYC))
    return p


# ------------------------------------------------------------------ сборка
def compound(parts, label):
    ch = []
    for q in parts:
        s = q.solid.moved(Location())
        s.label = q.name
        ch.append(s)
    c = Compound(children=ch)
    c.label = label
    return c


def place(parts, loc):
    return [P(q.solid.moved(loc), q.name, q.mat, q.color) for q in parts]


# стороны: (поворот, начало системы «стены»: s вдоль стены, o внутрь от наружной грани)
SIDES = {'A': (0, (0, 0)), 'B': (90, (SIZE, 0)), 'C': (180, (SIZE, SIZE)), 'D': (270, (0, SIZE))}
SPAN_OF = {'A': 'окно', 'B': 'окно', 'C': 'окно', 'D': 'дверь'}
EAVE = {'A': True, 'B': False, 'C': True, 'D': False}
TRUSS_X = (WC - T / 2, SIZE / 2 - T / 2, SIZE - WC - T / 2)
Y_RIDGE = SPAN_HALF


def build():
    blocks, house = {}, []

    def blk(name, parts):
        blocks.setdefault(name, parts)
        return parts

    for wn, (rot, org) in SIDES.items():
        loc = Location((org[0], org[1], 0), (0, 0, rot))
        house.append(('основание', f'лежень_{wn}', place(blk('лежень', lezhen()), loc * Location((POST, 0, 0)))))
        house.append(('каркас', f'стойка_{wn}', place(blk('стойка_угловая', post()), loc)))
        house.append(('каркас', f'болты_уголков_{wn}', place(frame_bolts(), loc)))
        house.append(('каркас', f'обвязка_{wn}', place(blk('обвязка_карнизная' if EAVE[wn] else 'обвязка_фронтонная', beam(EAVE[wn])),
                                                          loc * Location((POST, 0, 0)))))
        sp = blk(f'пролёт_{SPAN_OF[wn]}', span(SPAN_OF[wn]))
        house.append(('пролёты', f'пролёт_{SPAN_OF[wn]}_{wn}', place(sp, loc * Location((POST + GAP, PLY, Z0)))))
        top_b = [bolt((POST + GAP + s_, SPAN_O, Z0 + H - T), (0, 0, 1), 80, 'футорка') for s_ in (PW / 2, 2.5 * PW)]
        house.append(('пролёты', f'болты_пролётов_{wn}', place(span_bolts(), loc) + place(top_b, loc)))
    saved = CUT.copy(), HW.copy()     # щиты-образцы для блоки/ не входят в раскрой
    for k in ('глухой', 'окно', 'дверь'):
        blk(f'щит_{k}', panel(k))
    CUT.clear(), CUT.update(saved[0]), HW.clear(), HW.update(saved[1])

    for j, x0 in enumerate(TRUSS_X):
        kinds = ('фронтон_0', 'фронтон_25') if j == 0 else ('средняя', 'средняя') if j == 1 else ('фронтон_25', 'фронтон_0')
        south = blk(f'полуферма_{kinds[0]}', half_truss(kinds[0]))
        north = blk(f'полуферма_{kinds[1]}', half_truss(kinds[1]))
        tr = place(south, Location((x0, Y_RIDGE, ZP))) + place(north, Location((x0 + T, Y_RIDGE, ZP), (0, 0, 180)))
        zb = ZP + (D + HK) / 2
        tr.append(bolt((x0 + T / 2, Y_RIDGE - D, zb), (0, 1, 0), 130, 'барашек'))
        for yy in (WC, SIZE - WC):          # пяты: у крайних — в футорку стойки, у средней — обвязки
            tr.append(bolt((x0 + T / 2, yy, ZP + D), (0, 0, -1), 80, 'футорка'))
        house.append(('крыша', f'ферма_{j + 1}', tr))
    zr = ZP + HK
    RL = SIZE + 2 * OVH
    ridge = [P(box(-OVH, SIZE + OVH, Y_RIDGE - D, Y_RIDGE + D, zr, zr + 50), f'конёк_50х100х{RL}', 'дерево', FRAME)]
    for x0 in TRUSS_X:          # бобышки по бокам каждой фермы: конёк не сползает
        for xa in (x0 - PLY_G - 1 - T, x0 + T + PLY_G + 1):
            ridge.append(bar('бобышка_конька_25х50х100', '25×50', 100, box(xa, xa + T, Y_RIDGE - D, Y_RIDGE + D, zr - 50, zr), WOOD2))
    CUT[('50×100', RL)] += 1
    house.append(('крыша', 'конёк', blk('конёк', ridge)))
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for side in (1, -1):
        for u0 in PURLIN_U:
            du = 12.5 * COS
            A, B = np.array([u0 - du, L2(u0 - du)]), np.array([u0 + du, L2(u0 + du)])
            q = [A, B, B + 50 * n_, A + 50 * n_]
            pr = prism_x([tuple(x) for x in q], -OVH, SIZE + OVH, lambda u, s=side: Y_RIDGE - s * u).moved(Location((0, 0, ZP)))
            CUT[('25×50', RL)] += 1
            house.append(('крыша', 'прогон', blk('прогон', [P(pr, f'прогон_25х50х{RL}', 'дерево', (185, 140, 90))])))
        top = lambda u: L2(u) + 50 / COS + 1
        q = [(0, top(0)), (TAIL_U + 50, top(TAIL_U + 50)), (TAIL_U + 50, top(TAIL_U + 50) + 1), (0, top(0) + 1)]
        tent = prism_x(q, -OVH - 25, SIZE + OVH + 25, lambda u, s=side: Y_RIDGE - s * u).moved(Location((0, 0, ZP)))
        house.append(('крыша', 'тент', [P(tent, 'тент', 'фанера', (70, 110, 90))]))
    HW['Тент тарпаулин 4×5 м с люверсами'] += 1
    HW['Ремень стяжной с храповиком 6 м (через крышу к лежням)'] += 2
    return blocks, house


def export(out):
    CUT.clear()
    HW.clear()
    blocks, house = build()
    os.makedirs(f'{out}/блоки', exist_ok=True)
    for name, parts in blocks.items():
        save_step(compound(parts, name), f'{out}/блоки/{name}.step')
    groups = collections.OrderedDict()
    for g, b, parts in house:
        groups.setdefault(g, []).append(compound(parts, b))
    top = Compound(children=[Compound(children=v, label=k) for k, v in groups.items()])
    top.label = 'дом_v5_3х3'
    save_step(top, f'{out}/дом_v5_3х3.step')
    return blocks, house, top


def write_bom(out, blocks, house):
    L = ['# Дом v5 — спецификация', '',
         'Сгенерировано `tools/v5_house.py` по модели. Массы — сосна 500 кг/м³, фанера 600 кг/м³.', '',
         '## Брус (раскрой)', '', '| Сечение | Длина, мм | Шт. | Пог. м |', '|---|---|---|---|']
    tot = collections.Counter()
    for (sec, ln), n in sorted(CUT.items(), key=lambda t: (t[0][0], -t[0][1])):
        L.append(f'| {sec} | {ln} | {n} | {ln * n / 1000:.2f} |')
        tot[sec] += ln * n / 1000
    L += ['', '**Итого:** ' + ', '.join(f'{k} — {v:.1f} пог. м' for k, v in sorted(tot.items())), '',
          'Лапки прогонов 25×25×30 — из обрезков (строка «25×50 × 50»).', '',
          '## Фанера', '',
          f'* ФСФ {PLY} мм 4/4 (водостойкая), лист 1220×2440 — 15 листов: 12 щитов {PW}×{H} '
          '(лист целиком, без стыков), дверное полотно, 2 листа на 4 половины фронтонов '
          '(≈1604×610, по 2 на лист). Если 3 мм нет — ФСФ 4 мм, размеры те же.',
          f'* {PLY_G} мм — косынки ферм, 32 шт. (≈ 1 лист 1220×2440).', '',
          '## Фурнитура', '', '| Позиция | Шт. |', '|---|---|']
    for k, n in sorted(HW.items()):
        L.append(f'| {k} | {n} |')
    L += ['', 'Весь крепёж — одного диаметра М10, разной длины; ключ на 17 (или 16 — по стандарту болта). '
          'Взять запас 10%.', '',
          'Для мастерской: клей ПВА D3, саморезы 3,5×25 (обшивка), 4×40 (косынки, рейки), '
          '5×70 (узлы рам), антисептик; сверло по дереву Ø11 (под болты) и Ø14 (под футорки).', '',
          '## Массы блоков', '', '| Блок | Шт. | Масса, кг |', '|---|---|---|']
    cnt = {'стойка_угловая': 4, 'лежень': 4, 'обвязка_карнизная': 2,
           'обвязка_фронтонная': 2, 'щит_глухой': 8, 'щит_окно': 3, 'щит_дверь': 1,
           'пролёт_окно': 3, 'пролёт_дверь': 1, 'конёк': 1, 'прогон': 4}
    for name, parts in blocks.items():
        n = 2 if name.startswith('полуферма') else cnt.get(name, 0)
        L.append(f'| {name} | {n} | {sum(q.mass() for q in parts):.1f} |')
    total = sum(q.mass() for g, b, parts in house for q in parts if q.name != 'тент')
    L += ['', f'**Масса дома без тента: ≈ {total:.0f} кг.**', '']
    open(f'{out}/СПЕЦИФИКАЦИЯ.md', 'w').write('\n'.join(L))
    return total


if __name__ == '__main__':
    blocks, house, top = export(sys.argv[1])
    print('масса', round(write_bom(sys.argv[1], blocks, house)))
    bb = top.bounding_box()
    print('габарит', [round(v) for v in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)])
    for name, parts in blocks.items():
        print(f'{name:28s} {sum(q.mass() for q in parts):5.1f} кг')
    print(CUT)
    print(HW)
