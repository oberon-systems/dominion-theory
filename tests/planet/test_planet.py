import numpy as np
import pytest

from dominion_theory.content import LAYERS, Params
from dominion_theory.planet import Planet, Region, biome_names

CELLS = (*LAYERS, 'biomes')
GRIDS = (*CELLS, 'rivers')


def same(first: Region, second: Region) -> bool:
    return all(np.array_equal(getattr(first, grid), getattr(second, grid)) for grid in GRIDS)


def joined(first: Region, second: Region, axis: int) -> Region:
    return Region(**{grid: np.concatenate((getattr(first, grid), getattr(second, grid)), axis) for grid in GRIDS})


def test_same_seed_gives_the_same_planet(params: Params) -> None:
    assert same(Planet(5, params).read(8, 60, 24, 16, 10), Planet(5, params).read(8, 60, 24, 16, 10))
    assert not same(Planet(5, params).read(8, 60, 24, 16, 10), Planet(6, params).read(8, 60, 24, 16, 10))


def test_biome_codes_are_positions_in_the_ordered_identifiers(params: Params) -> None:
    planet = Planet(5, params)
    cells = planet.read(0, 0, 400, 200, 10).biomes

    assert planet.biomes == biome_names(params)
    assert cells.shape == (200, 400)
    assert cells.dtype == np.uint8
    assert int(cells.max()) < len(planet.biomes)


def test_rectangle_read_whole_and_in_halves_is_the_same(params: Params) -> None:
    planet = Planet(5, params)
    whole = planet.read(100, 60, 40, 30, 10)

    assert same(whole, joined(planet.read(100, 60, 20, 30, 10), planet.read(120, 60, 20, 30, 10), 1))
    assert same(whole, joined(planet.read(100, 60, 40, 15, 10), planet.read(100, 75, 40, 15, 10), 0))


def test_x_wraps_from_east_to_west(params: Params) -> None:
    planet = Planet(5, params)

    halves = joined(planet.read(396, 60, 4, 4, 10), planet.read(0, 60, 4, 4, 10), 1)

    assert same(planet.read(396, 60, 8, 4, 10), halves)
    assert same(planet.read(-4, 60, 8, 4, 10), planet.read(396, 60, 8, 4, 10))


def test_row_outside_the_poles_is_an_error(params: Params) -> None:
    planet = Planet(5, params)

    with pytest.raises(ValueError, match='between the poles'):
        planet.read(0, -1, 4, 4, 10)
    with pytest.raises(ValueError, match='between the poles'):
        planet.read(0, 197, 4, 4, 10)
    assert planet.read(0, 196, 4, 4, 10).biomes.shape == (4, 4)


def test_two_cell_sizes_agree_where_their_centres_coincide(params: Params) -> None:
    planet = Planet(5, params)
    fine = planet.read(0, 0, 400, 200, 10)
    coarse = planet.read(0, 0, 80, 40, 50)

    for grid in CELLS:
        assert np.array_equal(getattr(fine, grid)[2::5, 2::5], getattr(coarse, grid))


def test_mountains_are_the_highest_land(params: Params) -> None:
    planet = Planet(5, params)
    world = planet.read(0, 0, 400, 200, 10)
    mountain = world.biomes == planet.biomes.index('mountain')
    water = (world.biomes == planet.biomes.index('water')) | (world.biomes == planet.biomes.index('ice'))

    assert mountain.any()
    assert np.array_equal(mountain, world.elevation >= 0.92)
    assert np.array_equal(water, world.elevation <= 0.0)
    assert world.elevation[mountain].min() > world.elevation[~mountain].max()
