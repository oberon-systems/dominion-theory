import numpy as np
import pytest
from numpy.typing import NDArray

from dominion_theory.content import Params, load_params
from dominion_theory.planet import Planet
from dominion_theory.planet.rivers import NONE, Rivers, drain, fill, gather, rivers

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
# A sea, a slope with a hollow on the way, a ridge, and a second slope that reaches the sea through the seam.
SLOPE = [-1.0, 1.0, 2.0, 0.5, 3.0, 9.0, 2.0, 1.0]
HEIGHTS = np.tile(np.array(SLOPE), (3, 1))
LAND = HEIGHTS > 0
RAIN = np.where(LAND, np.arange(HEIGHTS.size, dtype=np.float64).reshape(HEIGHTS.shape), 0.0)


def way(targets: NDArray[np.int64], node: int) -> list[int]:
    passed = [node]
    while targets.flat[passed[-1]] != NONE:
        passed.append(int(targets.flat[passed[-1]]))
        assert len(passed) <= targets.size
    return passed


def test_water_reaches_the_sea_and_a_hollow_does_not_stop_it() -> None:
    surface = fill(HEIGHTS, LAND)
    targets = drain(surface, LAND)

    for node in np.flatnonzero(LAND).tolist():
        assert not LAND.flat[way(targets, node)[-1]]
    assert (surface[:, 3] > surface[:, 2]).all()
    assert np.array_equal(surface[:, [0, 1, 2, 4, 5, 6, 7]], HEIGHTS[:, [0, 1, 2, 4, 5, 6, 7]])
    assert (targets[~LAND] == NONE).all()


def test_flow_gathered_at_a_mouth_is_the_rain_of_its_basin() -> None:
    surface = fill(HEIGHTS, LAND)
    targets = drain(surface, LAND)
    flow = gather(surface, targets, RAIN)
    ways = [way(targets, node) for node in np.flatnonzero(LAND).tolist()]
    mouths = {passed[-2] for passed in ways}

    assert len(mouths) > 1
    for mouth in mouths:
        basin = sum(RAIN.flat[passed[0]] for passed in ways if mouth in passed)
        assert flow.flat[mouth] == pytest.approx(basin)
    assert flow[~LAND].sum() == pytest.approx(RAIN.sum())


def test_of_two_equally_low_neighbours_the_first_direction_wins() -> None:
    targets = drain(fill(HEIGHTS, LAND), LAND)

    assert targets[1, 1] == 16
    assert targets[1, 7] == 0
    assert targets[1, 3] == 18


@pytest.mark.parametrize('share', [0.0, 0.08, 0.3])
def test_share_of_river_nodes_is_the_parameter(share: float) -> None:
    planet = Planet(7, load_params(overrides={**SMALL, 'planet.rivers.share': share}))
    land = planet.skeleton.land
    nodes = planet.rivers.nodes

    assert abs(int(nodes.sum()) - share * int(land.sum())) <= 1
    assert not (nodes & ~land).any()


def test_same_seed_gives_the_same_lines_and_another_seed_others(params: Params) -> None:
    first = Planet(5, params).rivers.lines
    rivers.cache_clear()
    again = Planet(5, params).rivers.lines
    other = Planet(6, params).rivers.lines

    assert first
    assert len(first) == len(again)
    assert all(np.array_equal(one, two) for one, two in zip(first, again, strict=True))
    assert len(first) != len(other) or not all(np.array_equal(one, two) for one, two in zip(first, other, strict=True))


def test_rivers_are_kept_beside_the_skeleton(params: Params) -> None:
    assert Planet(5, params).rivers is Planet(5, params).rivers
    assert Planet(5, params).rivers is not Planet(6, params).rivers


def test_line_ends_at_the_sea_or_in_another_line(params: Params) -> None:
    planet = Planet(5, params)
    land = planet.skeleton.land
    side = params.planet.skeleton_km
    circumference = params.planet.circumference_km
    lines = planet.rivers.lines

    for number, line in enumerate(lines):
        x, y = line[-1]
        others = np.concatenate([other for position, other in enumerate(lines) if position != number] + [line[:0]])
        around = np.abs((others[:, 0] - x + circumference / 2) % circumference - circumference / 2)
        met = bool(((around < 1e-6) & (np.abs(others[:, 1] - y) < 1e-6)).any())
        at_sea = not land[int(y // side), int(x // side) % land.shape[1]]
        assert at_sea or met


def test_marks_agree_between_a_rectangle_and_its_halves(params: Params) -> None:
    marks = Planet(5, params).rivers.marks

    whole = marks(0, 0, 400, 200, 10)

    assert whole.any()
    assert np.array_equal(whole, np.concatenate((marks(0, 0, 200, 200, 10), marks(200, 0, 200, 200, 10)), 1))
    assert np.array_equal(whole, np.concatenate((marks(0, 0, 400, 100, 10), marks(0, 100, 400, 100, 10)), 0))
    assert np.array_equal(whole[40:90, 130:170], marks(130, 40, 40, 50, 10))


def test_marks_agree_across_the_seam(params: Params) -> None:
    marks = Planet(5, params).rivers.marks
    whole = marks(0, 0, 400, 200, 10)

    across = marks(380, 0, 40, 200, 10)

    assert np.array_equal(across, np.concatenate((whole[:, 380:], whole[:, :20]), 1))
    assert np.array_equal(across, marks(-20, 0, 40, 200, 10))


def test_river_that_leaves_through_the_seam_comes_back_on_the_other_side() -> None:
    line = np.array([[3955.0, 505.0], [4045.0, 505.0]])
    lone = Rivers(circumference_km=4000, nodes=np.zeros((20, 40), bool), flow=np.zeros((20, 40)), lines=(line,))

    assert lone.marks(395, 50, 5, 1, 10).all()
    assert lone.marks(0, 50, 6, 1, 10).tolist() == [[True, True, True, True, True, False]]
    assert not lone.marks(0, 49, 400, 1, 10).any()
    assert lone.crossing(0, 500, 100, 510) == 1
    assert lone.crossing(1000, 500, 1100, 510) == 0


def test_larger_cell_finds_the_same_river(params: Params) -> None:
    marks = Planet(5, params).rivers.marks

    fine = marks(0, 0, 400, 200, 10)
    coarse = marks(0, 0, 80, 40, 50)

    assert np.array_equal(fine.reshape(40, 5, 80, 5).any(axis=(1, 3)), coarse)


def test_cell_of_water_carries_no_mark(params: Params) -> None:
    planet = Planet(5, params)
    world = planet.read(0, 0, 400, 200, 10)
    water = world.biomes == planet.biomes.index('water')
    lines = planet.rivers.marks(0, 0, 400, 200, 10)

    assert (lines & water).any()
    assert not (world.rivers & water).any()
    assert np.array_equal(world.rivers, lines & ~water)
