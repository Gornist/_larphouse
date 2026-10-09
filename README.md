# Модульные игровые дома

Сборно-разборные деревянные дома для ролевых игр (LARP).

- **`step/6/`** — актуальная версия: модульная система на сетке 3,1 м, дома
  3×3, 3×6, 3×9, 6×6. Документация — [`step/6/README.md`](step/6/README.md),
  всё одним файлом для печати — [`step/6/Модульные_дома.pdf`](step/6/Модульные_дома.pdf).
- `step/5/` — предыдущая версия (одиночный дом 3×3), смета с источниками цен —
  `step/5/СТОИМОСТЬ.md`.

## Инструменты

- `tools/grid_house.py` — параметрическая модель v6: STEP, спецификация, смета, инструкция по сборке
- `tools/grid_draw.py` — картинки домов и деталей
- `tools/make_pdf.py` — сборка документации в PDF (pandoc + Chromium)
- `tools/v5_house.py`, `tools/v5_draw.py` — модель и картинки v5 (v6 использует их детали)
- `tools/step_io.py` — запись STEP с русскими названиями

```
pip install build123d scipy pillow
python tools/grid_house.py 6х6 step/6/6х6 step/6/блоки
python tools/grid_draw.py 6х6 step/6/6х6/img
python tools/make_pdf.py step/6 step/6/Модульные_дома.pdf
```
