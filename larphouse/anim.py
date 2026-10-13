"""Анимация сборки дома: раскадровка -> JSON для larphouse/anim_blender.py.

  python -m larphouse anim 3x3            # -> build/anim_3x3.json

Каждая деталь — меш в собранном положении (мм) и ключи [t, dx, dy, dz]:
смещение от собранного положения во времени. До первого ключа деталь скрыта.
Порядок: каркас -> щиты -> щиты в пролёты -> пролёты на каркас -> крыша.
"""
import json, math, os
import numpy as np

from .dims import POST, ZP
from .house import build
from .panels import panel

TOL = 0.6                     # точность тесселяции, мм
BOLT = (235, 110, 30)         # болты — оранжевые, чтобы было видно, где крутить
TIE = (215, 35, 45)           # резинки тента — красные


class Part:
    def __init__(self, q):
        v, f = q.solid.tessellate(TOL, 0.35)
        self.name = q.name
        self.color = BOLT if q.name.startswith('болт') else TIE if q.name.startswith('резинка') else q.color
        self.axis = getattr(q, 'axis', None)
        self.alpha = 0.85 if q.name == 'тент' else 1.0
        self.v = np.array([(p.X, p.Y, p.Z) for p in v])
        self.f = f
        self.keys = []
        self.c = (self.v.min(0) + self.v.max(0)) / 2      # центр габарита
        self.ext = self.v.max(0) - self.v.min(0)

    def json(self):
        return dict(name=self.name, color=self.color, alpha=self.alpha,
                    v=np.round(self.v, 2).ravel().tolist(), f=np.array(self.f).ravel().tolist(),
                    keys=[[round(k, 3) for k in key] for key in self.keys])


def go(parts, t0, dur, to=(0, 0, 0), frm=None):
    """Движение к смещению `to` за [t0, t0 + dur]. Новая деталь появляется в t0 в `frm`."""
    for p in parts:
        if not p.keys:
            p.keys.append([t0, *(frm if frm is not None else to)])
        else:
            p.keys.append([t0, *p.keys[-1][1:]])
        p.keys.append([t0 + dur, *to])


def add(a, b_):
    return tuple(x + y for x, y in zip(a, b_))


def mul(a, k):
    return tuple(x * k for x in a)


class Timeline:
    def __init__(self, center):
        self.t = 0.0
        self.center = np.array(center)
        self.captions, self.cam = [], []

    def caption(self, title, sub='', dur=None):
        if self.captions and self.captions[-1][1] is None:
            self.captions[-1][1] = self.t
        self.captions.append([self.t, None if dur is None else self.t + dur, title, sub])

    def camera(self, az, el, dist, tz, t=None):
        self.cam.append([self.t if t is None else t, az, el, dist, tz])

    def bolt_off(self, p, base=(0, 0, 0), L=250):
        """Смещение, из которого болт вдвигается по своей оси — со стороны головки."""
        if p.axis is not None:
            h, e = np.array(p.axis[0]), np.array(p.axis[1])
            return add(base, tuple(L * (h - e) / np.linalg.norm(h - e)))
        ax = int(np.argmax(p.ext))
        d = [0, 0, 0]
        if ax == 2:
            d[2] = L if p.c[2] > ZP else -L
        else:
            d[ax] = L if p.c[ax] >= self.center[ax] else -L
        return add(base, d)

    def bolts_in(self, bolts, t0, dur=0.5, base=(0, 0, 0)):
        for p in bolts:
            go([p], t0, dur, base, frm=self.bolt_off(p, base))


def storyboard(key, out):
    h = build(key)
    name, house = h.title, h.items
    SX, SY, ZT = h.dims
    tl = Timeline((SX / 2, SY / 2))
    items = [(gr, nm, [Part(q) for q in parts]) for gr, nm, parts in house]
    allp = [p for _, _, ps in items for p in ps]
    by = lambda pre: [(nm, ps) for gr, nm, ps in items if nm.startswith(pre)]

    def near(ps_named, xy):
        return [p for _, ps in ps_named for p in ps
                if abs(p.c[0] - xy[0]) < POST * 1.6 and abs(p.c[1] - xy[1]) < POST * 1.6]

    def outward(c):
        d = c[:2] - tl.center
        ax = int(np.argmax(np.abs(d)))
        v = [0, 0, 0]
        v[ax] = 1 if d[ax] > 0 else -1
        along = [0, 0, 0]
        along[1 - ax] = 1
        return tuple(v), tuple(along)

    # порядок рёбер по кругу: юг, восток, север, запад
    def angle_of(ps):
        c = np.mean([p.c for p in ps], 0)
        return (math.atan2(c[1] - tl.center[1], c[0] - tl.center[0]) + math.pi / 2) % (2 * math.pi)

    ring = lambda pre: sorted(by(pre), key=lambda it: angle_of(it[1]))

    # ---------------------------------------------------------- 0. заставка
    tl.camera(-35, 24, 11500, 1300)
    tl.caption(f'Дом {name}: сборка на площадке', 'Каркас → щиты → пролёты → крыша. Все соединения — болты М10', dur=3.0)
    tl.t = 2.5

    # ---------------------------------------------------------- 1. каркас
    tl.caption('1. Лежни', 'Раскладываем по плану на землю, уголками внутрь клетки')
    for _, ps in ring('лежень'):
        go(ps, tl.t, 0.8, frm=(0, 0, 600))
        tl.t += 0.6
    tl.t += 0.8

    tl.caption('2. Стойки', 'В каждый угол, между концами лежней. Болт М10×130 сквозь стойку в уголок — барашек руками')
    tl.camera(-10, 20, 9500, 1000)
    posts = ring('стойка')
    low = by('болт_уголка_низ')
    for _, ps in posts:
        go(ps, tl.t, 1.0, frm=(0, 0, 1500))
        tl.bolts_in(near(low, ps[0].c), tl.t + 1.0, 0.5)
        tl.t += 1.6
    tl.t += 0.3

    tl.caption('Колья', 'Арматура Ø12 × 1 м — сквозь лежни в землю')
    for _, ps in ring('колья'):
        go(ps, tl.t, 0.7, frm=(0, 0, 1100))
        tl.t += 0.35
    tl.t += 1.0

    tl.caption('3. Верхняя обвязка', 'Вдоль конька — уголками вниз, поперёк — перевёрнутая. Болт М10×130 на каждый конец')
    tl.camera(20, 26, 9500, 1400)
    high = by('болт_уголка_верх')
    for nm, ps in ring('обвязка'):
        go(ps, tl.t, 1.0, frm=(0, 0, 900))
        ends = [p for _, bs in high if nm.split('_')[1] in _ for p in bs]
        tl.bolts_in(ends, tl.t + 1.0, 0.5)
        tl.t += 1.6
    tl.t += 1.0

    # ---------------------------------------------------------- 2. щиты
    STAGE, SPREAD = 1500, 350
    spans = []
    for nm, ps in by('пролёт_'):
        kind = nm.split('_')[1]
        n = [len(panel(k)) for k in ('глухой', kind, 'глухой')]
        panels = [ps[sum(n[:i]):sum(n[:i + 1])] for i in range(3)]
        joints = ps[sum(n):]
        out_, along = outward(np.mean([p.c for p in ps], 0))
        # щиты пролёта идут по s ребра — на северной и западной стенах это против оси
        pc = [np.mean([p.c for p in pn], 0) for pn in panels]
        along = tuple(int(s) * abs(a) for s, a in zip(np.sign(pc[2] - pc[0]), along))
        bolts = dict(by('болты_пролёта_'))[nm.replace('пролёт_' + kind, 'болты_пролёта')]
        spans.append(dict(nm=nm, kind=kind, panels=panels, joints=joints, bolts=bolts, out=out_, along=along))
    spans.sort(key=lambda s: s['kind'] != 'дверь')                 # с дверью — первым, подробно

    def staged(s, i=None):
        o = mul(s['out'], STAGE)
        return o if i is None else add(o, mul(s['along'], (i - 1) * SPREAD))

    def build_panel(s, i, t0, k=1.0):
        st = staged(s, i)
        ps = s['panels'][i]
        sheath = [p for p in ps if p.name.startswith('обшивка')]
        leaf = [p for p in ps if p.name.split('_')[0] in ('полотно', 'петля', 'ручка')]
        frame = [p for p in ps if p not in sheath and p not in leaf]
        go(frame, t0, 0.6 * k, st, frm=add(st, (0, 0, 500)))
        go(sheath, t0 + 0.6 * k, 0.6 * k, st, frm=add(st, mul(s['out'], 500)))
        if leaf:
            go(leaf, t0 + 1.2 * k, 0.6 * k, st, frm=add(st, mul(s['out'], -600)))

    tl.caption('4. Щиты', 'Рама из бруска 25×50 на ребро, снаружи фанера ФСФ 3 мм. Глухие, с окном, с дверью — готовятся в мастерской')
    tl.camera(150, 30, 12500, 1100)
    s0 = spans[0]
    for i in range(3):
        build_panel(s0, i, tl.t)
        tl.t += 1.9 if s0['kind'] == 'дверь' and i == 1 else 1.4
    tl.t += 0.6
    tl.camera(150, 30, 12500, 1100)
    tl.camera(250, 32, 13500, 1100, t=tl.t + 4.5)
    for s in spans[1:]:
        for i in range(3):
            build_panel(s, i, tl.t, k=0.7)
            tl.t += 0.35
    tl.t += 1.6

    # ---------------------------------------------------------- 3. щиты -> пролёт
    tl.caption('5. Три щита → пролёт', 'Щиты сдвигаются вплотную, на каждом стыке 3 болта М10×80 с гайкой. Пролёт 2991 × 2400')
    for s in spans:
        for i in range(3):
            go(s['panels'][i], tl.t, 1.2, staged(s))
        tl.bolts_in(s['joints'], tl.t + 1.2, 0.6, base=staged(s))
    tl.t += 2.6
    tl.camera(250, 32, 13500, 1100)

    # ---------------------------------------------------------- 4. пролёты -> каркас
    tl.caption('6. Пролёты на каркас', 'На лежень между стойками. 4 болта М10×150 сквозь стойки (барашки изнутри) + 2 болта М10×80 снизу в обвязку')
    tl.camera(330, 24, 10500, 1200, t=tl.t + 4 * 2.4)
    for s in spans:
        mine = s['panels'][0] + s['panels'][1] + s['panels'][2] + s['joints']
        go(mine, tl.t, 1.5)
        tl.bolts_in(s['bolts'], tl.t + 1.5, 0.6)
        tl.t += 2.4
    tl.t += 0.6

    # ---------------------------------------------------------- 5. крыша
    tl.caption('7. Фермы', 'Две полуфермы + болт М10×130 в коньке. Крайние — фронтонные, зашиты фанерой. Пята — болт М10×80 в футорку')
    tl.camera(330, 24, 10500, 1200)
    tl.camera(285, 26, 9500, 1900, t=tl.t + 2.5)
    LIFT, SPL = 1700, 900
    YR = SY / 2
    for nm, ps in sorted(by('ферма_'), key=lambda it: int(it[0].split('_')[1])):
        bolts = [p for p in ps if p.name.startswith('болт')]
        ridge = [p for p in bolts if p.c[2] > ZP + 200]
        heel = [p for p in bolts if p not in ridge]
        halves = [p for p in ps if p not in bolts]
        for p in halves:
            sgn = -1 if p.c[1] < YR else 1
            go([p], tl.t, 0.9, (0, 0, LIFT), frm=(0, sgn * SPL, LIFT))
        tl.bolts_in(ridge, tl.t + 0.9, 0.4, base=(0, 0, LIFT))
        go(halves + ridge, tl.t + 1.5, 1.0)
        tl.bolts_in(heel, tl.t + 2.5, 0.4)
        tl.t += 2.4
    tl.t += 0.8

    tl.caption('8. Конёк', 'Брус 50×100 на верх ферм, бобышками по бокам. На каждой ферме 2 болта М10×130 '
                           'сквозь бобышки и стойки полуферм')
    tl.camera(285, 34, 6500, 2600, t=tl.t + 1.0)
    for _, ps in by('конёк'):
        bl = [p for p in ps if p.name.startswith('болт')]
        go([p for p in ps if p not in bl], tl.t, 1.0, frm=(0, 0, 800))
        for i, p in enumerate(bl):
            tl.bolts_in([p], tl.t + 1.1 + 0.25 * i, 0.4)
        tl.t += 1.2 + 0.25 * len(bl)
    tl.t += 0.6
    tl.caption('9. Прогоны', 'Брусок 25×50 плашмя поперёк стропил, нижний — карнизный. На каждой ферме болт М10×80 '
                             'сверху сквозь прогон в опору стропила, барашек снизу')
    tl.camera(285, 34, 6500, 2600)
    for _, ps in by('прогон'):
        bl = [p for p in ps if p.name.startswith('болт')]
        go([p for p in ps if p not in bl], tl.t, 0.7, frm=(0, 0, 600))
        tl.bolts_in(bl, tl.t + 0.7, 0.4)
        tl.t += 0.6
    tl.t += 1.2
    tl.caption('10. Тент', 'Через конёк по прогонам; край по карнизу заворачивают под карнизный прогон')
    tl.camera(285, 34, 6500, 2600)
    tl.camera(300, 22, 8000, 2200, t=tl.t + 1.6)
    go([p for _, ps in by('тент') for p in ps], tl.t, 1.4, frm=(0, 0, 1200))
    tl.t += 2.2
    ties = [p for _, ps in by('резинки') for p in ps]
    tl.caption('11. Резинки', f'Через люверсы тента — резинки с шариком ({len(ties)} шт.): по карнизу — вокруг карнизного '
                              'прогона через ~0,5 м, на фронтонах — вокруг концов прогонов и конька')
    for p in sorted(ties, key=lambda p: (p.c[1] > tl.center[1], p.c[0])):
        go([p], tl.t, 0.3, frm=(0, 0, 200))
        tl.t += 0.12
    tl.t += 1.6
    tl.camera(300, 22, 8000, 2200)

    tl.caption(f'Готово: дом {name}',
               f'Каркас {SX / 1000:.1f} × {SY / 1000:.1f} м, высота {ZT / 1000:.2f} м. Разборка — в обратном порядке')
    tl.camera(300, 22, 8000, 2200)
    tl.t += 8
    tl.camera(420, 22, 11000, 1500)
    tl.captions[-1][1] = tl.t

    hidden = [p.name for p in allp if not p.keys]
    assert not hidden, hidden
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(dict(name=name, duration=tl.t, parts=[p.json() for p in allp], captions=tl.captions,
                   camera=tl.cam, target=[SX / 2, SY / 2]), open(out, 'w'), ensure_ascii=False)
    print(f'{name}: {len(allp)} деталей, {tl.t:.1f} с -> {out}')

