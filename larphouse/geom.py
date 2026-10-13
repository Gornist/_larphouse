"""Твердотельные примитивы и деталь P."""
import numpy as np
from build123d import Align, Axis, Box, Compound, Cylinder, Face, Location, Plane, Solid, Vector, Wire, extrude

MIN = (Align.MIN, Align.MIN, Align.MIN)
DENS = {'дерево': 500e-9, 'фанера': 600e-9, 'сталь': 7850e-9}     # кг/мм³

# цвета для картинок
WOOD, WOOD2, PLYC = (222, 184, 135), (196, 152, 104), (236, 214, 170)
FRAME = (150, 105, 65)


class P:
    """Деталь: тело, имя (русское, с размерами), материал, цвет. У болтов ещё axis — (головка, конец)."""

    def __init__(self, solid, name, mat='дерево', color=(214, 176, 128)):
        self.solid, self.name, self.mat, self.color = solid, name, mat, color

    def mass(self):
        return self.solid.volume * DENS[self.mat]


def box(x0, x1, y0, y1, z0, z1):
    return Box(x1 - x0, y1 - y0, z1 - z0, align=MIN).moved(Location((x0, y0, z0)))


def cyl(d, p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    if np.count_nonzero(np.abs(v) > 1e-9) > 1:          # наклонный (болты прогонов — по нормали к скату)
        return Solid.make_cylinder(d / 2, float(np.linalg.norm(v)), Plane(origin=tuple(p0), z_dir=tuple(v)))
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
    """Призма вдоль X из многоугольника в плоскости (u, z); y = y_of_u(u)."""
    f = Face(Wire.make_polygon([Vector(x0, y_of_u(u), z) for u, z in pts_uz], close=True))
    return extrude(f, amount=x1 - x0, dir=(1, 0, 0))


def place(parts, loc):
    out = []
    for q in parts:
        m = P(q.solid.moved(loc), q.name, q.mat, q.color)
        if hasattr(q, 'axis'):
            m.axis = tuple(tuple((loc * Location(p)).position) for p in q.axis)
        out.append(m)
    return out


def compound(parts, label):
    ch = []
    for q in parts:
        s = q.solid.moved(Location())
        s.label = q.name
        ch.append(s)
    c = Compound(children=ch)
    c.label = label
    return c
