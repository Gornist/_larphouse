"""Где лежат результаты. Пути и имена файлов — латиница, содержимое — по-русски."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
PARTS_IMG = os.path.join(DOCS, 'img', 'parts')
PDF = os.path.join(DOCS, 'modular_houses.pdf')
HOUSES = os.path.join(ROOT, 'houses')
BLOCKS = os.path.join(ROOT, 'blocks')
BUILD = os.path.join(ROOT, 'build')          # промежуточное (не в git)


def house_dir(key):
    return os.path.join(HOUSES, key)


_WORDS = [('полуферма', 'half_truss'), ('стойка', 'post'), ('лежень', 'sill'), ('обвязка', 'beam'),
          ('пролёт', 'span'), ('щит', 'panel'), ('глухой', 'blank'), ('окно', 'window'), ('дверь', 'door'),
          ('средняя', 'middle'), ('фронтон_0', 'gable_a'), ('фронтон_25', 'gable_b')]
_SIZE = {'М': 'small', 'Б': 'big'}


def slug(block):
    """Имя блока -> имя файла: полуферма_М_фронтон_0 -> half_truss_small_gable_a."""
    parts = block.split('_')
    s = '_'.join(_SIZE.get(p, p) for p in parts)
    for ru, en in _WORDS:
        s = s.replace(ru, en)
    assert s.isascii(), s
    return s
