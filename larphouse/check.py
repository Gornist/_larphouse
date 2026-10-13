"""Проверка модели дома: пересечения деталей и болты.

  python -m larphouse check 3x3 [группа]       (то же — в tests/test_model.py)

1. Детали не должны пересекаться по объёму (касание гранями — можно).
2. Каждый болт стоит в отверстиях: сам болт (Ø10) ни с чем не пересекается,
   а щуп Ø14 по его оси задевает детали, которые болт стягивает, — они печатаются.
"""
import collections
import numpy as np

from .geom import cyl
from .house import build

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


def check(h, only=None):
    """-> (пересечения {(деталь, деталь): n}, болты, врезанные в детали [(болт, узел, [детали])],
    что стягивает каждый болт {(болт, узел, детали): n})."""
    parts = [(gr, it, q) for gr, it, ps in h.items for q in ps if only is None or gr == only]
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
    stuck, through = [], collections.Counter()
    for _, it, q in bolts:
        bq = bbox(q.solid)
        hits = [(r[2].name, vol(q.solid, r[2].solid)) for r, bb in zip(rest, boxes) if overlap(bq, bb)]
        hard = [n for n, v in hits if v > EPS]
        if hard:
            stuck.append((q.name, it, hard))
        p0, p1 = q.axis
        probe = cyl(14, tuple(p0), tuple(p1))
        hit = sorted({r[2].name.split('_')[0] for r, bb in zip(rest, boxes) if overlap(bbox(probe), bb) and vol(probe, r[2].solid) > EPS})
        through[(q.name, it.split('_')[0], ' + '.join(hit))] += 1
    return bad, stuck, through


def report(key, only=None):
    """Печать отчёта; True — модель чистая."""
    h = build(key)
    bad, stuck, through = check(h, only)
    n_bolts = sum(through.values())
    n_rest = sum(1 for gr, _, ps in h.items for q in ps if only is None or gr == only) - n_bolts
    print(f'{h.title}: {n_rest} деталей, {n_bolts} болтов')
    for (a, b_), n in bad.most_common():
        print(f'  пересечение: {a} × {b_} ({n})')
    for bn, it, hard in stuck:
        print(f'  болт {bn} ({it}) врезается в: {", ".join(hard)}')
    for (bn, it, hit), n in sorted(through.items()):
        print(f'  {bn:14s} {it:22s} ×{n:3d}: {hit or "НИЧЕГО"}')
    return not bad and not stuck and all(hit for _, _, hit in through)
