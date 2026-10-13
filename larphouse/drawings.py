"""Картинки домов (houses/<дом>/img) и деталей (docs/img/parts)."""
import os

from .house import build
from .frame import beam
from .panels import panel, KINDS
from .render import render, items_of

EN = {'глухой': 'blank', 'окно': 'window', 'дверь': 'door'}
HIDE = ('арматура',)


def house_images(h, out):
    os.makedirs(out, exist_ok=True)
    name = h.title
    sel = h.parts
    base = sel(lambda gr, b: gr == 'основание')
    frame = sel(lambda gr, b: gr == 'каркас')
    spans = sel(lambda gr, b: gr == 'пролёты')
    trusses = sel(lambda gr, b: b.startswith('ферма'))
    rest = sel(lambda gr, b: b in ('конёк', 'прогон'))
    tent = sel(lambda gr, b: b in ('тент', 'резинки'))
    W = 1200
    render(items_of(base + frame + spans + trusses + rest + tent, hide=HIDE), f'{out}/house.png', az=-35, el=22, size=W,
           title=f'Дом {name} в сборе')
    render(items_of(base + frame + spans + trusses + rest, hide=HIDE), f'{out}/no_tent.png', az=145, el=30, size=W,
           title=f'Дом {name} без тента')
    render(items_of(base + frame + trusses + rest, hide=HIDE), f'{out}/frame.png', az=-35, el=28, size=W,
           title='Каркас и фермы (без пролётов)')
    render(items_of(base + frame + spans, hide=HIDE), f'{out}/plan.png', az=0, el=89.9, size=W,
           title='План: стойки, лежни, пролёты (вид сверху)')
    steps = [('step1_frame', '1. Каркас: стойки, лежни, обвязка', [], base + frame),
             ('step2_spans', '2. Пролёты по периметру', base + frame, spans),
             ('step3_trusses', '3. Фермы', base + frame + spans, trusses),
             ('step4_roof', '4. Конёк, прогоны, тент на резинках', base + frame + spans + trusses, rest + tent)]
    for fn, t, old, new in steps:
        render(items_of(old, grey=True, hide=HIDE) + items_of(new, hide=HIDE, sheath_alpha=200 if 'roof' in fn else 255),
               f'{out}/{fn}.png', az=-35, el=28, size=1000, title=t)


def parts_images(out, small=None, big=None):
    """Картинки всех деталей системы (для docs/parts.md). small, big — дома 3x3 и 6x6, если уже построены."""
    os.makedirs(out, exist_ok=True)
    blocks3 = (small or build('3x3')).blocks
    blocks6 = (big or build('6x6')).blocks
    for k in KINDS:
        pp, e = panel(k), EN[k]
        render(items_of(pp), f'{out}/panel_{e}_outside.png', az=-20, el=12, size=600, title=f'Щит «{k}», снаружи')
        render(items_of(pp), f'{out}/panel_{e}_inside.png', az=160, el=12, size=600, title=f'Щит «{k}», изнутри')
        sp = blocks6.get(f'пролёт_{k}') or blocks3.get(f'пролёт_{k}')
        render(items_of(sp), f'{out}/span_{e}.png', az=165, el=10, size=900, title=f'Пролёт «{k}», изнутри (болты стыков)')
    render(items_of(blocks6['стойка']), f'{out}/post.png', az=-140, el=20, size=420, title='Стойка')
    render(items_of(blocks6['стойка']), f'{out}/post_holes.png', az=-140, el=25, size=600, title='Стойка: отверстия')
    render(items_of(blocks6['лежень']), f'{out}/sill.png', az=-20, el=40, size=1000, title='Лежень (уголки на концах)')
    render(items_of(beam('x')), f'{out}/beam.png', az=-20, el=25, size=1000, title='Обвязка: вдоль конька (уголки внизу)')
    render(items_of(beam('y')), f'{out}/beam_flipped.png', az=-20, el=25, size=1000, title='Обвязка поперёк — перевёрнута (уголки вверху)')
    for tag, size, src in (('М', 'малая', blocks3), ('Б', 'большая', blocks6)):
        for k, t, e in (('средняя', 'средняя', 'middle'), ('фронтон_0', 'фронтонная А', 'gable_a'),
                        ('фронтон_25', 'фронтонная Б', 'gable_b')):
            pp = src[f'полуферма_{tag}_{k}']
            fn = f'{out}/half_truss_{"small" if tag == "М" else "big"}_{e}'
            render(items_of(pp), f'{fn}.png', az=-90, el=0, size=1000, title=f'Полуферма {size} {t} — сбоку')
            render(items_of(pp), f'{fn}_iso.png', az=-60, el=25, size=800, title=f'Полуферма {size} {t}')
