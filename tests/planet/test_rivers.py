import numpy as np
import pytest
from numpy.typing import NDArray

from dominion_theory.content import Params, load_params
from dominion_theory.planet import Planet
from dominion_theory.planet.rivers import (
    NONE,
    PIECES,
    Rivers,
    _smooth,
    delta,
    drain,
    fill,
    flooded,
    gather,
    ocean,
    pick,
    rivers,
    sources,
)

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
def test_share_of_nodes_that_carry_the_most_is_the_parameter(share: float) -> None:
    planet = Planet(7, load_params(overrides={**SMALL, 'planet.rivers.share': share}))
    land = planet.skeleton.land
    nodes = planet.rivers.nodes

    assert int(nodes.sum()) >= round(share * int(land.sum()))
    assert nodes.any() == (share > 0)
    assert not (nodes & ~land).any()


def test_river_is_followed_up_to_its_source() -> None:
    surface = fill(HEIGHTS, LAND)
    targets = drain(surface, LAND)
    flow = gather(surface, targets, RAIN)
    chosen = pick(flow, surface, LAND, 0.1)

    followed = sources(chosen, flow, targets)

    assert chosen.sum() < followed.sum()
    assert (followed[chosen]).all()
    assert not (followed & ~LAND).any()
    heads = [node for node in np.flatnonzero(followed).tolist() if not followed.flat[targets.ravel() == node].any()]
    assert heads
    for head in heads:
        assert not (targets.ravel() == head).any()
    for node in np.flatnonzero(followed & ~chosen).tolist():
        assert followed.flat[targets.flat[node]]


def test_small_body_of_water_is_an_inland_sea_and_water_runs_through_it() -> None:
    heights = np.tile(np.array([-1.0, -1.0, 3.0, 2.0, -0.5, 2.5, 1.0, -1.0]), (3, 1))
    land = heights > 0

    wide = ocean(land, 0.3)
    surface = fill(heights, ~wide)
    targets = drain(surface, ~wide)

    assert np.array_equal(wide, np.tile(np.array([True, True, False, False, False, False, False, True]), (3, 1)))
    assert ocean(land, 0.0).sum() == (~land).sum()
    assert not ocean(land, 0.9).any()
    assert (surface[:, 4] > heights[:, 4]).all()
    for node in np.flatnonzero(~wide).tolist():
        assert wide.flat[way(targets, node)[-1]]
    assert (targets[:, 4] != NONE).all()


def test_deepest_basins_are_flooded_whole() -> None:
    surface = fill(HEIGHTS, LAND)

    assert not flooded(HEIGHTS, surface, LAND, 0.0).any()
    assert np.array_equal(flooded(HEIGHTS, surface, LAND, 1.0), surface > HEIGHTS)
    assert flooded(HEIGHTS, surface, LAND, 1.0)[:, 3].all()

    heights = np.tile(np.array([-1.0, 5.0, 1.0, 6.0, 4.0, 3.9, 7.0, 2.0]), (3, 1))
    land = heights > 0
    filled = fill(heights, land)
    deepest = flooded(heights, filled, land, 0.5)

    assert np.array_equal(flooded(heights, filled, land, 1.0), filled > heights)
    assert deepest[:, 2].all()
    assert not deepest[:, 5].any()


def test_lake_is_water_and_stays_in_its_basin() -> None:
    wet = load_params(overrides={**SMALL, 'planet.rivers.lakes': 1.0})
    dry = load_params(overrides={**SMALL, 'planet.rivers.lakes': 0.0})
    drowned = Planet(5, wet).read(0, 0, 400, 200, 10)
    world = Planet(5, dry).read(0, 0, 400, 200, 10)
    laid = Planet(5, wet).rivers
    lakes = (drowned.elevation <= 0) & (world.elevation > 0)
    centres = np.arange(40, dtype=np.float64) * 100.0 + 50.0
    levels = laid.lake(centres, np.full(40, 950.0))

    assert lakes.any()
    assert not ((drowned.elevation > 0) & (world.elevation <= 0)).any()
    assert (drowned.biomes[lakes] == Planet(5, wet).biomes.index('water')).all()
    assert np.array_equal(levels > -np.inf, laid.lakes[9])
    assert levels[laid.lakes[9]].tolist() == pytest.approx(laid.surface[9][laid.lakes[9]].tolist(), abs=1e-6)
    assert not Planet(5, dry).rivers.lakes.any()


def test_flow_is_a_ribbon_along_a_river_as_wide_as_the_river_is_large() -> None:
    line = np.array([[1000.0, 500.0], [1100.0, 500.0]])
    bare = np.zeros((20, 40))
    course = np.array([[1000.0, 500.0, 1100.0, 500.0, 0.0, 0.0, 0.5, 1.0]])
    lone = Rivers(4000, bare > 0, bare, (line,), course, 0.0, 60.0, surface=bare, lakes=bare > 0)
    x = np.array([1000.0, 1050.0, 1100.0, 1100.0, 1100.0, 1100.0, 1200.0, 3000.0])
    y = np.array([500.0, 500.0, 500.0, 530.0, 560.0, 440.0, 500.0, 500.0])

    assert lone.wet(x, y).tolist() == pytest.approx([0.5, 0.75, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0])
    assert not lone.bed(x, y).any()
    assert lone.wet(x + 4000.0, y).tolist() == pytest.approx(lone.wet(x, y).tolist())


def test_curve_runs_through_every_point_it_was_given() -> None:
    controls = np.array([[0.0, 0.0], [100.0, 50.0], [200.0, -50.0], [300.0, 0.0]])

    curve = _smooth(controls)

    assert len(curve) == 3 * PIECES + 1
    assert np.array_equal(curve[::PIECES], controls)
    steps = np.diff(curve, axis=0)
    turns = np.abs(np.diff(np.arctan2(steps[:, 1], steps[:, 0])))
    assert turns.max() < np.pi / 2


def test_great_river_has_a_bed_of_water_with_islands() -> None:
    great = {**SMALL, 'planet.rivers.great': 0.05, 'planet.rivers.width_km': 30}
    bare = Planet(5, load_params(overrides={**great, 'planet.rivers.islands': 0.0}))
    isles = Planet(5, load_params(overrides={**great, 'planet.rivers.islands': 0.5}))
    none = Planet(5, load_params(overrides={**SMALL, 'planet.rivers.great': 0.0}))
    beds = bare.rivers.beds
    x, y = np.meshgrid(np.arange(400) * 10.0 + 5.0, np.arange(200) * 10.0 + 5.0)

    lying = bare.rivers.bed(x, y)
    dry = none.read(0, 0, 400, 200, 10).elevation > 0

    assert len(none.rivers.beds) == 0
    assert not none.rivers.bed(x, y).any()
    assert len(beds)
    assert beds[:, 4:].max() == 15.0
    assert (lying & dry).any()
    assert not (bare.read(0, 0, 400, 200, 10).elevation[lying] > 0).any()
    assert (isles.read(0, 0, 400, 200, 10).elevation[lying] > 0).any()
    for west, north, east, south in beds[:20, :4].tolist():
        middle = np.array([(west + east) / 2]), np.array([(north + south) / 2])
        assert bare.rivers.bed(*middle).all()
    assert np.array_equal(lying[:, :200], bare.rivers.bed(x[:, :200], y[:, :200]))


def test_arm_of_a_delta_bears_away_and_ends_in_the_sea() -> None:
    def under(x: NDArray[np.float64], y: NDArray[np.float64]) -> NDArray[np.bool_]:
        return x >= 300.0

    course = {'delta_km': 200.0, 'arms': 5.0}
    forks = np.full((5, 2), 0.5)

    arms = delta(np.array([100.0, 500.0]), np.array([200.0, 500.0]), course, forks, under)

    assert len(arms) == 8
    for arm in arms:
        assert arm[-1, 0] >= 300.0
        assert (arm[:-1, 0] < 300.0).all()
    assert sum(1 for arm in arms if tuple(arm[0]) == (100.0, 500.0)) == 4
    assert {float(np.sign(arm[-1, 1] - 500.0)) for arm in arms} == {-1.0, 1.0}
    assert delta(np.array([100.0, 500.0]), np.array([200.0, 500.0]), course, forks, lambda x, y: x < 0) == []
    assert delta(np.array([100.0, 500.0]), np.array([200.0, 500.0]), {**course, 'arms': 0.0}, forks, under) == []


def test_great_river_meets_the_ocean_in_a_delta() -> None:
    great = {**SMALL, 'planet.rivers.great': 0.05}
    armed = Planet(5, load_params(overrides=great)).rivers
    plain = Planet(5, load_params(overrides={**great, 'planet.rivers.arms': 0})).rivers

    assert len(armed.lines) > len(plain.lines)
    assert len(armed.courses) > len(plain.courses)
    assert np.array_equal(armed.beds, plain.beds)


def test_mouth_of_a_river_lies_at_the_centre_of_a_sea_node(params: Params) -> None:
    planet = Planet(5, params)
    land = planet.skeleton.land
    side = params.planet.skeleton_km
    mouths = 0

    for line in planet.rivers.lines:
        x, y = line[-1]
        row, column = int(y // side), int(x // side) % land.shape[1]
        if not land[row, column] and (x % side, y % side) == pytest.approx((side / 2, side / 2)):
            mouths += 1
    assert mouths


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


def test_line_ends_in_water_or_in_another_line(params: Params) -> None:
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
        under = bool(planet.skeleton.restate(np.array([x]), np.array([y]))['elevation'][0] <= 0)
        assert at_sea or met or under


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
    bare = np.zeros((20, 40))
    lone = Rivers(4000, bare > 0, bare, (line,), np.zeros((0, 8)), 0.0, 60.0, surface=bare, lakes=bare > 0)

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
