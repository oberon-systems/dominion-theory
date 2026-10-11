import numpy as np
from numpy.typing import NDArray

from dominion_theory.planet import BIOMES, atlas, generate, settings
from dominion_theory.planet.generator import generator
from dominion_theory.planet.rivers import apply, create
from dominion_theory.planet.settings.biomes.base import Biome


def world(seed: int, rivers: int = 0) -> NDArray[np.uint8]:
    return generate(seed=seed, width=24, height=16, rivers=np.random.default_rng(rivers))


def test_atlas_fills_every_cell_with_a_biome() -> None:
    cells = atlas(seed=5, width=24, height=16, rivers=np.random.default_rng(0))

    assert cells.shape == (16, 24)
    assert all(isinstance(cell, Biome) for cell in cells.flat)
    assert [BIOMES.index(repr(cell)) for cell in cells.flat] == world(5).flatten().tolist()


def test_same_arguments_give_the_same_map() -> None:
    assert np.array_equal(world(5), world(5))
    assert not np.array_equal(world(5), world(6))


def test_rivers_follow_the_stream_given() -> None:
    elevation = np.zeros((32, 32))

    def rivers(seed: int) -> NDArray[np.bool_]:
        return create(height=32, width=32, num=settings.rivers, elevation=elevation, rng=np.random.default_rng(seed))

    assert np.array_equal(rivers(1), rivers(1))
    assert not np.array_equal(rivers(1), rivers(2))
    assert rivers(1).any()


def test_rivers_are_laid_as_water() -> None:
    cells = np.zeros((2, 2), dtype=np.uint8)
    rivers = np.array([[True, False], [False, True]])

    assert apply(biomes=cells, rivers=rivers, water=3).tolist() == [[3, 0], [0, 3]]
    assert not cells.any()


def test_first_biome_that_matches_wins() -> None:
    elevation = np.array([[-0.5, 0.1, 0.5, 0.1]])
    moisture = np.array([[-0.5, -0.5, -0.5, 0.5]])

    cells = generator(elevation=elevation, moisture=moisture, biomes=settings.biomes)

    assert [BIOMES[code] for code in cells[0]] == ['water', 'mountain', 'grass', 'forest']
