"""Дом из клеток сетки: каркас, пролёты по периметру, крыша.

build(key) -> House. Детали дома — список (группа, узел, [P]):
группы «основание», «каркас», «пролёты», «крыша»; узел — имя в STEP и в анимации.
"""
import collections
from dataclasses import dataclass, field
from build123d import Compound, Location

from .config import HOUSES
from .dims import POST, PITCH, Z0, GAP, PLY, ANG_O, TOP_O, Z_ANG
from .frame import post, lezhen, stakes, beam, span_bolts
from .geom import compound, place
from .panels import span
from .roof import roof
from .step_io import save_step
from . import tally
from .tally import bolt


@dataclass
class House:
    key: str                 # 3x3 — для путей
    title: str               # 3х3 — для текстов и STEP
    cfg: dict
    blocks: dict             # имя блока -> детали (в своих координатах), по одному экземпляру
    items: list              # [(группа, узел, [P])]
    dims: tuple              # габарит каркаса X, Y и высота до конька
    cut: collections.Counter = field(default_factory=collections.Counter)    # раскрой
    hw: collections.Counter = field(default_factory=collections.Counter)     # покупное

    def parts(self, pred=lambda gr, it: True):
        return [q for gr, it, ps in self.items if pred(gr, it) for q in ps]


def edge_loc(d, i, j, sigma):
    """Система координат ребра: s вдоль ребра (0..PITCH+POST, стойки по краям), o — внутрь от наружной грани."""
    if d == 'x':
        return (Location((i * PITCH, j * PITCH, 0), (0, 0, 0)) if sigma < 0
                else Location(((i + 1) * PITCH + POST, j * PITCH + POST, 0), (0, 0, 180)))
    return (Location((i * PITCH, (j + 1) * PITCH + POST, 0), (0, 0, 270)) if sigma < 0
            else Location((i * PITCH + POST, j * PITCH, 0), (0, 0, 90)))


def edges(cfg):
    """Рёбра сетки: (направление, i, j, сторона ±1, по периметру?, что в проёме)."""
    NX, NY = cfg['NX'], cfg['NY']
    out = []
    for j in range(NY + 1):
        for i in range(NX):
            per = j in (0, NY)
            kind = (cfg['S'][i] if j == 0 else cfg['N'][NX - 1 - i]) if per else None
            out.append(('x', i, j, 1 if (j == NY and NY > 0) else -1, per, kind))
    for i in range(NX + 1):
        for j in range(NY):
            per = i in (0, NX)
            kind = (cfg['W'][NY - 1 - j] if i == 0 else cfg['E'][j]) if per else None
            out.append(('y', i, j, 1 if i == NX else -1, per, kind))
    return out


def build(key):
    cfg = HOUSES[key]
    tally.reset()
    NX, NY = cfg['NX'], cfg['NY']
    SX, SY = NX * PITCH + POST, NY * PITCH + POST
    house, blocks = [], {}

    def blk(name, parts):
        blocks.setdefault(name, parts)
        return parts

    for i in range(NX + 1):
        for j in range(NY + 1):
            house.append(('каркас', f'стойка_{i}{j}', place(blk('стойка', post()), Location((i * PITCH, j * PITCH, 0)))))
    ang_bolts = set()
    for d, i, j, sg, per, kind in edges(cfg):
        loc = edge_loc(d, i, j, sg)
        nm = f'{d}{i}{j}'
        house.append(('основание', f'лежень_{nm}', place(blk('лежень', lezhen()), loc * Location((POST, 0, 0)))))
        if per:
            house.append(('основание', f'колья_{nm}', place(stakes(), loc * Location((POST, 0, 0)))))
        house.append(('каркас', f'обвязка_{nm}', place(blk('обвязка', beam(d)), loc * Location((POST, 0, 0)))))
        if kind:
            house.append(('пролёты', f'пролёт_{kind}_{nm}', place(blk(f'пролёт_{kind}', span(kind)), loc * Location((POST + GAP, PLY, Z0)))))
            house.append(('пролёты', f'болты_пролёта_{nm}', place(span_bolts(d), loc)))
        # болты уголков: по одному сквозному на узел/направление/высоту
        for end_s in (0, PITCH):
            for o, z in ((ANG_O, Z_ANG[d][0]), (TOP_O, Z_ANG[d][1])):
                g = loc * Location((end_s + POST / 2, o, z))
                k = (d, round(g.position.X), round(g.position.Y), round(g.position.Z))
                if k in ang_bolts:
                    continue
                ang_bolts.add(k)
                head = Location((end_s - 5 if end_s == 0 else end_s + POST + 5, o, z))
                house.append(('основание' if o == ANG_O else 'каркас', f'болт_уголка_{"низ" if o == ANG_O else "верх"}_{nm}_{end_s}',
                              place([bolt((0, 0, 0), (1, 0, 0) if end_s == 0 else (-1, 0, 0), 130, 'барашек')], loc * head)))
    items, top = roof(NX, NY, SX, SY, blk)
    house += items
    return House(key, cfg['title'], cfg, blocks, house, (SX, SY, top),
                 collections.Counter(tally.CUT), collections.Counter(tally.HW))


def save_house_step(h, path):
    groups = collections.OrderedDict()
    for g_, b_, parts in h.items:
        groups.setdefault(g_, []).append(compound(parts, b_))
    top = Compound(children=[Compound(children=v, label=k) for k, v in groups.items()])
    top.label = f'дом_{h.title}'
    save_step(top, path)


def save_block_steps(blocks, out, slug):
    for k, parts in blocks.items():
        save_step(compound(parts, k), f'{out}/{slug(k)}.step')
