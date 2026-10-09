"""Картинки модульных домов.  python tools/grid_draw.py <имя> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import grid_house as g
from v5_draw import render, items_of


def main(name, out):
    os.makedirs(out, exist_ok=True)
    blocks, house, dims = g.build(g.CONFIGS[name])
    sel = lambda pred: [q for gr, b, parts in house if pred(gr, b) for q in parts]
    hide = ('арматура',)
    base = sel(lambda gr, b: gr == 'основание')
    frame = sel(lambda gr, b: gr == 'каркас')
    spans = sel(lambda gr, b: gr == 'пролёты')
    trusses = sel(lambda gr, b: b.startswith('ферма'))
    rest = sel(lambda gr, b: b in ('конёк', 'прогон'))
    tent = sel(lambda gr, b: b == 'тент')
    W = 1200
    render(items_of(base + frame + spans + trusses + rest + tent, hide=hide), f'{out}/дом.png', az=-35, el=22, size=W,
           title=f'Дом {name} в сборе')
    render(items_of(base + frame + spans + trusses + rest, hide=hide), f'{out}/без_тента.png', az=145, el=30, size=W,
           title=f'Дом {name} без тента')
    render(items_of(base + frame + trusses + rest, hide=hide), f'{out}/каркас.png', az=-35, el=28, size=W,
           title='Каркас и фермы (без пролётов)')
    render(items_of(base + frame + spans, hide=hide), f'{out}/план.png', az=0, el=89.9, size=W,
           title='План: стойки, лежни, пролёты (вид сверху)')
    steps = [('шаг1_каркас', '1. Каркас: стойки, лежни, обвязка', [], base + frame),
             ('шаг2_пролёты', '2. Пролёты по периметру', base + frame, spans),
             ('шаг3_фермы', '3. Фермы', base + frame + spans, trusses),
             ('шаг4_крыша', '4. Конёк, прогоны, тент', base + frame + spans + trusses, rest + tent)]
    for fn, t, old, new in steps:
        render(items_of(old, grey=True, hide=hide) + items_of(new, hide=hide, sheath_alpha=200 if 'крыша' in fn else 255),
               f'{out}/{fn}.png', az=-35, el=28, size=1000, title=t)


if __name__ == '__main__' and sys.argv[1] != 'детали':
    main(sys.argv[1], sys.argv[2])


def parts(out):
    """Картинки всех деталей системы (для ДЕТАЛИ.md)."""
    import v5_house as b
    os.makedirs(out, exist_ok=True)
    blocks3, _, _ = g.build(g.CONFIGS['3х3'])
    blocks6, _, _ = g.build(g.CONFIGS['6х6'])
    for k in ('глухой', 'окно', 'дверь'):
        pp = b.panel(k)
        render(items_of(pp), f'{out}/щит_{k}_снаружи.png', az=-20, el=12, size=600, title=f'Щит «{k}», снаружи')
        render(items_of(pp), f'{out}/щит_{k}_изнутри.png', az=160, el=12, size=600, title=f'Щит «{k}», изнутри')
        sp = blocks6.get(f'пролёт_{k}') or blocks3.get(f'пролёт_{k}')
        render(items_of(sp), f'{out}/пролёт_{k}.png', az=165, el=10, size=900, title=f'Пролёт «{k}», изнутри (болты стыков)')
    render(items_of(blocks6['стойка']), f'{out}/стойка.png', az=-140, el=20, size=420, title='Стойка')
    render(items_of(blocks6['стойка']), f'{out}/стойка_низ.png', az=-140, el=25, size=600, title='Стойка: отверстия')
    render(items_of(blocks6['лежень']), f'{out}/лежень.png', az=-20, el=40, size=1000, title='Лежень (уголки на концах)')
    render(items_of(g.beam('x')), f'{out}/обвязка.png', az=-20, el=25, size=1000, title='Обвязка: вдоль конька (уголки внизу)')
    render(items_of(g.beam('y')), f'{out}/обвязка_перевёрнутая.png', az=-20, el=25, size=1000, title='Обвязка поперёк — перевёрнута (уголки вверху)')
    for tag, src in (('М', blocks3), ('Б', blocks6)):
        for k, t in (('средняя', 'средняя'), ('фронтон_0', 'фронтонная А'), ('фронтон_25', 'фронтонная Б')):
            pp = src[f'полуферма_{tag}_{k}']
            size = 'малая' if tag == 'М' else 'большая'
            render(items_of(pp), f'{out}/полуферма_{tag}_{k}.png', az=-90, el=0, size=1000, title=f'Полуферма {size} {t} — сбоку')
            render(items_of(pp), f'{out}/полуферма_{tag}_{k}_изо.png', az=-60, el=25, size=800, title=f'Полуферма {size} {t}')


if __name__ == '__main__' and sys.argv[1] == 'детали':
    parts(sys.argv[2])
