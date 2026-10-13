import time

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.planet import Planet

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
WIDE = {'planet.circumference_km': 8000, 'planet.window.width': 32, 'planet.window.height': 16}


def test_skeleton_has_a_node_every_skeleton_km(params: Params) -> None:
    skeleton = Planet(7, params).skeleton

    assert skeleton.elevation.shape == skeleton.relief.shape == skeleton.moisture.shape == (20, 40)


@pytest.mark.parametrize('sea', [0.0, 0.25, 0.6, 1.0])
def test_share_of_nodes_under_the_sea_is_the_parameter(sea: float) -> None:
    skeleton = Planet(7, load_params(overrides={**WIDE, 'planet.sea': sea})).skeleton
    under = int((~skeleton.land).sum())

    assert abs(under - sea * skeleton.land.size) <= 1


def test_elevation_restated_on_land_is_close_to_uniform() -> None:
    world = Planet(7, load_params(overrides=WIDE)).read(0, 0, 400, 200, 20)
    land = world.elevation[world.elevation > 0]
    shares, _ = np.histogram(land, bins=10, range=(0.0, 1.0))

    assert abs(land.size / world.elevation.size - 0.4) < 0.05
    assert np.abs(shares / land.size - 0.1).max() < 0.05


def test_relief_and_moisture_are_shares_of_land() -> None:
    world = Planet(7, load_params(overrides=WIDE)).read(0, 0, 400, 200, 20)
    land = world.elevation > 0

    assert abs(float(np.median(world.relief[land])) - 0.5) < 0.1
    assert abs(float(np.median(world.moisture[land])) - 0.5) < 0.1


def test_skeleton_is_worked_out_once_for_a_seed_and_a_planet(params: Params) -> None:
    other = load_params(overrides={**SMALL, 'planet.window.width': 64, 'planet.window.height': 8})

    assert Planet(7, params).skeleton is Planet(7, other).skeleton
    assert Planet(7, params).skeleton is not Planet(8, params).skeleton


def test_small_planet_builds_in_a_fraction_of_a_second(params: Params) -> None:
    started = time.perf_counter()

    Planet(987654321, params).read(0, 0, 32, 16, 10)

    assert time.perf_counter() - started < 0.5
