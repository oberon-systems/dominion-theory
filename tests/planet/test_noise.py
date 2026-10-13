import numpy as np
from numpy.typing import NDArray

from dominion_theory.engine.streams import Streams
from dominion_theory.planet.noise import Noise, stream

AROUND = 4000
STEP = 5.0


def noise(seed: int) -> Noise:
    return Noise(stream(seed, 'alpha'), circumference_km=AROUND, scale_km=700, octaves=4, persistence=0.5)


def ring(seed: int) -> NDArray[np.float64]:
    x, y = np.meshgrid(np.arange(0.0, AROUND, STEP), np.arange(2.5, AROUND / 2, 50.0))
    return noise(seed)(x, y)


def test_stream_is_derived_as_the_engine_derives_its_own() -> None:
    assert stream(5, 'alpha').random() == Streams(5)['alpha'].random()
    assert stream(5, 'alpha').random() != stream(5, 'beta').random()


def test_same_seed_gives_the_same_noise() -> None:
    assert np.array_equal(ring(7), ring(7))
    assert not np.array_equal(ring(7), ring(8))


def test_noise_stays_within_its_range_and_varies() -> None:
    world = ring(7)

    assert world.min() >= -1.0
    assert world.max() <= 1.0
    assert world.std() > 0.05


def test_noise_has_no_seam() -> None:
    world = ring(7)
    inside = np.abs(np.diff(world, axis=1))
    across = np.abs(world[:, 0] - world[:, -1])

    assert across.max() <= inside.max()
    assert across.mean() <= 2 * inside.mean()


def test_noise_repeats_after_one_turn_around_the_planet() -> None:
    x = np.array([10.0, 1234.5, 3999.0])
    y = np.array([20.0, 700.0, 1999.0])

    assert np.allclose(noise(7)(x, y), noise(7)(x + AROUND, y))


def test_largest_shapes_are_a_whole_number_around() -> None:
    made = noise(7)

    assert [table.shape[1] for table in made.gradients] == [6, 12, 24, 48]
