import numpy as np
import pytest

from dominion_theory.content import Params
from dominion_theory.planet.rules import classify, ordered

PLAIN = {'elevation': 0.5, 'relief': 0.6, 'moisture': 0.3, 'temperature': 0.4, 'flow': 0.3}


def biome(params: Params, **given: float) -> str:
    layers = {layer: np.array([[value]]) for layer, value in {**PLAIN, **given}.items()}
    return ordered(params.biomes)[int(classify(params.biomes, layers)[0, 0])]


def test_biomes_are_ordered_by_generation(params: Params) -> None:
    names = ('water', 'mountain', 'tundra', 'outcrops', 'hills', 'dunes', 'desert', 'swamp', 'marsh', 'forest', 'grass')

    assert ordered(params.biomes) == names


@pytest.mark.parametrize(
    ('given', 'expected'),
    [
        ({'elevation': -0.5, 'temperature': 0.1}, 'water'),
        ({'elevation': 0.95, 'temperature': 0.1}, 'mountain'),
        ({'temperature': 0.1, 'relief': 0.97}, 'tundra'),
        ({'relief': 0.97, 'elevation': 0.7}, 'outcrops'),
        ({'elevation': 0.7, 'moisture': 0.6}, 'hills'),
        ({'moisture': 0.6}, 'forest'),
        ({}, 'grass'),
    ],
)
def test_first_biome_by_order_wins(params: Params, given: dict[str, float], expected: str) -> None:
    assert biome(params, **given) == expected


def test_flat_warm_land_with_much_water_running_through_is_swamp(params: Params) -> None:
    assert biome(params, flow=0.95, relief=0.3) == 'swamp'
    assert biome(params, flow=0.95, relief=0.3, moisture=0.9) == 'swamp'
    assert biome(params, flow=0.95, relief=0.3, temperature=0.25) == 'grass'
    assert biome(params, flow=0.95, relief=0.6) == 'grass'
    assert biome(params, flow=0.8, relief=0.3) == 'grass'
    assert biome(params, flow=0.95, relief=0.3, elevation=0.7) == 'hills'


def test_low_flat_shore_is_marsh_where_it_is_moist_and_dunes_where_it_is_dry(params: Params) -> None:
    assert biome(params, elevation=0.1, relief=0.3, moisture=0.8) == 'marsh'
    assert biome(params, elevation=0.1, relief=0.3, moisture=0.8, flow=0.95) == 'swamp'
    assert biome(params, elevation=0.1, relief=0.3, moisture=0.8, temperature=0.25) == 'forest'
    assert biome(params, elevation=0.3, relief=0.3, moisture=0.8) == 'forest'
    assert biome(params, elevation=0.1, relief=0.3, moisture=0.2, temperature=0.6) == 'dunes'
    assert biome(params, elevation=0.1, relief=0.3, moisture=0.1, temperature=0.6) == 'dunes'
    assert biome(params, elevation=0.3, relief=0.3, moisture=0.1, temperature=0.6) == 'desert'
    assert biome(params, elevation=0.1, relief=0.6, moisture=0.2, temperature=0.6) == 'grass'


def test_all_ranges_of_a_rule_must_hold(params: Params) -> None:
    assert biome(params, moisture=0.1, temperature=0.6) == 'desert'
    assert biome(params, moisture=0.1, temperature=0.4) == 'grass'
    assert biome(params, moisture=0.3, temperature=0.6) == 'grass'


def test_ranges_are_closed(params: Params) -> None:
    assert biome(params, elevation=0.0) == 'water'
    assert biome(params, elevation=0.92) == 'mountain'
    assert biome(params, temperature=0.15) == 'tundra'


def test_every_cell_gets_a_biome(params: Params) -> None:
    rng = np.random.default_rng(3)
    layers = {layer: rng.uniform(-1.0 if layer == 'elevation' else 0.0, 1.0, (40, 60)) for layer in PLAIN}

    cells = classify(params.biomes, layers)

    assert cells.shape == (40, 60)
    assert cells.dtype == np.uint8
    assert sorted(set(cells.ravel().tolist())) == list(range(len(params.biomes)))
