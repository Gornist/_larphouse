"""Проверки модели: pytest (долго — строит и пересекает все детали всех домов, несколько минут)."""
import pytest

from larphouse.config import HOUSES
from larphouse.house import build
from larphouse.check import check
from larphouse.estimate import estimate
from larphouse.assembly import assembly


@pytest.fixture(scope='module', params=list(HOUSES))
def house(request):
    return build(request.param)


def test_no_intersections_and_bolts_in_holes(house):
    bad, stuck, through = check(house)
    assert not bad, f'пересечения деталей: {dict(bad)}'
    assert not stuck, f'болты врезаются в детали: {stuck}'
    empty = [k for k in through if not k[2]]
    assert not empty, f'болты ни через что не проходят: {empty}'


# итоги на момент рефакторинга: меняются только вместе с моделью или ценами
EXPECTED = {'3x3': (47930, 293, 127), '3x6': (75714, 467, 200), '3x9': (103401, 640, 274), '6x6': (113595, 705, 286)}


def test_estimate_and_time(house):
    _, cost, mass = estimate(house)
    _, minutes = assembly(house)
    assert (round(cost), round(mass), minutes) == EXPECTED[house.key]
