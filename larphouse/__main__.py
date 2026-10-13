"""Командная строка.

  python -m larphouse all [дом…]       всё: модели, сметы, инструкции, картинки, PDF
  python -m larphouse model [дом…]     STEP дома и блоков, estimate.md, assembly.md
  python -m larphouse images [дом…]    картинки домов
  python -m larphouse parts-images     картинки деталей (docs/img/parts)
  python -m larphouse pdf              docs/modular_houses.pdf
  python -m larphouse check [дом…] [--group каркас]
  python -m larphouse anim 3x3 [out.json]

Дом — ключ из data/houses.toml (3x3, 3x6, 3x9, 6x6); без ключа — все дома.
"""
import argparse, os, sys

from .config import HOUSES
from . import paths


def _houses(keys):
    keys = keys or list(HOUSES)
    unknown = [k for k in keys if k not in HOUSES]
    if unknown:
        sys.exit(f'нет такого дома: {", ".join(unknown)}; есть: {", ".join(HOUSES)}')
    return keys


def model(h):
    from .house import save_house_step, save_block_steps
    from .estimate import estimate
    from .assembly import assembly
    out = paths.house_dir(h.key)
    os.makedirs(out, exist_ok=True)
    save_house_step(h, f'{out}/house_{h.key}.step')
    est, cost, mass = estimate(h)
    asm, minutes = assembly(h)
    open(f'{out}/estimate.md', 'w', encoding='utf-8').write(est)
    open(f'{out}/assembly.md', 'w', encoding='utf-8').write(asm)
    os.makedirs(paths.BLOCKS, exist_ok=True)
    save_block_steps(h.blocks, paths.BLOCKS, paths.slug)        # блоки одинаковые для всех домов
    print(h.title, [round(x) for x in h.dims], f'{cost:,.0f} ₽', f'{mass:.0f} кг', f'{minutes} мин')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m larphouse', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['all', 'model', 'images', 'parts-images', 'pdf', 'check', 'anim'])
    ap.add_argument('houses', nargs='*')
    ap.add_argument('--group', help='check: только эта группа деталей')
    a = ap.parse_args(argv)
    from .house import build

    if a.cmd == 'anim':
        from .anim import storyboard
        key = _houses(a.houses[:1])[0]
        storyboard(key, a.houses[1] if len(a.houses) > 1 else os.path.join(paths.BUILD, f'anim_{key}.json'))
        return
    if a.cmd == 'check':
        from .check import report
        ok = [report(k, a.group) for k in _houses(a.houses)]
        sys.exit(0 if all(ok) else 1)
    if a.cmd == 'pdf':
        from .pdf import make_pdf
        make_pdf()
        return
    built = {}
    if a.cmd in ('all', 'model', 'images'):
        from .drawings import house_images
        for k in _houses(a.houses):
            h = built[k] = build(k)
            if a.cmd in ('all', 'model'):
                model(h)
            if a.cmd in ('all', 'images'):
                house_images(h, os.path.join(paths.house_dir(k), 'img'))
    if a.cmd in ('all', 'parts-images'):
        from .drawings import parts_images
        parts_images(paths.PARTS_IMG, built.get('3x3'), built.get('6x6'))
    if a.cmd == 'all':
        from .pdf import make_pdf
        make_pdf()


if __name__ == '__main__':
    main()
