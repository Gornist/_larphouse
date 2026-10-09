solidworks project for a wooden larp house

- `1/`–`4/` — версии модели в SolidWorks (актуальная — `4/`)
- `step/4/` — версия 4 в STEP для Fusion 360 и других CAD (см. `step/4/README.md`)
- `tools/sw2step.py` — конвертер SolidWorks → STEP
- `step/5/` — версия 5: щиты → пролёты стен (по 3 щита) → каркас (лежни, стойки, ригели) → пролёты в каркас → фермы, конёк, тент; монтаж 2 человека ≈ 1,5 ч (`tools/v5_house.py`, `tools/v5_draw.py`)
- `step/6/` — версия 6: модульная система на сетке 3,1 м (одинаковые стойки, лежни, обвязки, пролёты); дома 3×3, 3×6, 3×9, 6×6: детали, монтаж, закупка, сборка каждого дома — см. `step/6/README.md` (`tools/grid_house.py`, `tools/grid_draw.py`)
