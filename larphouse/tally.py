"""Детали, которые попадают в раскрой и закупку: брусок, болт, футорка, сталь.

Каждый вызов записывается в счётчики CUT (раскрой) и HW (покупное);
house.build() обнуляет их перед сборкой дома и забирает результат.
"""
import collections
import numpy as np

from .geom import P, cyl

CUT = collections.Counter()      # (сечение, длина) -> шт.
HW = collections.Counter()       # покупное -> шт.


def reset():
    CUT.clear()
    HW.clear()


def bar(name, sec, length, solid, color=(214, 176, 128)):
    CUT[(sec, round(length))] += 1
    return P(solid, name, 'дерево', color)


def bolt(p0, d, L, nut):
    """Болт М10×L: головка в p0, стержень по направлению d. nut: гайка | барашек | футорка."""
    p0, d = np.array(p0, float), np.array(d, float) / np.linalg.norm(d)
    HW[f'Болт М10×{L}'] += 1
    HW['Шайба М10 увеличенная'] += 1 if nut == 'футорка' else 2
    if nut == 'барашек':
        HW['Гайка-барашек М10'] += 1
    elif nut == 'гайка':
        HW['Гайка М10'] += 1
    q = P(cyl(10, p0, p0 + d * L), f'болт_М10х{L}', 'сталь', (60, 60, 60))
    q.axis = (tuple(p0), tuple(p0 + d * L))           # для проверки и анимации
    return q


def futorka(x, y, z_top, depth=25):
    """Врезная гайка М10 (футорка) — трубка Ø14 в дереве, сверху вниз."""
    HW['Гайка врезная (футорка) М10'] += 1
    t = cyl(14, (x, y, z_top - depth), (x, y, z_top)) - cyl(10.5, (x, y, z_top - depth - 1), (x, y, z_top + 1))
    return P(t, 'футорка_М10', 'сталь', (150, 150, 60))


def steel(solid, name, color=(70, 70, 80)):
    return P(solid, name, 'сталь', color)
