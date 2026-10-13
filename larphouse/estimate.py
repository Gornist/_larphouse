"""Спецификация и смета дома: раскрой в магазинные длины, крепёж, фанера, тент."""
import collections, math, re

from .config import PRICE_LUMBER, LUMBER_APPROX, PRICE, OTHER
from .dims import PLY, PLY_G


def pack(items, stock, kerf=4):
    """Раскрой «первый подходящий» деталей items из хлыстов длин stock -> Counter(длина хлыста: шт.)."""
    bars = []
    for L in sorted(items, reverse=True):
        for bar_ in bars:
            if bar_[0] >= L + kerf:
                bar_[0] -= L + kerf
                break
        else:
            S = min(x for x in stock if x >= L)
            bars.append([S - L - kerf, S])
    return collections.Counter(x[1] for x in bars)


def lumber_buy(cut):
    """Самый дешёвый набор магазинных длин по каждому сечению -> {сечение: (₽, Counter)}."""
    out = {}
    for sec, prices in PRICE_LUMBER.items():
        items = [ln for (sc, ln), n in cut.items() if sc == sec for _ in range(n)]
        if not items:
            continue
        best = None
        stocks = sorted(prices)
        for k in range(1, len(stocks) + 1):
            for combo in [stocks[:k], stocks[-k:]]:
                if max(items) > max(combo):
                    continue
                c = pack(items, combo)
                cost = sum(prices[L] * n for L, n in c.items())
                if best is None or cost < best[0]:
                    best = (cost, c)
        out[sec] = best
    return out


def block_counts(h):
    cnt = collections.Counter()
    for g_, b_, _ in h.items:
        k = b_.rsplit('_', 1)[0] if b_[:5] in ('стойк', 'лежен', 'обвяз', 'ферма') else b_
        k = 'пролёт ' + b_.split('_')[1] if b_.startswith('пролёт_') else k
        if k.startswith(('стойка', 'лежень', 'обвязка', 'пролёт', 'ферма', 'конёк', 'прогон')):
            cnt[k] += 1
    return cnt


def estimate(h):
    """-> (текст estimate.md, итог ₽, масса без тента кг)."""
    hw, cut, dims = h.hw, h.cut, h.dims
    area = lambda pred: sum(q.solid.volume for q in h.parts() if pred(q))
    gable_m2 = area(lambda q: 'фронтона' in q.name) / PLY / 1e6
    gus_m2 = area(lambda q: q.name.startswith('косынка')) / PLY_G / 1e6
    n_spans = sum(1 for g_, b_, _ in h.items if b_.startswith('пролёт_'))
    n_doors = sum(1 for g_, b_, _ in h.items if b_.startswith('пролёт_дверь'))
    sheets3 = 3 * n_spans + n_doors + math.ceil(gable_m2 * 1.3 / 2.977)
    sheets9 = max(1, math.ceil(gus_m2 * 1.4 / 2.326))
    buy = lumber_buy(cut)
    lum_m = sum(ln * n for (sc, ln), n in cut.items()) / 1000
    consum = OTHER['consumables_3x3'] * lum_m / 175
    FSF3, FK9 = OTHER['fsf3_sheet'], OTHER['fk9_sheet']
    tent_name = next(k for k in hw if k.startswith('Тент'))
    tw, tl = [float(x) for x in tent_name.split('≥ ')[1].split(' м')[0].split('×')]
    L = [f'# Дом {h.title} — спецификация и смета', '',
         f'Габарит каркаса {dims[0] / 1000:.1f} × {dims[1] / 1000:.1f} м, высота до конька {dims[2] / 1000:.2f} м. '
         'Сгенерировано `python -m larphouse`. Цены — средние по строймагам РФ, октябрь 2026 '
         '(источники — [Закупка](../../docs/purchasing.md)), ≈ — оценка.', '',
         '## Блоки', '', '| Блок | Шт. |', '|---|---|']
    for k, n in block_counts(h).items():
        L.append(f'| {k} | {n} |')
    L += ['', '## Смета', '', '| Позиция | Кол-во | Цена, ₽ | Сумма, ₽ |', '|---|---|---|---|']
    total = collections.Counter()
    for sec, (cost, c) in buy.items():
        for ln, n in sorted(c.items()):
            pr = PRICE_LUMBER[sec][ln]
            L.append(f'| Брус/брусок {sec}×{ln} | {n} шт | {"≈ " if (sec, ln) in LUMBER_APPROX else ""}{pr} | {pr * n:,.0f} |')
            total['Пиломатериалы'] += pr * n
    L.append(f'| Фанера ФСФ 3 мм 1220×2440 | {sheets3} листов | ≈ {FSF3} | {FSF3 * sheets3:,.0f} |')
    L.append(f'| Фанера ФК 9 мм 1525×1525 (косынки) | {sheets9} | {FK9} | {FK9 * sheets9:,.0f} |')
    total['Фанера'] += FSF3 * sheets3 + FK9 * sheets9
    for k, n in sorted(hw.items()):
        if k.startswith('Уголок г/к'):
            m, pr = math.ceil(n * 0.043), OTHER['angle_m']        # отрезок 40 + пропил 3
            L.append(f'| Уголок г/к 63×63×6 (нарезать {n} шт по 40 мм) | {m} м | ≈ {pr} | {pr * m:,.0f} |')
            total['Крепёж'] += pr * m
            continue
        if k.startswith('Футорка'):
            packs = math.ceil(n / 40)
            pr = OTHER['epoxy_pack']
            L.append(f'| Клей эпоксидный ЭДП 280 г (футорки) | {packs} шт | ≈ {pr} | {pr * packs:,.0f} |')
            total['Крепёж'] += pr * packs
        if k.startswith('Тент'):
            pr = OTHER['tent_m2'] * tw * tl
            L.append(f'| {k} | 1 | ≈ {pr:,.0f} | {pr:,.0f} |')
            total['Прочее'] += pr
            continue
        pr = PRICE.get(k)
        if pr is None:
            continue
        q = math.ceil(n * 1.1) if k.startswith(('Болт', 'Гайка', 'Шайба', 'Футорка')) else n
        unit = 'м' if 'Арматура' in k else 'шт'
        L.append(f'| {k} | {q} {unit} | {pr} | {pr * q:,.0f} |')
        total['Крепёж' if k.startswith(('Болт', 'Гайка', 'Шайба', 'Футорка')) else 'Прочее'] += pr * q
    L.append(f'| Саморезы, клей D3, антисептик | | ≈ | {consum:,.0f} |')
    total['Прочее'] += consum
    s = sum(total.values())
    L += ['', '| Группа | ₽ |', '|---|---|'] + [f'| {k} | {v:,.0f} |' for k, v in total.items()]
    L += [f'| **Итого** | **≈ {s:,.0f}** |', f'| С запасом 10 % | ≈ {s * 1.1:,.0f} |', '',
          'Метизы — с запасом 10 %. Пиломатериал — в магазинных длинах, раскрой из модели с пропилом 4 мм.', '']
    L += ['## Раскрой', '', '| Сечение | Длина, мм | Шт. |', '|---|---|---|']
    for (sc, ln), n in sorted(cut.items(), key=lambda t: (t[0][0], -t[0][1])):
        L.append(f'| {sc} | {ln} | {n} |')
    total_mass = sum(q.mass() for q in h.parts() if q.name != 'тент')
    L += ['', f'Масса без тента ≈ {total_mass:.0f} кг.', '']
    txt = '\n'.join(L)
    txt = re.sub(r'(?<=\d),(?=\d{3})', ' ', txt)       # 12,345 -> 12 345
    return txt, s, total_mass
