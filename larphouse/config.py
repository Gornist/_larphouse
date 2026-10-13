"""Файлы данных: дома, цены, нормы времени (larphouse/data/*.toml)."""
import os, tomllib

DATA = os.path.join(os.path.dirname(__file__), 'data')


def _load(name):
    with open(os.path.join(DATA, name), 'rb') as f:
        return tomllib.load(f)


HOUSES = _load('houses.toml')                       # ключ (латиница) -> конфигурация
_p = _load('prices.toml')
PRICE_LUMBER = {sec: {int(L): v for L, v in d.items()} for sec, d in _p['lumber'].items()}
LUMBER_APPROX = {(sec, L) for sec, Ls in _p['lumber_approx'].items() for L in Ls}
PRICE = _p['hardware']
OTHER = _p['other']
LABOR = _load('labor.toml')
