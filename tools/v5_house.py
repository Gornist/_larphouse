"""Дом 3×3, версия 5: быстроразборная конструкция из готовых блоков.

Блоки (собираются в мастерской навсегда, на клей + саморезы):
  щиты стен 1000×2400 (глухой, угловой со стойкой, окно, дверь),
  полуфермы (средняя, фронтонная левая/правая), обвязки, лежни.
На площадке блоки соединяются штырями, рычажными замками и 3 барашками.

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
W, H = 1000, 2400            # щит
T, D = 25, 50                # брус 25×50: толщина в плоскости щита, глубина
PLY = 4                      # фанера обшивки
PLY_G = 9                    # фанера косынок
PIN_D, HOLE_D = 12, 13       # штырь и отверстие под него
WALL_L = 3 * W               # длина стены без стойки
LEZ = (50, 100)              # лежень: высота × ширина
PLATE = 50                   # обвязка 50×50
ALPHA = math.radians(17.6)   # уклон кровли
TAN, COS, SIN = math.tan(ALPHA), math.cos(ALPHA), math.sin(ALPHA)
SPAN_HALF = 1550             # от конька до наружной грани стены
CHORD_L = 1600               # затяжка полуфермы
TAIL_U = 1930                # конец стропила (свес ≈ 380)
PURLIN_U = (650, 1300)       # прогоны
OVH = 150                    # свес конька/прогонов за фронтон

DENS = {'дерево': 500e-9, 'фанера': 600e-9, 'сталь': 7850e-9}   # кг/мм³

# ------------------------------------------------------------------ учёт деталей
CUT = collections.Counter()      # (сечение, длина) -> шт (раскрой)
HW = collections.Counter()       # фурнитура


class P:
    """Деталь: тело + имя + материал + цвет."""
    def __init__(self, solid, name, mat='дерево', color=(214, 176, 128)):
        self.solid, self.name, self.mat, self.color = solid, name, mat, color

    def mass(self):
        return self.solid.volume * DENS[self.mat]


def box(x0, x1, y0, y1, z0, z1):
    return Box(x1 - x0, y1 - y0, z1 - z0, align=MIN).moved(Location((x0, y0, z0)))


def cyl(d, p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    L = np.linalg.norm(v)
    c = Cylinder(d / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ax = np.argmax(np.abs(v))
    if ax == 0:
        c = c.rotate(Axis.Y, 90 if v[0] > 0 else -90)
    elif ax == 1:
        c = c.rotate(Axis.X, -90 if v[1] > 0 else 90)
    elif v[2] < 0:
        c = c.rotate(Axis.X, 180)
    return c.moved(Location(tuple(p0)))


def prism_x(pts_uz, x0, x1, y_of_u=lambda u: -u):
    """Плоский многоугольник (u, z) -> призма по X от x0 до x1."""
    f = Face(Wire.make_polygon([Vector(x0, y_of_u(u), z) for u, z in pts_uz], close=True))
    return extrude(f, amount=x1 - x0, dir=(1, 0, 0))


def bar(name, sec, length, solid, color=(214, 176, 128), cut=True):
    if cut:
        CUT[(sec, round(length))] += 1
    return P(solid, name, 'дерево', color)


def pin(p0, p1, kind='штырь'):
    L = round(np.linalg.norm(np.subtract(p1, p0)))
    HW[f'{kind} Ø{PIN_D}×{L}'] += 1
    return P(cyl(PIN_D, p0, p1), f'штырь_{PIN_D}х{L}', 'сталь', (90, 90, 100))


# ------------------------------------------------------------------ щиты стен
WOOD = (222, 184, 135)
WOOD2 = (196, 152, 104)
PLYC = (236, 214, 170)


def panel(kind):
    """Щит в своих координатах: X=s вдоль стены, Y=n внутрь (0 — наружная грань
    каркаса, обшивка на n<0), Z вверх. kind: глухой | угловой | окно | дверь."""
    parts = []
    PIN_BOT, PIN_TOP = (60, 940), (237.5, 712.5)
    # стойки
    left = box(0, T, 0, D, 0, H)
    right = box(W - T, W, 0, D, 0, H)
    parts += [bar('стойка_щита_25х50х2400', '25×50', H, left),
              bar('стойка_щита_25х50х2400', '25×50', H, right)]
    # перемычки низ/верх с отверстиями и штырями
    bot = box(T, W - T, 0, D, 0, T)
    top = box(T, W - T, 0, D, H - T, H)
    for s in PIN_BOT:
        bot = bot - cyl(HOLE_D, (s, D / 2, -1), (s, D / 2, T + 1))
    for s in PIN_TOP:
        top = top - cyl(PIN_D, (s, D / 2, H - T - 1), (s, D / 2, H + 1))
        parts.append(pin((s, D / 2, H - T), (s, D / 2, H + 40)))
    parts += [bar('перемычка_25х50х950', '25×50', W - 2 * T, bot, WOOD2),
              bar('перемычка_25х50х950', '25×50', W - 2 * T, top, WOOD2)]
    cut = None
    if kind == 'окно':
        for z0 in (1187.5, 2187.5):
            parts.append(bar('перемычка_25х50х950', '25×50', W - 2 * T,
                             box(T, W - T, 0, D, z0, z0 + T), WOOD2))
        cut = (T, W - T, 1212.5, 2187.5)
    if kind == 'дверь':
        for s0 in (75, 900):
            parts.append(bar('стойка_двери_25х50х2050', '25×50', 2050,
                             box(s0, s0 + T, 0, D, T, 2075), WOOD2))
        parts.append(bar('перемычка_25х50х950', '25×50', W - 2 * T,
                         box(T, W - T, 0, D, 2075, 2100), WOOD2))
        cut = (100, 900, T, 2075)
        parts += door_leaf()
    width = W
    if kind == 'угловой':
        width = W + 50
        post = box(W, W + 50, 0, 50, 0, H)
        post = post - cyl(HOLE_D, (W + 25, 25, -1), (W + 25, 25, 45))           # низ: угловой штырь
        post = post - cyl(PIN_D, (W + 25, 25, H - 40), (W + 25, 25, H + 1))      # верх: штырь
        parts.append(bar('стойка_угловая_50х50х2400', '50×50', H, post, (170, 125, 80)))
        parts.append(pin((W + 25, 25, H - 40), (W + 25, 25, H + PLATE + T + 25), 'штырь (с R-шплинтом)'))
        HW['R-шплинт под штырь Ø12'] += 1
    sh = box(0, width, -PLY, 0, 0, H)
    if cut:
        sh = sh - box(cut[0], cut[1], -PLY - 1, 1, cut[2], cut[3])
    parts.append(P(sh, f'обшивка_фанера_{PLY}мм_{width}х{H}', 'фанера', PLYC))
    return parts


def door_leaf():
    """Дверное полотно 790×2040 на 2 петлях, проём 800×2050."""
    s0, s1, z0, z1 = 105, 895, 30, 2070
    p = []
    for s in (s0, s1 - 50):
        p.append(bar('полотно_стойка_25х50х2040', '25×50', z1 - z0, box(s, s + 50, 0, T, z0, z1), (200, 150, 95)))
    for z in (z0, (z0 + z1) / 2 - 25, z1 - 50):
        p.append(bar('полотно_перемычка_25х50х690', '25×50', s1 - s0 - 100,
                     box(s0 + 50, s1 - 50, 0, T, z, z + 50), (200, 150, 95)))
    p.append(P(box(s0, s1, -PLY, 0, z0, z1), 'полотно_фанера_790х2040', 'фанера', (225, 200, 150)))
    for z in (300, 1700):
        p.append(P(box(s0 - 5, s0 + 25, T, T + 3, z, z + 100), 'петля_100', 'сталь', (60, 60, 60)))
    p.append(P(box(s1 - 45, s1 - 25, T, T + 40, 1000, 1150), 'ручка', 'сталь', (60, 60, 60)))
    HW['петля дверная 100 мм'] += 2
    HW['ручка + завёртка/щеколда'] += 1
    return p


def plate(eave):
    """Обвязка 50×50×3050 на щиты стены (координаты стены, Z от низа щитов)."""
    L = WALL_L + 50
    b = box(0, L, 0, 50, H, H + PLATE)
    holes = [i * W + s for i in range(3) for s in (237.5, 712.5)] + [WALL_L + 25]
    for s in holes:
        b = b - cyl(HOLE_D, (s, 25, H - 1), (s, 25, H + PLATE + 1))
    parts = []
    if eave:     # штырь пяты средней фермы
        b = b - cyl(PIN_D, (1500, 25, H + 10), (1500, 25, H + PLATE + 1))
        parts.append(pin((1500, 25, H + 10), (1500, 25, H + PLATE + T + 25), 'штырь (с R-шплинтом)'))
        HW['R-шплинт под штырь Ø12'] += 1
    parts.insert(0, bar(f'обвязка_{"карнизная" if eave else "фронтонная"}_50х50х{L}', '50×50', L, b, (160, 115, 70)))
    return parts


def latch(x0, x1, y0, y1, z):
    HW['замок рычажный («лягушка»)'] += 1
    return P(box(x0, x1, y0, y1, z - 20, z + 20), 'замок_рычажный', 'сталь', (200, 40, 40))


# ------------------------------------------------------------------ полуфермы
def L1(u):   # низ стропила
    return D + (CHORD_L - u) * TAN


def L2(u):   # верх стропила
    return L1(u) + D / COS


HK = L2(D)   # верх стойки фермы


def half_truss(kind):
    """Полуферма в своих координатах: X — толщина 0..25, Y = -u (u — от конька
    наружу), Z — от низа затяжки. kind: средняя | фронтон_0 | фронтон_25
    (на какой грани по X обшивка фронтона)."""
    p = []
    chord = prism_x([(0, 0), (CHORD_L, 0), (CHORD_L, D), (0, D)], 0, T)
    chord = chord - cyl(HOLE_D, (T / 2, -1525, -1), (T / 2, -1525, D + 1))
    p.append(bar(f'затяжка_25х50х{CHORD_L}', '25×50', CHORD_L, chord, WOOD))
    post = prism_x([(0, D), (D, D), (D, HK), (0, HK)], 0, T)
    zb = (D + HK) / 2
    post = post - cyl(9, (T / 2, 1, zb), (T / 2, -D - 1, zb))
    post = post - cyl(PIN_D, (T / 2, -25, HK - 40), (T / 2, -25, HK + 1))
    p.append(bar(f'стойка_фермы_25х50х{HK - D:.0f}', '25×50', HK - D, post, WOOD2))
    p.append(pin((T / 2, -25, HK - 40), (T / 2, -25, HK + 40)))
    raf_len = (TAIL_U - D) / COS
    p.append(bar(f'стропило_25х50х{raf_len:.0f}', '25×50', raf_len,
                 prism_x([(D, L1(D)), (TAIL_U, L1(TAIL_U)), (TAIL_U, L2(TAIL_U)), (D, L2(D))], 0, T),
                 (205, 160, 110)))

    def hit(u0, z0):
        s = (D + CHORD_L * TAN - z0 - u0 * TAN) / (1 + TAN)
        return (u0 + s, z0 + s)
    a, b = (D + D * math.sqrt(2), D), (D, D + D * math.sqrt(2))
    br = [(D, D), a, hit(*a), hit(*b), b]
    br_len = math.dist(a, hit(*a))
    p.append(bar(f'подкос_25х50х{br_len:.0f}', '25×50', br_len, prism_x(br, 0, T), (165, 115, 70)))
    # лапки под прогоны
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for u0 in PURLIN_U:
        du = 12.5 * COS
        B = np.array([u0 + du, L2(u0 + du)])
        q = [B, B + 25 * t_, B + 25 * t_ + 30 * n_, B + 30 * n_]
        p.append(bar('лапка_прогона_25х25х30', '25×25', 30, prism_x([tuple(x) for x in q], 0, T), WOOD2, cut=False))
    CUT[('25×50', 50)] += len(PURLIN_U)
    # косынки
    gus = {
        'вершина': [(0, HK), (D, HK), (250, L2(250)), (250, L2(250) - 250), (0, HK - 250)],
        'пята': [(1350, 0), (CHORD_L, 0), (CHORD_L, L2(CHORD_L)), (1350, L2(1350))],
        'низ_подкоса': [(0, 0), (220, 0), (220, 220), (0, 220)],
        'верх_подкоса': [(320, L1(320) - 160), (520, L1(520) - 160), (520, L2(520)), (320, L2(320))],
    }
    sides = {'средняя': [(-PLY_G, 0), (T, T + PLY_G)],
             'фронтон_0': [(T, T + PLY_G)], 'фронтон_25': [(-PLY_G, 0)]}[kind]
    for x0, x1 in sides:
        for g, pts in gus.items():
            p.append(P(prism_x(pts, x0, x1), f'косынка_{g}_фанера_{PLY_G}', 'фанера', (240, 220, 175)))
    if kind != 'средняя':
        x0, x1 = (-PLY, 0) if kind == 'фронтон_0' else (T, T + PLY)
        gable = [(0, 0), (SPAN_HALF + PLY, 0), (SPAN_HALF + PLY, L2(SPAN_HALF + PLY)), (D, HK), (0, HK)]
        p.append(P(prism_x(gable, x0, x1), f'обшивка_фронтона_фанера_{PLY}', 'фанера', PLYC))
    return p


# ------------------------------------------------------------------ сборка дома
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


WALLS = {   # имя: (поворот, начало, тип среднего щита, карнизная?)
    'A': (0, (0, 0), 'окно', True),
    'B': (90, (WALL_L + 50, 50), 'окно', False),
    'C': (180, (WALL_L, WALL_L + 100), 'окно', True),
    'D': (270, (-50, WALL_L + 50), 'дверь', False),
}
Z0 = LEZ[0]                  # низ щитов
ZP = Z0 + H + PLATE          # верх обвязки = низ затяжек
TRUSS_X = (-37.5, 1487.5, 3012.5)
Y_RIDGE = SPAN_HALF


def build():
    blocks = {}              # имя блока -> список деталей (в своих координатах)
    house = []               # (имя группы, имя блока, детали в мировых координатах)

    def blk(name, parts):
        blocks.setdefault(name, parts)
        return parts

    # основание
    lez = []
    for name, (x0, x1, y0, y1), lower in [
            ('лежень_X', (-50, 3050, 0, 100), True), ('лежень_X', (-50, 3050, 3000, 3100), True),
            ('лежень_Y', (2950, 3050, 0, 3100), False), ('лежень_Y', (-50, 50, 0, 3100), False)]:
        b = box(x0, x1, y0, y1, 0, LEZ[0])
        laps = [(-50, 50), (2950, 3050)] if lower else [(0, 100), (3000, 3100)]
        for a0, a1 in laps:
            b = b - (box(a0, a1, y0 - 1, y1 + 1, 25, 51) if lower else box(x0 - 1, x1 + 1, a0, a1, -1, 25))
        lez.append([name, b, (x0, x1, y0, y1), lower])
    corner_pins = [(3025, 25), (3025, 3075), (-25, 3075), (-25, 25)]
    anchors = [(2975, 75), (2975, 3025), (25, 3025), (25, 75), (1500, 75), (1500, 3025)]
    wall_pins = []
    for wn, (rot, org, mid, eave) in WALLS.items():
        r = math.radians(rot)
        for i in range(3):
            for s in (60, 940):
                sx, ny = i * W + s, 25
                wall_pins.append((org[0] + sx * math.cos(r) - ny * math.sin(r),
                                  org[1] + sx * math.sin(r) + ny * math.cos(r)))
    for k, (name, b, (x0, x1, y0, y1), lower) in enumerate(lez):
        inside = lambda x, y: x0 < x < x1 and y0 < y < y1
        uniq = [(x, y, 10, Z0 + 40, PIN_D, 'pin') for x, y in wall_pins if inside(x, y)]
        # угловые штыри: вклеены в нижний лежень, проходят верхний и входят в стойку
        uniq += [(x, y, 5, Z0 + 40, PIN_D, 'pin') if lower else (x, y, -1, Z0 + 1, HOLE_D, 'hole')
                 for x, y in corner_pins if inside(x, y)]
        uniq += [(x, y, -1, Z0 + 1, 16, 'hole') for x, y in anchors if inside(x, y)]
        parts = []
        for x, y, z0, z1, d, kind in uniq:
            if kind == 'pin':
                b = b - cyl(PIN_D, (x, y, z0), (x, y, Z0 + 1))
                parts.append(pin((x, y, z0), (x, y, z1)))
            else:
                b = b - cyl(d, (x, y, z0), (x, y, z1))
        CUT[('50×100', 3100)] += 1
        parts.insert(0, P(b, f'{name}_50х100х3100', 'дерево', (150, 105, 65)))
        blk(name, place(parts, Location()))
        house.append(('основание', name + f'_{k + 1}', parts))
    for x, y in anchors:
        HW['анкер-штопор Ø14×600 + шайба 50'] += 1
        house.append(('основание', 'анкер', [P(cyl(14, (x, y, -600), (x, y, Z0 + 3)), 'анкер_штопор', 'сталь', (70, 70, 80))]))

    # стены
    for wn, (rot, org, mid, eave) in WALLS.items():
        loc = Location((org[0], org[1], Z0), (0, 0, rot))
        kinds = ['глухой', mid, 'угловой']
        for i, k in enumerate(kinds):
            pp = blk(f'щит_{k}', panel(k))
            house.append((f'стена_{wn}', f'щит_{k}', place(pp, loc * Location((i * W, 0, 0)))))
        pl = blk(f'обвязка_{"карнизная" if eave else "фронтонная"}', plate(eave))
        house.append((f'стена_{wn}', pl[0].name, place(pl, loc)))
        lt = []
        for i in (1, 2):
            for z in (300, 2100):
                lt.append(latch(i * W - 40, i * W + 40, D, D + 22, z))
        for z in (300, 2100, H + PLATE / 2):           # угол: стены и обвязки
            lt.append(latch(WALL_L - 30, WALL_L, D, D + 30, z))
        house.append((f'стена_{wn}', 'замки', place(lt, loc)))

    # крыша
    for j, x0 in enumerate(TRUSS_X):
        kinds = ('фронтон_0', 'фронтон_25') if j == 0 else ('средняя', 'средняя') if j == 1 else ('фронтон_25', 'фронтон_0')
        south = blk(f'полуферма_{kinds[0]}', half_truss(kinds[0]))
        north = blk(f'полуферма_{kinds[1]}', half_truss(kinds[1]))
        tr = place(south, Location((x0, Y_RIDGE, ZP)))
        tr += place(north, Location((x0 + T, Y_RIDGE, ZP), (0, 0, 180)))
        zb = ZP + (D + HK) / 2
        tr.append(P(cyl(8, (x0 + T / 2, Y_RIDGE - D - 15, zb), (x0 + T / 2, Y_RIDGE + D + 15, zb)), 'болт_M8х130_барашек', 'сталь', (60, 60, 60)))
        HW['болт M8×130 + барашковая гайка + 2 шайбы'] += 1
        house.append(('крыша', f'ферма_{j + 1}', tr))
    zr = ZP + HK
    ridge = box(-OVH, WALL_L + 50 + OVH, Y_RIDGE - D, Y_RIDGE + D, zr, zr + 50)
    for x0 in TRUSS_X:
        for dy in (-25, 25):
            ridge = ridge - cyl(HOLE_D, (x0 + T / 2, Y_RIDGE + dy, zr - 1), (x0 + T / 2, Y_RIDGE + dy, zr + 45))
    CUT[('50×100', WALL_L + 50 + 2 * OVH)] += 1
    blk('конёк', [P(ridge, f'конёк_50х100х{WALL_L + 50 + 2 * OVH}', 'дерево', (150, 105, 65))])
    house.append(('крыша', 'конёк', [P(ridge, f'конёк_50х100х{WALL_L + 50 + 2 * OVH}', 'дерево', (150, 105, 65))]))
    t_, n_ = np.array([COS, -SIN]), np.array([SIN, COS])
    for side in (1, -1):
        for u0 in PURLIN_U:
            du = 12.5 * COS
            A = np.array([u0 - du, L2(u0 - du)])
            B = np.array([u0 + du, L2(u0 + du)])
            q = [A, B, B + 50 * n_, A + 50 * n_]
            pr = prism_x([tuple(x) for x in q], -OVH, WALL_L + 50 + OVH, lambda u, s=side: Y_RIDGE - s * u)
            pr = pr.moved(Location((0, 0, ZP)))
            CUT[('25×50', WALL_L + 50 + 2 * OVH)] += 1
            blk('прогон', [P(pr, f'прогон_25х50х{WALL_L + 50 + 2 * OVH}', 'дерево', (185, 140, 90))])
            house.append(('крыша', 'прогон', [P(pr, f'прогон_25х50х{WALL_L + 50 + 2 * OVH}', 'дерево', (185, 140, 90))]))
        top = lambda u: L2(u) + 50 / COS + 1
        q = [(0, top(0)), (TAIL_U + 50, top(TAIL_U + 50)), (TAIL_U + 50, top(TAIL_U + 50) + 1), (0, top(0) + 1)]
        tent = prism_x(q, -OVH - 25, WALL_L + 50 + OVH + 25, lambda u, s=side: Y_RIDGE - s * u).moved(Location((0, 0, ZP)))
        house.append(('крыша', 'тент', [P(tent, 'тент', 'фанера', (70, 110, 90))]))
    HW['тент ПВХ/оксфорд ~3,4×4,2 м с люверсами'] += 1
    HW['растяжка ремённая с колышком'] += 4
    return blocks, house


def export(out):
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
    """Спецификация: раскрой бруса, фанера, фурнитура, массы блоков."""
    L = ['# Дом v5 — спецификация', '',
         'Сгенерировано `tools/v5_house.py` по модели. Массы — сосна 500 кг/м³, фанера 600 кг/м³.', '',
         '## Брус (раскрой)', '', '| Сечение | Длина, мм | Шт. | Пог. м |', '|---|---|---|---|']
    tot = collections.Counter()
    for (sec, ln), n in sorted(CUT.items(), key=lambda t: (t[0][0], -t[0][1])):
        L.append(f'| {sec} | {ln} | {n} | {ln * n / 1000:.2f} |')
        tot[sec] += ln * n / 1000
    L += ['', '**Итого:** ' + ', '.join(f'{k} — {v:.1f} пог. м' for k, v in sorted(tot.items())), '']
    L += ['Лапки прогонов 25×25×30 нарезаются из обрезков 25×50 (строка «25×50 × 50»).', '',
          '## Фанера', '',
          f'* {PLY} мм — 15 листов 1220×2440: 12 щитов (1000×2400, угловые 1050×2400), '
          'дверное полотно 790×2040, 2 листа на 4 половины фронтонов (≈1554×594, по 2 на лист).',
          f'* {PLY_G} мм — косынки ферм, 32 шт. (≈ 1 лист 1220×2440).', '',
          '## Фурнитура', '', '| Позиция | Шт. |', '|---|---|']
    for k, n in sorted(HW.items()):
        L.append(f'| {k} | {n} |')
    L += ['', 'Плюс для мастерской: клей ПВА D3, саморезы по дереву 4×40 (обшивка, косынки) '
          'и 5×70 (узлы рам), антисептик.', '', '## Массы блоков', '', '| Блок | Шт. | Масса, кг |', '|---|---|---|']
    cnt = collections.Counter(b for g, b, parts in house)
    for name, parts in blocks.items():
        n = 2 if name.startswith('полуферма') else sum(c for k, c in cnt.items() if k.startswith(name))
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
        m = sum(q.mass() for q in parts)
        print(f'{name:28s} {m:5.1f} кг')
    print(CUT)
    print(HW)
