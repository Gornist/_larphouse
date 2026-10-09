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


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
