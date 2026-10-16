from functools import partial
from typing import Any

import pytest

from dominion_theory.content import Params
from dominion_theory.engine import decisions, routes
from dominion_theory.engine.band import Band, adults

ERA = 'band'
HOME = (100, 50)
GRASS = {'biome': 'grass', 'river': False, 'water': 0.28, 'food': 0.8, 'threat': 0.1, 'passability': 1.0, 'seen': 0}
FOREST = {'biome': 'forest', 'river': False, 'water': 0.6, 'food': 0.9, 'threat': 0.4, 'passability': 0.6, 'seen': 0}
SEA = {'biome': 'water', 'river': False, 'water': 1.0, 'food': 0.3, 'threat': 0.2, 'passability': 0.0, 'seen': 0}
SATED = {'hunger': 0.1, 'thirst': 0.1}


def held(known: dict[tuple[int, int], dict[str, Any]]) -> Band:
    return Band(id=1, x=HOME[0], y=HOME[1], members=adults(15), stores={}, known=dict(known))


def field(cell: dict[str, Any], width: int = 7, height: int = 5) -> dict[tuple[int, int], dict[str, Any]]:
    return {(HOME[0] + dx, HOME[1] + dy): cell for dx in range(width) for dy in range(-2, height - 2)}


def inside(x: int, y: int) -> bool:
    return 95 <= x <= 110 and 45 <= y <= 55


def laid(params: Params, band: Band, to: tuple[int, int], within: Any = inside) -> list[Any] | None:
    return routes.lay(params, band, to, within, partial(decisions.looks, params, band, ERA), SATED)


def test_a_step_costs_its_time_its_threat_and_what_it_lacks(params: Params) -> None:
    thirsty = {'hunger': 0.1, 'thirst': 1.0}

    assert routes.cost(params, FOREST, SATED) == pytest.approx(1 / 0.6 + 2.0 * 0.4 + 0.1 * 0.1 + 0.1 * 0.4)
    assert routes.cost(params, GRASS, thirsty) > routes.cost(params, GRASS, SATED)
    assert routes.cost(params, FOREST, SATED, 0.25) == pytest.approx(0.75 / 0.6 + 2.0 * 0.4 + 0.1 * 0.1 + 0.1 * 0.4)


def test_a_route_laid_anew_keeps_the_cell_the_band_is_partway_into(params: Params) -> None:
    band = held(field(GRASS))
    to = (HOME[0] + 2, HOME[1] - 1)
    fresh = laid(params, band, to)
    band.target, band.progress = (HOME[0] + 1, HOME[1]), 0.5

    assert fresh == [(101, 49), (102, 49)]
    assert laid(params, band, to) == [(101, 50), (102, 49)]


def test_a_route_on_even_land_runs_straight_to_the_target(params: Params) -> None:
    band = held(field(GRASS))

    assert laid(params, band, (HOME[0] + 3, HOME[1])) == [(101, 50), (102, 50), (103, 50)]
    assert laid(params, band, (HOME[0] + 2, HOME[1] + 2)) == [(101, 51), (102, 52)]


def test_a_route_bends_round_a_forest_when_the_way_round_costs_less(params: Params) -> None:
    known = field(GRASS)
    known.update({(101, 50): FOREST, (102, 50): FOREST})

    assert laid(params, held(known), (HOME[0] + 3, HOME[1])) == [(101, 49), (102, 49), (103, 50)]


def test_land_the_band_does_not_know_is_costed_by_what_it_expects(params: Params) -> None:
    band = held({HOME: GRASS})

    way = laid(params, band, (HOME[0] + 3, HOME[1]))

    assert way == [(101, 50), (102, 50), (103, 50)]
    assert decisions.looks(params, band, ERA, (101, 50)) == dict(params.units.band.decisions.unknown)


def test_there_is_no_route_through_water_or_out_of_the_box(params: Params) -> None:
    known = field(GRASS)
    known.update({(HOME[0] + 1, HOME[1] + dy): SEA for dy in range(-2, 3)})
    walled = held(known)

    assert laid(params, walled, (HOME[0] + 3, HOME[1]), lambda x, y: inside(x, y) and 48 <= y <= 52) is None
    assert laid(params, held(field(GRASS)), (120, 50)) is None


@pytest.mark.parametrize(
    ('to', 'towards'),
    [((0, -5), 'north'), ((3, -3), 'north-east'), ((4, -1), 'east'), ((-2, 5), 'south'), ((-3, -2), 'north-west')],
)
def test_a_way_is_told_by_the_nearest_of_the_eight_directions(to: tuple[int, int], towards: str) -> None:
    assert routes.towards((0, 0), to) == towards
