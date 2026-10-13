"""Модульные игровые дома: параметрическая модель и генератор документации.

Модули по слоям:
  dims, geom, tally          — размеры, примитивы, учёт раскроя и покупного
  panels, frame, roof        — детали: щиты и пролёты, каркас, крыша
  house                      — дом из клеток сетки (конфигурации — data/houses.toml)
  estimate, assembly         — смета (цены — data/prices.toml) и инструкция по сборке
  render, drawings, anim     — картинки и раскадровка анимации (anim_blender.py — внутри Blender)
  check, pdf                 — проверка модели, сборка PDF
Запуск — python -m larphouse (см. __main__.py).
"""
