import numpy as np
from numpy.typing import NDArray

from dominion_theory.planet.layers import generator


def layer(seed: int) -> NDArray[np.float64]:
    return generator(height=48, width=64, scale=20, octaves=4, persistence=0.5, lacunarity=2.0, seed=seed)


def test_same_seed_gives_same_layer() -> None:
    assert np.array_equal(layer(7), layer(7))


def test_other_seed_gives_other_layer() -> None:
    assert not np.array_equal(layer(7), layer(8))


def test_layer_has_requested_shape_and_range() -> None:
    world = layer(7)

    assert world.shape == (48, 64)
    assert world.min() >= -1.0
    assert world.max() <= 1.0
    assert world.std() > 0.05
