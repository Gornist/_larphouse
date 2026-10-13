# Модульные игровые дома

Сборно-разборные деревянные дома для ролевых игр (LARP): модульная система
на сетке 3,1 м, дома 3×3, 3×6, 3×9, 6×6.

- **Документация** — [`docs/README.md`](docs/README.md), всё одним файлом
  для печати — [`docs/modular_houses.pdf`](docs/modular_houses.pdf).
- **Дома** — `houses/<дом>/`: инструкция по сборке `assembly.md`, смета
  `estimate.md`, 3D-модель `house_<дом>.step`, картинки `img/`; видео сборки
  дома 3×3 — [`houses/3x3/assembly_3x3.mp4`](houses/3x3/assembly_3x3.mp4).
- **Блоки** (детали системы, STEP) — `blocks/`.

## Как устроено

```
docs/                      документация (пишется вручную) и картинки деталей
houses/<дом>/              генерируется: assembly.md, estimate.md, STEP, img/
blocks/                    генерируется: STEP деталей
larphouse/                 генератор (Python)
  data/houses.toml         дома: размер сетки и что стоит в проёмах
  data/prices.toml         цены для смет
  data/labor.toml          нормы времени монтажа
  dims.py                  все размеры
  geom.py, tally.py        примитивы; учёт раскроя и покупного
  panels.py, frame.py,     детали: щиты и пролёты, каркас, крыша
  roof.py
  house.py                 дом из клеток сетки
  estimate.py, assembly.py смета и инструкция по сборке
  render.py, drawings.py   картинки
  anim.py, anim_blender.py анимация сборки (раскадровка → Blender → MP4)
  check.py                 проверка: пересечения деталей, болты в отверстиях
  pdf.py                   PDF (pandoc + Chromium)
tests/                     pytest
```

Пути и имена файлов — латиница; тексты, названия деталей и метки в STEP —
по-русски.

## Команды

```
pip install build123d scipy pillow pytest
python -m larphouse all              # всё: STEP, сметы, инструкции, картинки, PDF
python -m larphouse model 6x6        # только STEP, estimate.md, assembly.md дома 6x6
python -m larphouse images 6x6       # картинки дома
python -m larphouse parts-images     # картинки деталей → docs/img/parts
python -m larphouse pdf              # → docs/modular_houses.pdf
python -m larphouse check 3x3        # отчёт проверки модели
pytest                               # проверка всех домов (несколько минут)
python -m larphouse anim 3x3         # → build/anim_3x3.json
blender -b -P larphouse/anim_blender.py -- build/anim_3x3.json houses/3x3/assembly_3x3.mp4
```

Новый дом — секция в `larphouse/data/houses.toml`, затем
`python -m larphouse all <ключ>` и строка в таблице домов `docs/README.md`.
