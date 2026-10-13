"""Проверка модели дома: пересечения деталей и болты.

  python tools/check_house.py 3х3 [группа]

1. Детали не должны пересекаться по объёму (касание гранями — можно).
2. Каждый болт стоит в отверстиях: сам болт (Ø10) ни с чем не пересекается,
   а щуп Ø14 по его оси задевает детали, которые болт стягивает, — они печатаются.
"""
import collections, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import grid_house as g
from v5_house import cyl

EPS = 1.0                    # мм³ — меньше считаем касанием
ALLOWED = {('тент', 'резинка_с_шариком')}             # резинка проходит сквозь люверс тента


def bbox(s):
    b = s.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def overlap(b1, b2):
    return np.all(b1[0] < b2[1]) and np.all(b2[0] < b1[1])


def vol(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def main(name, only=None):
    _, house, _ = g.build(g.CONFIGS[name])
    parts = [(gr, it, q) for gr, it, ps in house for q in ps if only is None or gr == only]
    bolts = [x for x in parts if x[2].name.startswith('болт')]
    rest = [x for x in parts if not x[2].name.startswith('болт')]
    boxes = [bbox(q.solid) for _, _, q in rest]
    bad = collections.Counter()
    for i in range(len(rest)):
        for j in range(i + 1, len(rest)):
            pair = tuple(sorted((rest[i][2].name, rest[j][2].name), reverse=True))
            if pair in ALLOWED or tuple(reversed(pair)) in ALLOWED:
                continue
            if overlap(boxes[i], boxes[j]) and vol(rest[i][2].solid, rest[j][2].solid) > EPS:
                bad[(rest[i][2].name, rest[j][2].name)] += 1
    print(f'{name}: {len(rest)} деталей, {len(bolts)} болтов')
    for (a, b_), n in bad.most_common():
        print(f'  пересечение: {a} × {b_} ({n})')
    through = collections.Counter()
    for _, it, q in bolts:
        bq = bbox(q.solid)
        hits = [(r[2].name, vol(q.solid, r[2].solid)) for r, bb in zip(rest, boxes) if overlap(bq, bb)]
        hard = [n for n, v in hits if v > EPS]
        if hard:
            print(f'  болт {q.name} ({it}) врезается в: {", ".join(hard)}')
        p0, p1 = q.axis
        probe = cyl(14, tuple(p0), tuple(p1))
        hit = sorted({r[2].name.split('_')[0] for r, bb in zip(rest, boxes) if overlap(bbox(probe), bb) and vol(probe, r[2].solid) > EPS})
        through[(q.name, it.split('_')[0], ' + '.join(hit))] += 1
    for (bn, it, hit), n in sorted(through.items()):
        print(f'  {bn:14s} {it:22s} ×{n:3d}: {hit or "НИЧЕГО"}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
